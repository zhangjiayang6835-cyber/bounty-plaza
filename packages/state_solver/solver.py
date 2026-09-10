"""Deterministic bidirectional cyclic state graph resolution engine."""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


@dataclass
class StateNode:
    """Represents a state node within a cyclic topological graph."""

    node_id: str
    payload: Dict[str, Any] = field(default_factory=dict)
    next_node: Optional[StateNode] = None
    prev_node: Optional[StateNode] = None
    compute: Optional[Callable[[], StateNode]] = None

    def __hash__(self) -> int:
        """Hash state node based on identifier."""
        return hash(self.node_id)

    def __eq__(self, other: object) -> bool:
        """Check equality between state nodes."""
        if not isinstance(other, StateNode):
            return False
        return self.node_id == other.node_id


@dataclass(frozen=True)
class StateResolutionResult:
    """Immutable record storing outcomes of state resolution."""

    resolved_states: Dict[str, Dict[str, Any]]
    visited_order: Tuple[str, ...]
    has_cycle: bool
    cycle_nodes: Tuple[str, ...]
    depth_reached: int


@dataclass
class _TraversalState:
    """Internal mutable accumulator holding traversal graph structures."""

    visited: Dict[str, Dict[str, Any]]
    visited_order: List[str]
    cycle_nodes: Set[str]
    queue: collections.deque


class BidirectionalStateSolver:
    """Resolves nested state transitions across bidirectional cyclic topologies."""

    def __init__(self, max_depth: int = 20) -> None:
        """Initialize solver with recursion depth boundary."""
        self._max_depth = max_depth

    @property
    def max_depth(self) -> int:
        """Retrieve solver recursion depth ceiling."""
        return self._max_depth

    @staticmethod
    def _is_reciprocal(
        parent_id: Optional[str],
        entry_dir: Optional[str],
        candidate_id: str,
        edge_dir: str,
    ) -> bool:
        """Check if edge transition is reciprocal return to immediate parent."""
        if parent_id is None or candidate_id != parent_id:
            return False
        if entry_dir == "next" and edge_dir == "prev":
            return True
        return entry_dir == "prev" and edge_dir == "next"

    def _process_candidate(
        self,
        candidate_edge: Tuple[Optional[StateNode], str],
        context: Tuple[StateNode, int, Set[str], Optional[str], Optional[str]],
        state: _TraversalState,
    ) -> None:
        """Evaluate a single candidate node during topological graph traversal."""
        candidate, edge_dir = candidate_edge
        if candidate is None:
            return

        current_node, current_depth, path_nodes, parent_id, entry_dir = context
        if self._is_reciprocal(parent_id, entry_dir, candidate.node_id, edge_dir):
            return

        if candidate.node_id in state.visited:
            state.cycle_nodes.add(candidate.node_id)
            state.cycle_nodes.add(current_node.node_id)
            return

        state.visited[candidate.node_id] = dict(candidate.payload)
        state.visited_order.append(candidate.node_id)
        new_path = set(path_nodes)
        new_path.add(candidate.node_id)
        state.queue.append(
            (candidate, current_depth + 1, new_path, current_node.node_id, edge_dir)
        )

    def resolve(self, root: StateNode) -> StateResolutionResult:
        """Unwrap state transitions across cyclic topology within depth bounds."""
        state = _TraversalState(
            visited={root.node_id: dict(root.payload)},
            visited_order=[root.node_id],
            cycle_nodes=set(),
            queue=collections.deque([(root, 0, {root.node_id}, None, None)]),
        )
        max_observed_depth = 0

        while state.queue:
            context = state.queue.popleft()
            curr_node, curr_depth = context[0], context[1]
            max_observed_depth = max(max_observed_depth, curr_depth)

            if curr_depth >= self._max_depth:
                continue

            for cand_edge in ((curr_node.next_node, "next"), (curr_node.prev_node, "prev")):
                self._process_candidate(cand_edge, context, state)

        return StateResolutionResult(
            resolved_states=state.visited,
            visited_order=tuple(state.visited_order),
            has_cycle=len(state.cycle_nodes) > 0,
            cycle_nodes=tuple(sorted(state.cycle_nodes)),
            depth_reached=max_observed_depth,
        )

    def verify_bidirectional_symmetry(self, nodes: List[StateNode]) -> bool:
        """Confirm that forward and backward connections maintain reciprocal symmetry."""
        for node in nodes:
            if node.next_node is not None:
                neighbor = node.next_node
                if neighbor.prev_node is not None and neighbor.prev_node.node_id != node.node_id:
                    return False
            if node.prev_node is not None:
                predecessor = node.prev_node
                pred_next = predecessor.next_node
                if pred_next is not None and pred_next.node_id != node.node_id:
                    return False
        return True


def create_cyclic_chain(node_ids: List[str]) -> List[StateNode]:
    """Construct a bidirectional cyclic ring from an ordered sequence of identifiers."""
    if not node_ids:
        return []

    nodes = [StateNode(node_id=nid, payload={"idx": idx}) for idx, nid in enumerate(node_ids)]
    total_count = len(nodes)

    for idx, node in enumerate(nodes):
        next_idx = (idx + 1) % total_count
        prev_idx = (idx - 1 + total_count) % total_count
        node.next_node = nodes[next_idx]
        node.prev_node = nodes[prev_idx]
        node.compute = lambda target=node: target

    return nodes


def resolve_cyclic_state(root: StateNode, max_depth: int = 20) -> StateResolutionResult:
    """Execute state unwrapping for a given root node."""
    solver = BidirectionalStateSolver(max_depth=max_depth)
    return solver.resolve(root)


if __name__ == "__main__":
    sample_nodes = create_cyclic_chain(["alpha", "beta", "gamma"])
    outcome = resolve_cyclic_state(sample_nodes[0])
    if not outcome.has_cycle:
        raise SystemExit(1)
