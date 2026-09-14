"""Formal verification harness for cyclic state graph invariants."""

from __future__ import annotations

from packages.state_solver.solver import (
    BidirectionalStateSolver,
    StateNode,
    create_cyclic_chain,
)


def verify_two_node_cyclic_topology() -> bool:
    """Verify bidirectional cyclic resolution between two interconnected nodes."""
    nodes = create_cyclic_chain(["node_a", "node_b"])
    solver = BidirectionalStateSolver(max_depth=10)
    result = solver.resolve(nodes[0])

    if not result.has_cycle:
        return False
    if len(result.resolved_states) != 2:
        return False
    if set(result.visited_order) != {"node_a", "node_b"}:
        return False
    return solver.verify_bidirectional_symmetry(nodes)


def verify_three_node_bidirectional_ring() -> bool:
    """Verify invariant preservation across a three-node bidirectional ring."""
    nodes = create_cyclic_chain(["ring_0", "ring_1", "ring_2"])
    solver = BidirectionalStateSolver(max_depth=10)
    result = solver.resolve(nodes[0])

    if not result.has_cycle:
        return False
    if len(result.resolved_states) != 3:
        return False
    if not solver.verify_bidirectional_symmetry(nodes):
        return False
    return "ring_1" in result.cycle_nodes and "ring_2" in result.cycle_nodes


def verify_depth_boundary_enforcement() -> bool:
    """Verify that resolution terminates strictly at configured maximum depth."""
    node_ids = [f"seq_{idx}" for idx in range(30)]
    nodes = create_cyclic_chain(node_ids)

    shallow_solver = BidirectionalStateSolver(max_depth=3)
    result = shallow_solver.resolve(nodes[0])

    return result.depth_reached <= 3 and len(result.resolved_states) < 30


def verify_acyclic_vs_cyclic_distinction() -> bool:
    """Confirm that an acyclic linear sequence is correctly recognized as non-cyclic."""
    node_0 = StateNode(node_id="root", payload={"step": 0})
    node_1 = StateNode(node_id="leaf", payload={"step": 1})
    node_0.next_node = node_1
    node_1.prev_node = node_0

    solver = BidirectionalStateSolver(max_depth=10)
    result = solver.resolve(node_0)

    if result.has_cycle:
        return False
    return len(result.resolved_states) == 2


def verify_symmetry_invariants() -> bool:
    """Verify detection of asymmetric or broken bidirectional links."""
    nodes = create_cyclic_chain(["x", "y", "z"])
    solver = BidirectionalStateSolver(max_depth=10)

    if not solver.verify_bidirectional_symmetry(nodes):
        return False

    nodes[0].next_node = StateNode(node_id="intruder")
    return not solver.verify_bidirectional_symmetry(nodes)


def verify_fuzzed_cyclic_topologies() -> bool:
    """Verify invariant stability across deterministically generated varied graph sizes."""
    solver = BidirectionalStateSolver(max_depth=15)
    for size in (1, 2, 4, 7, 13):
        node_ids = [f"fuzz_{size}_{idx}" for idx in range(size)]
        nodes = create_cyclic_chain(node_ids)
        result = solver.resolve(nodes[0])
        if len(result.resolved_states) != size:
            return False
        if size > 1 and not result.has_cycle:
            return False
    return True


def run_full_verification() -> bool:
    """Execute complete suite of state invariant verification checks."""
    checks = [
        verify_two_node_cyclic_topology(),
        verify_three_node_bidirectional_ring(),
        verify_depth_boundary_enforcement(),
        verify_acyclic_vs_cyclic_distinction(),
        verify_symmetry_invariants(),
        verify_fuzzed_cyclic_topologies(),
    ]
    return all(checks)


if __name__ == "__main__":
    if not run_full_verification():
        raise SystemExit(1)
