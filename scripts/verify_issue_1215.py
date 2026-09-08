"""Verification script for Issue #1215 Turing Decider implementation."""

import sys
from packages.turing_decider.consensus_decider import DeterministicConsensusDecider
from packages.turing_decider.graph_analyzer import (
    ASTTerminationAnalyzer,
    DAGCycleDetector,
)
from packages.turing_decider.models import (
    ComputationalNode,
    ExecutionBudget,
)
from packages.turing_decider.proof_verifier import (
    TuringUndecidabilityProofVerifier,
)


def verify_implementation() -> bool:
    """Executes verification suite across models, graph analysis, and proofs.

    :return: True if all verifications pass cleanly, False otherwise.
    """
    invariant = TuringUndecidabilityProofVerifier.verify_undecidability_theorem()
    paradox = TuringUndecidabilityProofVerifier.simulate_diagonal_paradox()
    theorem_ok = invariant.undecidable and ("contradiction" in paradox["case_halts"]["result"])

    nodes = {
        "A": ComputationalNode(node_id="A", dependencies=[], computation=lambda inp: 21),
        "B": ComputationalNode(
            node_id="B", dependencies=["A"], computation=lambda inp: inp["A"] * 2
        ),
    }
    validation = DAGCycleDetector.validate_graph(nodes)
    decider = DeterministicConsensusDecider(default_budget=ExecutionBudget())
    decision = decider.evaluate_graph(nodes)
    graph_ok = (
        validation.is_dag
        and decision.will_halt
        and (decision.execution_output.get("B") == 42)
        and (decision.tokens_consumed == 0)
    )

    valid_loop = ASTTerminationAnalyzer.analyze_source("for x in range(10): pass")
    infinite_loop = ASTTerminationAnalyzer.analyze_source("while True: pass")
    ast_ok = valid_loop and (not infinite_loop)

    all_passed = theorem_ok and graph_ok and ast_ok
    if all_passed:
        print("Verified Issue #1215 Turing Decider: all invariants passed.")
    return all_passed


if __name__ == "__main__":
    success = verify_implementation()
    sys.exit(0 if success else 1)
