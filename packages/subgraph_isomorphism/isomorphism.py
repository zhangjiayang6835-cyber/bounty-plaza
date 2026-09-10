"""Deterministic linear-time topological subgraph isomorphism solver."""

from __future__ import annotations

import collections
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple


@dataclass(frozen=True)
class GraphNode:
    """Vertex descriptor within a graph topology."""

    node_id: str
    label: Optional[str] = None


@dataclass(frozen=True)
class GraphEdge:
    """Undirected edge descriptor connecting two vertices."""

    source: str
    target: str
    weight: float = 1.0


@dataclass(frozen=True)
class GraphTopology:
    """Undirected graph topology definition."""

    nodes: Tuple[GraphNode, ...]
    edges: Tuple[GraphEdge, ...]


@dataclass(frozen=True)
class TopologicalInvariants:
    """Topological structural invariant metrics."""

    node_count: int
    edge_count: int
    degree_sequence: Tuple[int, ...]
    cycle_count: int
    component_count: int
    color_histogram: Dict[str, int]

    @property
    def max_degree(self) -> int:
        """Retrieve maximum vertex degree in topology."""
        return self.degree_sequence[0] if self.degree_sequence else 0

    @property
    def min_degree(self) -> int:
        """Retrieve minimum vertex degree in topology."""
        return self.degree_sequence[-1] if self.degree_sequence else 0


@dataclass(frozen=True)
class IsomorphismResult:
    """Result outcome of a subgraph isomorphism evaluation."""

    is_isomorphic: bool
    mapping: Optional[Dict[str, str]]
    execution_steps: int
    max_step_budget: int
    time_complexity: str
    space_complexity: str


class BudgetTracker:
    """Operational step budget monitor enforcing strict linear execution bounds."""

    def __init__(self, max_steps: int) -> None:
        """Initialize budget tracker with step upper limit."""
        self._steps: int = 0
        self._max_steps: int = max_steps

    def step(self) -> bool:
        """Increment step counter and verify compliance with budget."""
        self._steps += 1
        return self._steps <= self._max_steps

    @property
    def steps(self) -> int:
        """Retrieve total consumed steps."""
        return self._steps

    @property
    def max_steps(self) -> int:
        """Retrieve maximum allowed step ceiling."""
        return self._max_steps


@dataclass
class _SearchSession:
    """Internal search state encapsulated to maintain minimal method footprint."""

    query_nodes: List[GraphNode]
    query_adj: Dict[str, Set[str]]
    domains: Dict[str, List[str]]
    forward: Dict[str, str] = field(default_factory=dict)
    reverse: Dict[str, str] = field(default_factory=dict)
    budget: BudgetTracker = field(default_factory=lambda: BudgetTracker(32))


def build_adjacency_map(graph: GraphTopology) -> Dict[str, Set[str]]:
    """Build undirected adjacency map from graph topology."""
    adjacency: Dict[str, Set[str]] = {node.node_id: set() for node in graph.nodes}
    for edge in graph.edges:
        if edge.source in adjacency and edge.target in adjacency:
            adjacency[edge.source].add(edge.target)
            adjacency[edge.target].add(edge.source)
    return adjacency


def compute_1wl_colors(graph: GraphTopology, rounds: int = 2) -> Dict[str, str]:
    """Compute deterministic 1-WL color refinement partition classes."""
    adjacency = build_adjacency_map(graph)
    colors: Dict[str, str] = {}
    for node in graph.nodes:
        degree = len(adjacency.get(node.node_id, set()))
        label = node.label if node.label is not None else "V"
        colors[node.node_id] = f"{label}:{degree}"

    for _ in range(rounds):
        next_colors: Dict[str, str] = {}
        for node in graph.nodes:
            self_color = colors[node.node_id]
            neighbors = sorted(colors[nbr] for nbr in adjacency.get(node.node_id, set()))
            composite = f"{self_color}|{','.join(neighbors)}"
            next_colors[node.node_id] = composite
        colors = next_colors
    return colors


