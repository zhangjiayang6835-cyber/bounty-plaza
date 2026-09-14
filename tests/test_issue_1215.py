"""Unit and integration test suite for Issue #1215 Turing Decider."""

import pytest
from packages.turing_decider.consensus_decider import DeterministicConsensusDecider
from packages.turing_decider.graph_analyzer import (
    ASTTerminationAnalyzer,
    DAGCycleDetector,
)
from packages.turing_decider.models import (
    ComputationalNode,
    ExecutionBudget,
    HaltingDecision,
    ProofInvariant,
)
from packages.turing_decider.proof_verifier import (
    TuringUndecidabilityProofVerifier,
)


def test_models_instantiation():
    """Verifies that core data models initialize with valid properties."""
    budget = ExecutionBudget(max_steps=500, max_gas=20000, timeout_seconds=1.5)
    assert budget.max_steps == 500
    assert budget.max_gas == 20000
    assert budget.timeout_seconds == 1.5

    node = ComputationalNode(node_id="test_node", dependencies=["dep1"], gas_cost=15)
    assert node.node_id == "test_node"
    assert node.dependencies == ["dep1"]
    assert node.gas_cost == 15

    decision = HaltingDecision(
        will_halt=True,
        reason="Completed successfully",
        steps_consumed=5,
        gas_consumed=50,
        tokens_consumed=0,
        execution_output=100,
    )
    assert decision.will_halt is True
    assert decision.tokens_consumed == 0
    assert decision.execution_output == 100


def test_dag_linear_graph_validation():
    """Verifies that a linear dependency graph is recognized as a valid DAG."""
    nodes = {
        "A": ComputationalNode(node_id="A", dependencies=[]),
        "B": ComputationalNode(node_id="B", dependencies=["A"]),
        "C": ComputationalNode(node_id="C", dependencies=["B"]),
    }
    result = DAGCycleDetector.validate_graph(nodes)
    assert result.is_dag is True
    assert result.topological_order == ["A", "B", "C"]
    assert len(result.cycles_detected) == 0


def test_dag_diamond_graph_validation():
    """Verifies that a diamond-shaped dependency graph is recognized as a valid DAG."""
    nodes = {
        "root": ComputationalNode(node_id="root", dependencies=[]),
        "left": ComputationalNode(node_id="left", dependencies=["root"]),
        "right": ComputationalNode(node_id="right", dependencies=["root"]),
        "sink": ComputationalNode(node_id="sink", dependencies=["left", "right"]),
    }
    result = DAGCycleDetector.validate_graph(nodes)
    assert result.is_dag is True
    assert len(result.topological_order) == 4
    assert result.topological_order[0] == "root"
    assert result.topological_order[-1] == "sink"


def test_dag_cycle_detection():
    """Verifies that cyclic graph dependencies are accurately detected as non-halting."""
    nodes = {
        "node1": ComputationalNode(node_id="node1", dependencies=["node2"]),
        "node2": ComputationalNode(node_id="node2", dependencies=["node1"]),
    }
    result = DAGCycleDetector.validate_graph(nodes)
    assert result.is_dag is False
    assert len(result.topological_order) == 0
    assert len(result.cycles_detected) > 0


def test_dag_missing_dependency():
    """Verifies that dependencies pointing to non-existent nodes fail validation."""
    nodes = {
        "worker": ComputationalNode(node_id="worker", dependencies=["missing_parent"]),
    }
    result = DAGCycleDetector.validate_graph(nodes)
    assert result.is_dag is False
    assert result.cycles_detected == [["missing_parent", "worker"]]


def test_ast_analyzer_finite_loop():
    """Verifies that static analysis recognizes terminating loops."""
    code = "def compute(n):\n    total = 0\n    for i in range(n):\n        total += i\n    return total"
    assert ASTTerminationAnalyzer.analyze_source(code) is True


def test_ast_analyzer_while_true_no_break():
    """Verifies that static analysis detects infinite while loops lacking break statements."""
    code = "def infinite_loop():\n    while True:\n        x = 1\n    return x"
    assert ASTTerminationAnalyzer.analyze_source(code) is False


def test_ast_analyzer_while_true_with_break():
    """Verifies that static analysis allows while loops with explicit break statements."""
    code = "def bounded_loop():\n    while True:\n        break\n    return 0"
    assert ASTTerminationAnalyzer.analyze_source(code) is True


def test_ast_analyzer_syntax_error():
    """Verifies that unparseable syntax safely evaluates to False."""
    code = "def broken(:\n    return 0"
    assert ASTTerminationAnalyzer.analyze_source(code) is False


