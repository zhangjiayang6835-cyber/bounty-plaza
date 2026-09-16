"""Cooperative fiber scheduler and execution unit for Forever If blocks."""

from typing import Any, Callable, Dict, Optional, Union
import uuid
from packages.omni_forever_if.condition import ConditionEvaluator
from packages.omni_forever_if.models import FiberStats, LoopState, TriggerMode


class ForeverIfFiber:
    """Scheduled task fiber managing continuous conditional block iterations."""

    def __init__(
        self,
        condition: Union[str, bool, Callable[[], bool]],
        body: Callable[[], Any],
        *,
        evaluator: Optional[ConditionEvaluator] = None,
        trigger_mode: TriggerMode = TriggerMode.LEVEL_TRIGGERED,
        max_cycles: int = 100000,
        fiber_id: Optional[str] = None,
    ) -> None:
        """Initialize the forever if fiber execution unit."""
        self.fiber_id: str = fiber_id or f"fiber_{uuid.uuid4().hex[:8]}"
        self.condition: Union[str, bool, Callable[[], bool]] = condition
        self.body: Callable[[], Any] = body
        self.evaluator: ConditionEvaluator = evaluator if evaluator is not None else ConditionEvaluator()
        self.trigger_mode: TriggerMode = trigger_mode
        self.max_cycles: int = max_cycles
        self.state: LoopState = LoopState.IDLE
        self.total_ticks: int = 0
        self.active_executions: int = 0
        self.last_condition_val: bool = False
        self.break_requested: bool = False
        self.execution_history: list[Dict[str, Any]] = []

    def start(self) -> None:
        """Transition fiber to active running state."""
        if self.state not in (LoopState.STOPPED, LoopState.COMPLETED):
            self.state = LoopState.RUNNING

    def pause(self) -> None:
        """Pause fiber execution while preserving internal counters."""
        if self.state == LoopState.RUNNING:
            self.state = LoopState.PAUSED

    def resume(self) -> None:
        """Resume execution of a paused fiber."""
        if self.state == LoopState.PAUSED:
            self.state = LoopState.RUNNING

    def stop(self) -> None:
        """Halt loop execution permanently."""
        self.state = LoopState.STOPPED
        self.break_requested = True

    def reset(self) -> None:
        """Restore fiber to clean initial state."""
        self.state = LoopState.IDLE
        self.total_ticks = 0
        self.active_executions = 0
        self.last_condition_val = False
        self.break_requested = False
        self.execution_history.clear()

    def step(self) -> bool:
        """Execute a single scheduler tick of the conditional loop."""
        if self.state in (LoopState.STOPPED, LoopState.COMPLETED):
            return False

        if self.state == LoopState.PAUSED:
            return True

        if self.state == LoopState.IDLE:
            self.state = LoopState.RUNNING

        if self.total_ticks >= self.max_cycles:
            self.state = LoopState.COMPLETED
            return False

        self.total_ticks += 1
        cond_val = self.evaluator.evaluate(self.condition)

        executed_this_tick = False
        if cond_val:
            if self.trigger_mode == TriggerMode.LEVEL_TRIGGERED:
                self.body()
                self.active_executions += 1
                executed_this_tick = True
            elif self.trigger_mode == TriggerMode.EDGE_TRIGGERED and not self.last_condition_val:
                self.body()
                self.active_executions += 1
                executed_this_tick = True

        self.last_condition_val = cond_val

        self.execution_history.append({
            "tick": self.total_ticks,
            "condition": cond_val,
            "executed": executed_this_tick,
        })

        if self.break_requested:
            self.state = LoopState.STOPPED
            return False

        return True

    def run(self, max_ticks: int = 100) -> int:
        """Execute multiple scheduler ticks up to specified limit."""
        ticks_executed = 0
        while ticks_executed < max_ticks:
            can_continue = self.step()
            ticks_executed += 1
            if not can_continue:
                break
        return ticks_executed

    def get_stats(self) -> FiberStats:
        """Return runtime statistics snapshot."""
        return FiberStats(
            fiber_id=self.fiber_id,
            state=self.state.value,
            total_ticks=self.total_ticks,
            active_executions=self.active_executions,
            last_condition_result=self.last_condition_val,
        )