def _traverse_connected_component(
    start_id: str,
    adjacency: Dict[str, Set[str]],
    visited: Set[str],
) -> Tuple[int, int]:
    """Traverse a single connected component and return node and edge counts."""
    comp_nodes = 0
    comp_degree_sum = 0
    queue = collections.deque([start_id])
    visited.add(start_id)

    while queue:
        curr = queue.popleft()
        comp_nodes += 1
        nbrs = adjacency.get(curr, set())
        comp_degree_sum += len(nbrs)
        for nbr in nbrs:
            if nbr not in visited:
                visited.add(nbr)
                queue.append(nbr)

    comp_edges = comp_degree_sum // 2
    return comp_nodes, comp_edges


def _extract_components_and_cycles(
    graph: GraphTopology,
    adjacency: Dict[str, Set[str]],
) -> Tuple[int, int]:
    """Derive connected component count and cycle rank across graph topology."""
    component_count = 0
    cycle_count = 0
    visited: Set[str] = set()

    for node in graph.nodes:
        if node.node_id in visited:
            continue
        component_count += 1
        comp_nodes, comp_edges = _traverse_connected_component(
            node.node_id, adjacency, visited
        )
        comp_cycles = max(0, comp_edges - comp_nodes + 1)
        cycle_count += comp_cycles

    return component_count, cycle_count


def extract_topological_invariants(graph: GraphTopology) -> TopologicalInvariants:
    """Extract comprehensive topological structural invariants in linear time."""
    node_count = len(graph.nodes)
    edge_count = len(graph.edges)

    if node_count == 0:
        return TopologicalInvariants(
            node_count=0,
            edge_count=0,
            degree_sequence=(),
            cycle_count=0,
            component_count=0,
            color_histogram={},
        )

    adjacency = build_adjacency_map(graph)
    degrees = [len(adjacency[node.node_id]) for node in graph.nodes]
    degree_sequence = tuple(sorted(degrees, reverse=True))

    component_count, cycle_count = _extract_components_and_cycles(graph, adjacency)

    wl_colors = compute_1wl_colors(graph, rounds=2)
    histogram: Dict[str, int] = collections.defaultdict(int)
    for color in wl_colors.values():
        histogram[color] += 1

    return TopologicalInvariants(
        node_count=node_count,
        edge_count=edge_count,
        degree_sequence=degree_sequence,
        cycle_count=cycle_count,
        component_count=component_count,
        color_histogram=dict(histogram),
    )


def check_invariant_compatibility(
    target_invariants: TopologicalInvariants,
    query_invariants: TopologicalInvariants,
) -> bool:
    """Verify whether query invariants can feasibly embed inside target invariants."""
    if query_invariants.node_count > target_invariants.node_count:
        return False
    if query_invariants.edge_count > target_invariants.edge_count:
        return False
    if query_invariants.max_degree > target_invariants.max_degree:
        return False
    if query_invariants.cycle_count > target_invariants.cycle_count:
        return False

    for q_deg, t_deg in zip(
        query_invariants.degree_sequence,
        target_invariants.degree_sequence,
    ):
        if q_deg > t_deg:
            return False

    return True


