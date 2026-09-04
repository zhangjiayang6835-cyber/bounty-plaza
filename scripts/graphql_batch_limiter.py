"""GraphQL Query Complexity & Batch Cost Rate Limiter.
Resolves Issue #304: GraphQL Batch Query + Rate Limit Bypass Defense ($150).
"""

import re
from typing import Any, Dict, List, Optional, Tuple, Union


class GraphQLLimitError(Exception):
    """Base error for GraphQL query limit violations."""
    pass


class GraphQLDepthLimitExceeded(GraphQLLimitError):
    """Raised when query selection nesting exceeds max depth."""
    pass


class GraphQLCostLimitExceeded(GraphQLLimitError):
    """Raised when query or batch complexity score exceeds quota."""
    pass


class GraphQLBatchLimitExceeded(GraphQLLimitError):
    """Raised when batch contains too many queries."""
    pass


class GraphQLSyntaxError(GraphQLLimitError):
    """Raised when query syntax is malformed."""
    pass


class GraphQLComplexityAnalyzer:
    """Zero-dependency parser and complexity analyzer for GraphQL queries.
    Calculates query depth, field weights, list multipliers, and aggregate batch costs.
    """

    def __init__(
        self,
        max_depth: int = 7,
        max_query_cost: int = 100,
        max_batch_cost: int = 250,
        max_batch_size: int = 15,
        default_field_cost: int = 1,
        custom_field_costs: Optional[Dict[str, int]] = None,
    ):
        self.max_depth = max_depth
        self.max_query_cost = max_query_cost
        self.max_batch_cost = max_batch_cost
        self.max_batch_size = max_batch_size
        self.default_field_cost = default_field_cost
        self.custom_field_costs = custom_field_costs or {}

    def _strip_comments_and_strings(self, query: str) -> str:
        """Strip GraphQL comments (#) and string literals to prevent brace counting anomalies."""
        # Strip string literals (both single and multiline)
        without_strings = re.sub(r'"""[\s\S]*?"""|"(?:\\.|[^"\\])*"', '""', query)
        # Strip comments
        lines = []
        for line in without_strings.splitlines():
            comment_idx = line.find('#')
            if comment_idx != -1:
                line = line[:comment_idx]
            lines.append(line)
        return '\n'.join(lines)

    def calculate_depth(self, query: str) -> int:
        """Calculate the maximum nesting depth of selection sets ({ ... })."""
        clean_query = self._strip_comments_and_strings(query)
        current_depth = 0
        max_depth = 0

        for char in clean_query:
            if char == '{':
                current_depth += 1
                if current_depth > max_depth:
                    max_depth = current_depth
            elif char == '}':
                current_depth = max(0, current_depth - 1)

        return max_depth

    def _extract_tokens_and_args(self, query: str) -> List[Tuple[str, Optional[int]]]:
        """Tokenize field names and detect list sizing arguments like first: N or limit: N."""
        clean_query = self._strip_comments_and_strings(query)
        # Normalize structural characters
        tokens = []
        # Match pattern: field_name or field_name(args)
        field_pattern = re.compile(r'([a-zA-Z_][a-zA-Z0-9_]*)(?:\s*\(([^)]*)\))?')
        for match in field_pattern.finditer(clean_query):
            field_name = match.group(1)
            args_str = match.group(2)
            # Skip GraphQL operation keywords
            if field_name in ('query', 'mutation', 'subscription', 'fragment', 'on', 'true', 'false', 'null'):
                continue

            limit = 1
            if args_str:
                # Check for limit / first: \d+
                limit_match = re.search(r'\b(?:first|limit|take)\s*:\s*(\d+)', args_str)
                if limit_match:
                    limit = int(limit_match.group(1))
            tokens.append((field_name, limit))
        return tokens

    def calculate_query_cost(self, query: str) -> int:
        """Compute the total complexity score of a single GraphQL query."""
        if not query or not query.strip():
            return 0

        # Enforce depth check first
        depth = self.calculate_depth(query)
        if depth > self.max_depth:
            raise GraphQLDepthLimitExceeded(
                f"Query depth {depth} exceeds maximum allowable depth of {self.max_depth}"
            )

        tokens = self._extract_tokens_and_args(query)
        total_cost = 0

        for field_name, multiplier in tokens:
            base_cost = self.custom_field_costs.get(field_name, self.default_field_cost)
            field_cost = base_cost * multiplier
            total_cost += field_cost

        if total_cost > self.max_query_cost:
            raise GraphQLCostLimitExceeded(
                f"Query cost {total_cost} exceeds maximum single query cost of {self.max_query_cost}"
            )

        return total_cost

    def analyze_batch(
        self, batch: List[Union[str, Dict[str, Any]]]
    ) -> Dict[str, Any]:
        """Analyze and validate a batch of GraphQL queries.

        Args:
            batch: List of query strings or dicts with 'query' key (standard GraphQL HTTP batch).

        Returns:
            Dict containing batch metrics (total_cost, queries_analyzed, max_depth_observed).

        Raises:
            GraphQLBatchLimitExceeded: If batch size exceeds limit.
            GraphQLDepthLimitExceeded: If any query exceeds depth limit.
            GraphQLCostLimitExceeded: If single query or batch total cost exceeds limit.
        """
        if len(batch) > self.max_batch_size:
            raise GraphQLBatchLimitExceeded(
                f"Batch query count {len(batch)} exceeds maximum batch limit of {self.max_batch_size}"
            )

        total_cost = 0
        max_depth = 0
        costs_per_query = []

        for item in batch:
            if isinstance(item, dict):
                query_str = item.get("query", "")
            elif isinstance(item, str):
                query_str = item
            else:
                raise GraphQLSyntaxError(f"Unsupported batch query item type: {type(item)}")

            depth = self.calculate_depth(query_str)
            if depth > max_depth:
                max_depth = depth

            # Will raise GraphQLDepthLimitExceeded or GraphQLCostLimitExceeded if violated
            cost = self.calculate_query_cost(query_str)
            costs_per_query.append(cost)
            total_cost += cost

        if total_cost > self.max_batch_cost:
            raise GraphQLCostLimitExceeded(
                f"Batch total cost {total_cost} exceeds maximum allowed batch cost of {self.max_batch_cost}"
            )

        return {
            "valid": True,
            "total_cost": total_cost,
            "query_count": len(batch),
            "max_depth": max_depth,
            "individual_costs": costs_per_query,
        }
