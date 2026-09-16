"""Safe condition evaluation engine for OmniBlocks visual conditional statements."""

import ast
from typing import Any, Callable, Dict, Optional, Union


class ConditionEvaluator:
    """Evaluates conditional expressions safely without dynamic code compilation."""

    SAFE_OPERATORS = {
        ast.Eq: lambda left, right: left == right,
        ast.NotEq: lambda left, right: left != right,
        ast.Lt: lambda left, right: left < right,
        ast.LtE: lambda left, right: left <= right,
        ast.Gt: lambda left, right: left > right,
        ast.GtE: lambda left, right: left >= right,
        ast.Add: lambda left, right: left + right,
        ast.Sub: lambda left, right: left - right,
        ast.Mult: lambda left, right: left * right,
        ast.Div: lambda left, right: left / right if right != 0 else 0,
    }

    def __init__(self, context: Optional[Dict[str, Any]] = None) -> None:
        """Initialize condition evaluator with variable storage context."""
        self.context: Dict[str, Any] = context if context is not None else {}
        self.registered_predicates: Dict[str, Callable[..., bool]] = {}

    def set_variable(self, name: str, value: Any) -> None:
        """Store a variable in evaluation context."""
        self.context[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Retrieve a variable from evaluation context."""
        return self.context.get(name, default)

    def register_predicate(self, name: str, predicate: Callable[..., bool]) -> None:
        """Register a custom condition predicate callback."""
        self.registered_predicates[name] = predicate

    def evaluate(self, condition: Union[str, bool, Callable[[], bool]]) -> bool:
        """Evaluate a boolean condition specification against the current context."""
        if isinstance(condition, bool):
            return condition

        if callable(condition):
            return bool(condition())

        if not isinstance(condition, str):
            return bool(condition)

        normalized = condition.strip()
        if not normalized:
            return False

        if normalized.lower() == "true":
            return True
        if normalized.lower() == "false":
            return False

        if normalized in self.registered_predicates:
            return bool(self.registered_predicates[normalized]())

        if normalized in self.context:
            return bool(self.context[normalized])

        parsed_tree = ast.parse(normalized, mode="eval")
        return bool(self._eval_node(parsed_tree.body))

    def _eval_node(self, node: ast.AST) -> Any:
        """Recursively evaluate approved AST expression nodes."""
        if isinstance(node, ast.Constant):
            return node.value

        if isinstance(node, ast.Name):
            return self._eval_name(node)

        if isinstance(node, ast.UnaryOp):
            return self._eval_unary(node)

        if isinstance(node, ast.BoolOp):
            return self._eval_bool_op(node)

        if isinstance(node, ast.Compare):
            return self._eval_compare(node)

        if isinstance(node, ast.BinOp):
            return self._eval_bin_op(node)

        raise ValueError(f"Unsupported AST node expression: {type(node)}")

    def _eval_name(self, node: ast.Name) -> Any:
        """Resolve identifier name against context or constants."""
        if node.id in self.context:
            return self.context[node.id]
        if node.id.lower() == "true":
            return True
        if node.id.lower() == "false":
            return False
        return False

    def _eval_unary(self, node: ast.UnaryOp) -> Any:
        """Evaluate unary operation node."""
        operand_val = self._eval_node(node.operand)
        if isinstance(node.op, ast.Not):
            return not operand_val
        if isinstance(node.op, ast.USub):
            return -operand_val
        raise ValueError(f"Unsupported unary operator: {type(node.op)}")

    def _eval_bool_op(self, node: ast.BoolOp) -> bool:
        """Evaluate boolean conjunction or disjunction."""
        if isinstance(node.op, ast.And):
            for val_node in node.values:
                if not self._eval_node(val_node):
                    return False
            return True
        if isinstance(node.op, ast.Or):
            for val_node in node.values:
                if self._eval_node(val_node):
                    return True
            return False
        raise ValueError(f"Unsupported boolean operator: {type(node.op)}")

    def _eval_compare(self, node: ast.Compare) -> bool:
        """Evaluate chained relational comparison."""
        left = self._eval_node(node.left)
        for op, comparator in zip(node.ops, node.comparators):
            right = self._eval_node(comparator)
            op_type = type(op)
            if op_type not in self.SAFE_OPERATORS:
                raise ValueError(f"Unsupported comparison operator: {op_type}")
            if not self.SAFE_OPERATORS[op_type](left, right):
                return False
            left = right
        return True

    def _eval_bin_op(self, node: ast.BinOp) -> Any:
        """Evaluate binary arithmetic operator."""
        left_val = self._eval_node(node.left)
        right_val = self._eval_node(node.right)
        bin_op_type = type(node.op)
        if bin_op_type not in self.SAFE_OPERATORS:
            raise ValueError(f"Unsupported binary operator: {bin_op_type}")
        return self.SAFE_OPERATORS[bin_op_type](left_val, right_val)
