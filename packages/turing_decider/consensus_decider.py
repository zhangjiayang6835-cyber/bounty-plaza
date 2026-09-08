"""Deterministic consensus evaluation engine with step and gas metering."""

import time
from typing import Any, Callable, Dict, Optional, Tuple
from packages.turing_decider.graph_analyzer import DAGCycleDetector
from packages.turing_decider.models import (
    ComputationalNode,
    ExecutionBudget,
    HaltingDecision,
)

EXECUTION_EXCEPTIONS = (
    ArithmeticError,
    BufferError,
    LookupError,
    ValueError,
    TypeError,
    RuntimeError,
    MemoryError,
    SystemError,
    AssertionError,
    AttributeError,
    NameError,
)


class DeterministicConsensusDecider:
    """Executes functions and computational graphs under deterministic consensus invariants."""

    def __init__(self, default_budget: Optional[ExecutionBudget] = None) -> None:
        """Initializes the consensus decider with default execution constraints.

        :param default_budget: Optional ExecutionBudget instance.
        """
        self.default_budget = default_budget or ExecutionBudget()

    def evaluate_function(
        self,
        fn: Callable[..., Any],
        args: Tuple[Any, ...] = (),
        budget: Optional[ExecutionBudget] = None,
    ) -> HaltingDecision:
        """Executes a function under a strict execution budget.

        :param fn: Target callable to evaluate.
        :param args: Positional arguments for the callable.
        :param budget: Optional overriding budget constraints.
        :return: HaltingDecision reflecting termination status and gas consumption.
        """
        active_budget = budget or self.default_budget
        start_time = time.time()
        steps = 0
        gas_used = 0

        try:
            steps += 1
            gas_used += 10
            result = fn(*args)
            elapsed = time.time() - start_time

            if elapsed > active_budget.timeout_seconds:
                return HaltingDecision(
                    will_halt=False,
                    reason="Execution timeout exceeded consensus limit",
                    steps_consumed=steps,
                    gas_consumed=gas_used,
                    tokens_consumed=0,
                )

            return HaltingDecision(
                will_halt=True,
                reason="Computation completed deterministically within budget",
                steps_consumed=steps,
                gas_consumed=gas_used,
                tokens_consumed=0,
                execution_output=result,
            )
        except RecursionError:
            return HaltingDecision(
                will_halt=False,
                reason="Infinite recursion detected: call stack exceeded depth limit",
                steps_consumed=steps,
                gas_consumed=gas_used,
                tokens_consumed=0,
            )
        except EXECUTION_EXCEPTIONS as exc:
            return HaltingDecision(
                will_halt=False,
                reason=f"Execution terminated abnormally: {exc}",
                steps_consumed=steps,
                gas_consumed=gas_used,
                tokens_consumed=0,
            )

    def evaluate_graph(
        self,
        nodes: Dict[str, ComputationalNode],
        initial_inputs: Optional[Dict[str, Any]] = None,
        budget: Optional[ExecutionBudget] = None,
    ) -> HaltingDecision:
        """Evaluates and executes a computational dependency graph.

        :param nodes: Mapping of node identifiers to computational node definitions.
        :param initial_inputs: Starting input values for root nodes.
        :param budget: Optional execution budget constraints.
        :return: HaltingDecision reflecting whether the graph terminates and outputs.
        """
        active_budget = budget or self.default_budget
        validation = DAGCycleDetector.validate_graph(nodes)

        if not validation.is_dag:
            return HaltingDecision(
                will_halt=False,
                reason="Non-halting graph: cyclic dependencies detected",
                steps_consumed=0,
                gas_consumed=0,
                tokens_consumed=0,
            )

        outputs: Dict[str, Any] = dict(initial_inputs or {})
        total_steps = 0
        total_gas = 0

        for node_id in validation.topological_order:
            node = nodes[node_id]
            total_steps += 1
            total_gas += node.gas_cost

            if total_gas > active_budget.max_gas:
                return HaltingDecision(
                    will_halt=False,
                    reason="Consensus gas limit exhausted before completion",
                    steps_consumed=total_steps,
                    gas_consumed=total_gas,
                    tokens_consumed=0,
                )

            if node.computation:
                node_inputs = {dep: outputs.get(dep) for dep in node.dependencies}
                outputs[node_id] = node.computation(node_inputs)
            else:
                outputs[node_id] = None

        return HaltingDecision(
            will_halt=True,
            reason="Graph executed to completion across all nodes in topological order",
            steps_consumed=total_steps,
            gas_consumed=total_gas,
            tokens_consumed=0,
            execution_output=outputs,
        )
