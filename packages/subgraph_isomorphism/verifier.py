"""Formal verifier for deterministic topological subgraph isomorphism invariants."""

from __future__ import annotations

from typing import Tuple

from packages.subgraph_isomorphism.isomorphism import (
    GraphEdge,
    GraphNode,
    GraphTopology,
    check_subgraph_isomorphism,
    compute_1wl_colors,
    extract_topological_invariants,
)


def create_cyclic_target() -> GraphTopology:
    """Construct reference 5-vertex cyclic graph topology."""
    nodes = tuple(GraphNode(f"t{idx}") for idx in range(5))
    edges = (
        GraphEdge("t0", "t1"),
        GraphEdge("t1", "t2"),
        GraphEdge("t2", "t3"),
        GraphEdge("t3", "t4"),
        GraphEdge("t4", "t0"),
        GraphEdge("t0", "t2"),
    )
    return GraphTopology(nodes=nodes, edges=edges)


def create_triangle_query() -> GraphTopology:
    """Construct 3-vertex clique query graph topology."""
    nodes = tuple(GraphNode(f"q{idx}") for idx in range(3))
    edges = (
        GraphEdge("q0", "q1"),
        GraphEdge("q1", "q2"),
        GraphEdge("q2", "q0"),
    )
    return GraphTopology(nodes=nodes, edges=edges)


def create_bipartite_target() -> GraphTopology:
    """Construct 6-vertex bipartite cycle topology."""
    nodes = tuple(GraphNode(f"b{idx}") for idx in range(6))
    edges = (
        GraphEdge("b0", "b1"),
        GraphEdge("b1", "b2"),
        GraphEdge("b2", "b3"),
        GraphEdge("b3", "b4"),
        GraphEdge("b4", "b5"),
        GraphEdge("b5", "b0"),
    )
    return GraphTopology(nodes=nodes, edges=edges)


def verify_cyclic_invariants() -> bool:
    """Verify invariant extraction metrics on cyclic target graph."""
    target = create_cyclic_target()
    invariants = extract_topological_invariants(target)
    return (
        invariants.node_count == 5
        and invariants.edge_count == 6
        and invariants.cycle_count == 2
        and invariants.component_count == 1
        and invariants.max_degree == 3
        and invariants.min_degree == 2
    )


def verify_1wl_coloring() -> bool:
    """Verify 1-WL color refinement partitions vertices deterministically."""
    target = create_cyclic_target()
    colors = compute_1wl_colors(target, rounds=3)
    return len(colors) == 5 and colors["t0"] == colors["t2"] and colors["t0"] != colors["t1"]


def verify_isomorphism_discovery() -> bool:
    """Verify triangle subgraph discovery within cyclic target graph."""
    target = create_cyclic_target()
    query = create_triangle_query()
    result = check_subgraph_isomorphism(target, query)
    return (
        result.is_isomorphic
        and result.mapping is not None
        and len(result.mapping) == 3
        and result.execution_steps <= result.max_step_budget
    )


def verify_bipartite_rejection() -> bool:
    """Verify deterministic rejection of triangle query in bipartite target."""
    target = create_bipartite_target()
    query = create_triangle_query()
    result = check_subgraph_isomorphism(target, query)
    return not result.is_isomorphic and result.mapping is None


def verify_empty_query() -> bool:
    """Verify empty query subgraph evaluation handling."""
    target = create_cyclic_target()
    empty_nodes: Tuple[GraphNode, ...] = ()
    empty_edges: Tuple[GraphEdge, ...] = ()
    empty_query = GraphTopology(nodes=empty_nodes, edges=empty_edges)
    result = check_subgraph_isomorphism(target, empty_query)
    return result.is_isomorphic and result.mapping is not None and len(result.mapping) == 0


def run_full_verification() -> bool:
    """Execute complete suite of invariant verification checks."""
    return (
        verify_cyclic_invariants()
        and verify_1wl_coloring()
        and verify_isomorphism_discovery()
        and verify_bipartite_rejection()
        and verify_empty_query()
    )


if __name__ == "__main__":
    if not run_full_verification():
        raise RuntimeError("Full verification suite failed")