def test_consensus_decider_terminating_function():
    """Verifies deterministic evaluation of terminating Python callables."""
    decider = DeterministicConsensusDecider()
    decision = decider.evaluate_function(lambda x, y: x * y + 7, args=(6, 7))
    assert decision.will_halt is True
    assert decision.execution_output == 49
    assert decision.tokens_consumed == 0


def test_consensus_decider_recursion_error():
    """Verifies that infinite recursion triggers a clean non-halting decision."""
    decider = DeterministicConsensusDecider()

    def unbounded_recursion(n):
        return unbounded_recursion(n + 1)

    decision = decider.evaluate_function(unbounded_recursion, args=(1,))
    assert decision.will_halt is False
    assert "recursion" in decision.reason.lower()


def test_consensus_decider_exception_handling():
    """Verifies that runtime exceptions are handled cleanly without crashing the decider."""
    decider = DeterministicConsensusDecider()

    def faulty_function():
        return 1 / 0

    decision = decider.evaluate_function(faulty_function)
    assert decision.will_halt is False
    assert "abnormally" in decision.reason


def test_consensus_decider_graph_execution_success():
    """Verifies end-to-end execution of a computational DAG with node outputs."""
    nodes = {
        "A": ComputationalNode(
            node_id="A",
            dependencies=[],
            computation=lambda inputs: 10,
            gas_cost=20,
        ),
        "B": ComputationalNode(
            node_id="B",
            dependencies=["A"],
            computation=lambda inputs: inputs["A"] * 3,
            gas_cost=30,
        ),
        "C": ComputationalNode(
            node_id="C",
            dependencies=["B"],
            computation=lambda inputs: inputs["B"] + 12,
            gas_cost=40,
        ),
    }
    decider = DeterministicConsensusDecider()
    decision = decider.evaluate_graph(nodes)
    assert decision.will_halt is True
    assert decision.execution_output["A"] == 10
    assert decision.execution_output["B"] == 30
    assert decision.execution_output["C"] == 42
    assert decision.gas_consumed == 90
    assert decision.tokens_consumed == 0


def test_consensus_decider_graph_execution_cycle():
    """Verifies that evaluate_graph rejects cyclic structures immediately."""
    nodes = {
        "X": ComputationalNode(node_id="X", dependencies=["Y"]),
        "Y": ComputationalNode(node_id="Y", dependencies=["X"]),
    }
    decider = DeterministicConsensusDecider()
    decision = decider.evaluate_graph(nodes)
    assert decision.will_halt is False
    assert "cyclic" in decision.reason.lower()


def test_consensus_decider_gas_limit_exhausted():
    """Verifies that computations exceeding consensus gas limit halt with limit error."""
    nodes = {
        "heavy1": ComputationalNode(node_id="heavy1", dependencies=[], gas_cost=500),
        "heavy2": ComputationalNode(node_id="heavy2", dependencies=["heavy1"], gas_cost=600),
    }
    budget = ExecutionBudget(max_gas=800)
    decider = DeterministicConsensusDecider(default_budget=budget)
    decision = decider.evaluate_graph(nodes)
    assert decision.will_halt is False
    assert "gas limit" in decision.reason.lower()


def test_proof_verifier_undecidability():
    """Verifies the formal invariant of the Halting Problem proof."""
    invariant = TuringUndecidabilityProofVerifier.verify_undecidability_theorem()
    assert isinstance(invariant, ProofInvariant)
    assert invariant.undecidable is True
    assert invariant.diagonal_paradox_verified is True
    assert "1936" in invariant.theorem_name
    assert "gas" in invariant.consensus_architecture.lower()


def test_proof_verifier_diagonal_paradox():
    """Verifies the mathematical contradiction modeling in the diagonal paradox."""
    paradox = TuringUndecidabilityProofVerifier.simulate_diagonal_paradox()
    assert paradox["case_halts"]["result"] == "contradiction"
    assert paradox["case_loops"]["result"] == "contradiction"
    assert "disproven" in paradox["conclusion"]


def test_proof_verifier_zero_tokens():
    """Verifies that decision objects satisfy the zero LLM token consumption invariant."""
    decision = HaltingDecision(
        will_halt=True,
        reason="Success",
        steps_consumed=1,
        gas_consumed=10,
        tokens_consumed=0,
    )
    assert TuringUndecidabilityProofVerifier.verify_zero_token_consumption(decision) is True