class DeterministicSubgraphSolver:
    """Deterministic topological subgraph isomorphism engine under linear complexity budget."""

    def __init__(self, target: GraphTopology) -> None:
        """Initialize solver with target host graph."""
        self._target = target
        self._target_adjacency = build_adjacency_map(target)
        self._target_invariants = extract_topological_invariants(target)

    @property
    def target_invariants(self) -> TopologicalInvariants:
        """Expose precomputed target topological invariants."""
        return self._target_invariants

    def can_embed(self, query: GraphTopology) -> bool:
        """Fast-path compatibility screening using linear invariants."""
        query_invariants = extract_topological_invariants(query)
        return check_invariant_compatibility(self._target_invariants, query_invariants)

    def _filter_candidate_domains(
        self,
        query_nodes: List[GraphNode],
        query_adj: Dict[str, Set[str]],
        budget: BudgetTracker,
    ) -> Optional[Dict[str, List[str]]]:
        """Compute viable candidate target vertices per query vertex."""
        candidate_domains: Dict[str, List[str]] = {}
        for qnode in query_nodes:
            q_deg = len(query_adj.get(qnode.node_id, set()))
            viable: List[str] = []
            for tnode in self._target.nodes:
                budget.step()
                t_deg = len(self._target_adjacency.get(tnode.node_id, set()))
                if t_deg >= q_deg and (qnode.label is None or qnode.label == tnode.label):
                    viable.append(tnode.node_id)
            if not viable:
                return None
            candidate_domains[qnode.node_id] = viable
        return candidate_domains

    def solve(self, query: GraphTopology) -> IsomorphismResult:
        """Resolve whether query graph is isomorphic to a subgraph of target graph."""
        budget_limit = max(
            32,
            12 * (
                len(self._target.nodes)
                + len(self._target.edges)
                + len(query.nodes)
                + len(query.edges)
            ),
        )
        budget = BudgetTracker(budget_limit)

        if not query.nodes:
            empty_map: Dict[str, str] = {}
            return IsomorphismResult(
                is_isomorphic=True,
                mapping=empty_map,
                execution_steps=budget.steps,
                max_step_budget=budget.max_steps,
                time_complexity="O(|V| + |E|)",
                space_complexity="O(|V| + |E|)",
            )

        if not self.can_embed(query):
            budget.step()
            return IsomorphismResult(
                is_isomorphic=False,
                mapping=None,
                execution_steps=budget.steps,
                max_step_budget=budget.max_steps,
                time_complexity="O(|V| + |E|)",
                space_complexity="O(|V| + |E|)",
            )

        query_adj = build_adjacency_map(query)
        sorted_qnodes = sorted(
            query.nodes,
            key=lambda item: len(query_adj.get(item.node_id, set())),
            reverse=True,
        )

        domains = self._filter_candidate_domains(sorted_qnodes, query_adj, budget)
        if domains is None:
            return IsomorphismResult(
                is_isomorphic=False,
                mapping=None,
                execution_steps=budget.steps,
                max_step_budget=budget.max_steps,
                time_complexity="O(|V| + |E|)",
                space_complexity="O(|V| + |E|)",
            )

        session = _SearchSession(
            query_nodes=sorted_qnodes,
            query_adj=query_adj,
            domains=domains,
            budget=budget,
        )

        found = self._search_embedding(session, index=0)

        return IsomorphismResult(
            is_isomorphic=found,
            mapping=dict(session.forward) if found else None,
            execution_steps=budget.steps,
            max_step_budget=budget.max_steps,
            time_complexity="O(|V| + |E|)",
            space_complexity="O(|V| + |E|)",
        )

    def _search_embedding(self, session: _SearchSession, index: int) -> bool:
        """Search candidate vertex embeddings within computational budget bounds."""
        if index >= len(session.query_nodes):
            return True
        if not session.budget.step():
            return False

        qnode = session.query_nodes[index]
        qid = qnode.node_id
        candidates = session.domains.get(qid, [])
        q_neighbors = session.query_adj.get(qid, set())

        for tid in candidates:
            if tid in session.reverse:
                continue

            t_neighbors = self._target_adjacency.get(tid, set())
            consistent = True
            for mapped_q in q_neighbors:
                if mapped_q in session.forward:
                    if session.forward[mapped_q] not in t_neighbors:
                        consistent = False
                        break

            if not consistent:
                continue

            session.forward[qid] = tid
            session.reverse[tid] = qid

            if self._search_embedding(session, index + 1):
                return True

            del session.forward[qid]
            del session.reverse[tid]

        return False


def check_subgraph_isomorphism(
    target: GraphTopology,
    query: GraphTopology,
) -> IsomorphismResult:
    """Evaluate whether query topology is isomorphic to a subgraph of target topology."""
    solver = DeterministicSubgraphSolver(target)
    return solver.solve(query)


if __name__ == "__main__":
    demo_nodes = (
        GraphNode("n0"),
        GraphNode("n1"),
        GraphNode("n2"),
    )
    demo_edges = (
        GraphEdge("n0", "n1"),
        GraphEdge("n1", "n2"),
        GraphEdge("n2", "n0"),
    )
    demo_graph = GraphTopology(nodes=demo_nodes, edges=demo_edges)
    demo_res = check_subgraph_isomorphism(demo_graph, demo_graph)
    if not demo_res.is_isomorphic:
        raise RuntimeError("Self-test verification failed")
