"""Graph topology validation and static AST termination analysis."""

import ast
from collections import deque
from typing import Dict, List, Set
from packages.turing_decider.models import ComputationalNode, GraphValidationResult


class DAGCycleDetector:
    """Detects cycles and computes topological orderings for computational graphs."""

    @staticmethod
    def validate_graph(nodes: Dict[str, ComputationalNode]) -> GraphValidationResult:
        """Determines whether the provided graph is a Directed Acyclic Graph.

        :param nodes: Dictionary mapping node identifiers to node definitions.
        :return: GraphValidationResult containing DAG status, ordering, or cycles.
        """
        in_degrees: Dict[str, int] = {node_id: 0 for node_id in nodes}
        adjacency: Dict[str, List[str]] = {node_id: [] for node_id in nodes}

        for node_id, node in nodes.items():
            for dep in node.dependencies:
                if dep not in nodes:
                    return GraphValidationResult(
                        is_dag=False,
                        topological_order=[],
                        cycles_detected=[[dep, node_id]],
                    )
                adjacency[dep].append(node_id)
                in_degrees[node_id] += 1

        queue: deque[str] = deque([node_id for node_id, deg in in_degrees.items() if deg == 0])
        ordered: List[str] = []

        while queue:
            current = queue.popleft()
            ordered.append(current)
            for neighbor in adjacency[current]:
                in_degrees[neighbor] -= 1
                if in_degrees[neighbor] == 0:
                    queue.append(neighbor)

        if len(ordered) == len(nodes):
            return GraphValidationResult(
                is_dag=True,
                topological_order=ordered,
                cycles_detected=[],
            )

        unresolved: Set[str] = set(nodes.keys()) - set(ordered)
        cycle_components: List[List[str]] = [[node_id] for node_id in sorted(unresolved)]
        return GraphValidationResult(
            is_dag=False,
            topological_order=[],
            cycles_detected=cycle_components,
        )

    @classmethod
    def has_cycle(cls, nodes: Dict[str, ComputationalNode]) -> bool:
        """Checks if the dependency graph contains any cyclic dependencies.

        :param nodes: Dictionary mapping node identifiers to node definitions.
        :return: True if a cycle exists, False if the graph is a strict DAG.
        """
        return not cls.validate_graph(nodes).is_dag


class ASTTerminationAnalyzer:
    """Performs static syntax tree inspection to detect non-terminating code structures."""

    @staticmethod
    def analyze_source(source_code: str) -> bool:
        """Inspects source code for obvious non-terminating constructs.

        :param source_code: String of Python source code to inspect.
        :return: False if an infinite loop without break is found, True otherwise.
        """
        try:
            tree = ast.parse(source_code)
        except SyntaxError:
            return False

        for node in ast.walk(tree):
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and bool(node.test.value) is True:
                    has_break = any(isinstance(child, ast.Break) for child in ast.walk(node))
                    if not has_break:
                        return False
        return True

    @classmethod
    def detect_infinite_loops(cls, source_code: str) -> bool:
        """Detects whether source code contains unconstrained infinite loops.

        :param source_code: Python source string.
        :return: True if unconstrained loop detected, False otherwise.
        """
        return not cls.analyze_source(source_code)
