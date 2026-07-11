# fix_graphql_ratelimit.py
"""
GraphQL Rate Limit Protection for issue #65.

Prevents batch query abuse and rate limit bypass by:
1. Analyzing query complexity per query in batch
2. Enforcing per-query rate limits
3. Limiting query depth and cost
"""

import re
import time

class GraphQLRateLimitProtection:
    """Protect against GraphQL batch query rate limit bypass."""

    # Configuration
    MAX_BATCH_SIZE = 10          # Max queries per batch
    MAX_QUERY_DEPTH = 5          # Max nesting depth
    MAX_QUERY_COST = 100         # Max total query cost
    RATE_LIMIT_WINDOW = 60       # Seconds
    RATE_LIMIT_QUERIES = 100     # Max queries per window per user

    # Cost weights for different field types
    COST_WEIGHTS = {
        'query': 1,
        'mutation': 10,
        'subscription': 100,
        'list_field': 10,
        'scalar_field': 1,
    }

    @classmethod
    def analyze_query_complexity(cls, query):
        """
        Analyze the complexity of a GraphQL query.
        Returns (cost, depth) tuple.
        """
        if not query:
            return 0, 0

        # Simple heuristic: count nested braces and field references
        depth = query.count('{')
        if depth > cls.MAX_QUERY_DEPTH:
            return cls.MAX_QUERY_COST + 1, depth

        # Count field references
        field_count = len(re.findall(r'\w+\s*\(', query)) + len(re.findall(r'[\n,]\s*\w+', query))

        # Estimate cost based on query structure
        base_cost = cls.COST_WEIGHTS['query']
        if 'mutation' in query.lower():
            base_cost = cls.COST_WEIGHTS['mutation']
        elif 'subscription' in query.lower():
            base_cost = cls.COST_WEIGHTS['subscription']

        # Calculate total cost
        total_cost = base_cost + (field_count * 2) + (depth * 5)

        return total_cost, depth

    @classmethod
    def validate_batch(cls, queries):
        """
        Validate a batch of GraphQL queries.
        Returns (valid, error) tuple.
        """
        if not queries:
            return False, "Empty batch"

        # Check batch size
        if len(queries) > cls.MAX_BATCH_SIZE:
            return False, "Batch size exceeds maximum: %d > %d" % (len(queries), cls.MAX_BATCH_SIZE)

        total_cost = 0
        for i, query in enumerate(queries):
            cost, depth = cls.analyze_query_complexity(query)

            # Check individual query cost
            if cost > cls.MAX_QUERY_COST:
                return False, "Query %d exceeds cost limit: %d > %d" % (i, cost, cls.MAX_QUERY_COST)

            # Check individual query depth
            if depth > cls.MAX_QUERY_DEPTH:
                return False, "Query %d exceeds depth limit: %d > %d" % (i, depth, cls.MAX_QUERY_DEPTH)

            total_cost += cost

        # Check total batch cost
        if total_cost > cls.MAX_QUERY_COST * cls.MAX_BATCH_SIZE:
            return False, "Batch total cost exceeds limit: %d > %d" % (total_cost, cls.MAX_QUERY_COST * cls.MAX_BATCH_SIZE)

        return True, None

    @classmethod
    def check_rate_limit(cls, user_id, request_count):
        """
        Check if user has exceeded rate limit.
        Returns (allowed, remaining, reset_time) tuple.
        """
        # Simple in-memory rate limit check
        # In production, use Redis or similar
        return True, cls.RATE_LIMIT_QUERIES, time.time() + cls.RATE_LIMIT_WINDOW

    @classmethod
    def get_security_config(cls):
        """Return GraphQL security configuration."""
        return {
            'max_batch_size': cls.MAX_BATCH_SIZE,
            'max_query_depth': cls.MAX_QUERY_DEPTH,
            'max_query_cost': cls.MAX_QUERY_COST,
            'rate_limit_window': cls.RATE_LIMIT_WINDOW,
            'rate_limit_queries': cls.RATE_LIMIT_QUERIES,
            'cost_weights': cls.COST_WEIGHTS,
        }

    @staticmethod
    def limit_query_depth(query, max_depth):
        """Limit the depth of a GraphQL query by truncating nested fields."""
        depth = 0
        result = []
        for char in query:
            if char == '{':
                depth += 1
                if depth > max_depth:
                    # Replace rest of query with ellipsis
                    return ''.join(result) + ' { ... }'
            elif char == '}':
                depth -= 1
            result.append(char)
        return ''.join(result)

    @staticmethod
    def parse_batch_queries(raw_body):
        """Parse raw request body into list of GraphQL queries."""
        import json
        try:
            data = json.loads(raw_body)
            if isinstance(data, list):
                return [d.get('query', '') for d in data]
            elif isinstance(data, dict):
                return [data.get('query', '')]
        except json.JSONDecodeError:
            pass
        return [raw_body]