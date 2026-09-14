"""Comprehensive pytest test suite for issue #1332 recursive state solver."""

from __future__ import annotations

from packages.state_solver.solver import (
    BidirectionalStateSolver,
    StateNode,
    create_cyclic_chain,
    resolve_cyclic_state,
)
from packages.state_solver.verifier import (
    run_full_verification,
    verify_acyclic_vs_cyclic_distinction,
    verify_depth_boundary_enforcement,
    verify_fuzzed_cyclic_topologies,
    verify_symmetry_invariants,
    verify_three_node_bidirectional_ring,
    verify_two_node_cyclic_topology,
)


def test_two_node_cyclic_topology() -> None:
    """Verify bidirectional cyclic resolution between two interconnected nodes."""
    assert verify_two_node_cyclic_topology() is True


def test_three_node_bidirectional_ring() -> None:
    """Verify invariant preservation across a three-node bidirectional ring."""
    assert verify_three_node_bidirectional_ring() is True


def test_depth_boundary_enforcement() -> None:
    """Verify that resolution terminates strictly at configured maximum depth."""
    assert verify_depth_boundary_enforcement() is True


def test_acyclic_vs_cyclic_distinction() -> None:
    """Confirm that an acyclic linear sequence is correctly recognized as non-cyclic."""
    assert verify_acyclic_vs_cyclic_distinction() is True


def test_symmetry_invariants() -> None:
    """Verify detection of asymmetric or broken bidirectional links."""
    assert verify_symmetry_invariants() is True


def test_fuzzed_cyclic_topologies() -> None:
    """Verify invariant stability across deterministically generated varied graph sizes."""
    assert verify_fuzzed_cyclic_topologies() is True


def test_full_verification_runner() -> None:
    """Execute complete suite of state invariant verification checks."""
    assert run_full_verification() is True


def test_single_node_self_loop() -> None:
    """Verify that a state node with self-referential pointer is resolved with cycle detected."""
    node = StateNode(node_id="singleton", payload={"metric": 42})
    node.next_node = node
    solver = BidirectionalStateSolver(max_depth=5)
    result = solver.resolve(node)

    assert result.has_cycle is True
    assert "singleton" in result.resolved_states
    assert result.resolved_states["singleton"]["metric"] == 42


def test_state_node_equality_and_hash() -> None:
    """Verify StateNode equality semantics and set/dict membership behavior."""
    node_a = StateNode(node_id="target", payload={"tag": "a"})
    node_b = StateNode(node_id="target", payload={"tag": "b"})
    node_c = StateNode(node_id="other", payload={"tag": "a"})

    assert node_a == node_b
    assert node_a != node_c
    assert node_a != "non_node_object"
    assert hash(node_a) == hash(node_b)

    node_set = {node_a, node_b, node_c}
    assert len(node_set) == 2


def test_resolve_cyclic_state_convenience_function() -> None:
    """Verify convenience entrypoint resolve_cyclic_state matches solver behavior."""
    nodes = create_cyclic_chain(["c0", "c1"])
    result = resolve_cyclic_state(nodes[0], max_depth=8)

    assert result.has_cycle is True
    assert len(result.resolved_states) == 2
    assert result.visited_order == ("c0", "c1")


def test_empty_chain_creation() -> None:
    """Verify handling of empty identifier lists when building cyclic chains."""
    empty_nodes = create_cyclic_chain([])
    assert len(empty_nodes) == 0
