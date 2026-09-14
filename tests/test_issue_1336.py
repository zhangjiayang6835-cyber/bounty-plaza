"""Comprehensive pytest test suite for issue #1336 topological isomorphism solver."""

from __future__ import annotations

from typing import Tuple

from packages.subgraph_isomorphism.isomorphism import (
    BudgetTracker,
    GraphEdge,
    GraphNode,
    GraphTopology,
    check_invariant_compatibility,
    check_subgraph_isomorphism,
    compute_1wl_colors,
    extract_topological_invariants,
)
from packages.subgraph_isomorphism.verifier import (
    create_bipartite_target,
    create_cyclic_target,
    create_triangle_query,
    run_full_verification,
)


def test_cyclic_target_invariants() -> None:
    """Verify invariant extraction metrics on cyclic target graph."""
    target = create_cyclic_target()
    invariants = extract_topological_invariants(target)
    assert invariants.node_count == 5
    assert invariants.edge_count == 6
    assert invariants.cycle_count == 2
    assert invariants.component_count == 1
    assert invariants.max_degree == 3
    assert invariants.min_degree == 2


def test_1wl_coloring_partitions() -> None:
    """Verify 1-WL color refinement partitions vertices deterministically."""
    target = create_cyclic_target()
    colors = compute_1wl_colors(target, rounds=3)
    assert len(colors) == 5
    assert colors["t0"] == colors["t2"]
    assert colors["t0"] != colors["t1"]


def test_subgraph_isomorphism_triangle_in_cyclic() -> None:
    """Verify triangle subgraph discovery within cyclic target graph."""
    target = create_cyclic_target()
    query = create_triangle_query()
    result = check_subgraph_isomorphism(target, query)
    assert result.is_isomorphic is True
    assert result.mapping is not None
    assert len(result.mapping) == 3
    assert result.execution_steps <= result.max_step_budget
    assert result.time_complexity == "O(|V| + |E|)"
    assert result.space_complexity == "O(|V| + |E|)"


def test_subgraph_isomorphism_bipartite_rejection() -> None:
    """Verify deterministic rejection of triangle query in bipartite target."""
    target = create_bipartite_target()
    query = create_triangle_query()
    result = check_subgraph_isomorphism(target, query)
    assert result.is_isomorphic is False
    assert result.mapping is None


def test_subgraph_isomorphism_empty_query() -> None:
    """Verify empty query subgraph evaluation handling."""
    target = create_cyclic_target()
    empty_nodes: Tuple[GraphNode, ...] = ()
    empty_edges: Tuple[GraphEdge, ...] = ()
    empty_query = GraphTopology(nodes=empty_nodes, edges=empty_edges)
    result = check_subgraph_isomorphism(target, empty_query)
    assert result.is_isomorphic is True
    assert result.mapping is not None
    assert len(result.mapping) == 0


def test_subgraph_isomorphism_c4_in_cyclic() -> None:
    """Verify discovery of 4-cycle subgraph in 4-vertex cyclic graph."""
    target_nodes = (
        GraphNode("n0"),
        GraphNode("n1"),
        GraphNode("n2"),
        GraphNode("n3"),
    )
    target_edges = (
        GraphEdge("n0", "n1"),
        GraphEdge("n1", "n2"),
        GraphEdge("n2", "n3"),
        GraphEdge("n3", "n0"),
    )
    target = GraphTopology(nodes=target_nodes, edges=target_edges)

    query_nodes = (
        GraphNode("x0"),
        GraphNode("x1"),
        GraphNode("x2"),
        GraphNode("x3"),
    )
    query_edges = (
        GraphEdge("x0", "x1"),
        GraphEdge("x1", "x2"),
        GraphEdge("x2", "x3"),
        GraphEdge("x3", "x0"),
    )
    query = GraphTopology(nodes=query_nodes, edges=query_edges)

    result = check_subgraph_isomorphism(target, query)
    assert result.is_isomorphic is True
    assert result.mapping is not None
    assert len(result.mapping) == 4


def test_invariant_compatibility_screening() -> None:
    """Verify that incompatible query graph sizes are deterministically rejected."""
    target = create_triangle_query()
    query = create_cyclic_target()
    t_inv = extract_topological_invariants(target)
    q_inv = extract_topological_invariants(query)
    assert check_invariant_compatibility(t_inv, q_inv) is False


def test_budget_tracker_enforcement() -> None:
    """Verify BudgetTracker step counting and budget limit compliance."""
    tracker = BudgetTracker(max_steps=5)
    assert tracker.max_steps == 5
    for _ in range(5):
        assert tracker.step() is True
    assert tracker.steps == 5
    assert tracker.step() is False
    assert tracker.steps == 6


def test_run_full_verification() -> None:
    """Verify execution of full verification harness from verifier module."""
    assert run_full_verification() is True


def test_labeled_vertices_embedding() -> None:
    """Verify that node labels are strictly enforced during embedding."""
    target_nodes = (
        GraphNode("t0", label="ALPHA"),
        GraphNode("t1", label="BETA"),
    )
    target_edges = (GraphEdge("t0", "t1"),)
    target = GraphTopology(nodes=target_nodes, edges=target_edges)

    query_nodes = (
        GraphNode("q0", label="ALPHA"),
        GraphNode("q1", label="GAMMA"),
    )
    query_edges = (GraphEdge("q0", "q1"),)
    query = GraphTopology(nodes=query_nodes, edges=query_edges)

    result = check_subgraph_isomorphism(target, query)
    assert result.is_isomorphic is False
