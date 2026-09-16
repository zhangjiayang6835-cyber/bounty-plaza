"""OmniBlocks runtime scheduler and state management engine."""

from typing import Any, Callable, Dict, List, Optional, Union
from packages.omni_forever_if.condition import ConditionEvaluator
from packages.omni_forever_if.fiber import ForeverIfFiber
from packages.omni_forever_if.models import FiberStats, LoopState, TriggerMode


class OmniBlocksRuntime:
    """Cooperative virtual execution environment for OmniBlocks block programs."""

    def __init__(self) -> None:
        """Initialize runtime state, variables, and fiber scheduler."""
        self.variables: Dict[str, Any] = {}
        self.fibers: Dict[str, ForeverIfFiber] = {}
        self.evaluator: ConditionEvaluator = ConditionEvaluator(self.variables)
        self.event_log: List[Dict[str, Any]] = []
        self.current_tick: int = 0

    def set_variable(self, name: str, value: Any) -> None:
        """Store value into runtime global variables."""
        self.variables[name] = value

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Retrieve value from runtime global variables."""
        return self.variables.get(name, default)

    def change_variable(self, name: str, delta: Union[int, float] = 1) -> Union[int, float]:
        """Modify numeric variable by delta value."""
        curr = self.variables.get(name, 0)
        updated = curr + delta
        self.variables[name] = updated
        return updated

    def register_forever_if(
        self,
        condition: Union[str, bool, Callable[[], bool]],
        body: Callable[[], Any],
        trigger_mode: TriggerMode = TriggerMode.LEVEL_TRIGGERED,
        max_cycles: int = 100000,
        fiber_id: Optional[str] = None,
    ) -> ForeverIfFiber:
        """Register a new Forever If fiber into the runtime scheduler."""
        fiber = ForeverIfFiber(
            condition=condition,
            body=body,
            evaluator=self.evaluator,
            trigger_mode=trigger_mode,
            max_cycles=max_cycles,
            fiber_id=fiber_id,
        )
        self.fibers[fiber.fiber_id] = fiber
        return fiber

    def register_fiber(self, fiber: ForeverIfFiber) -> str:
        """Add an instantiated fiber into active scheduler."""
        self.fibers[fiber.fiber_id] = fiber
        return fiber.fiber_id

    def get_fiber(self, fiber_id: str) -> Optional[ForeverIfFiber]:
        """Look up fiber instance by identifier."""
        return self.fibers.get(fiber_id)

    def list_fibers(self) -> List[FiberStats]:
        """Generate list of statistics across all scheduled fibers."""
        stats = []
        for fiber in self.fibers.values():
            stats.append(fiber.get_stats())
        return stats

    def step(self) -> int:
        """Advance all active fibers by one cooperative tick."""
        self.current_tick += 1
        active_count = 0

        for fiber in list(self.fibers.values()):
            if fiber.state not in (LoopState.STOPPED, LoopState.COMPLETED):
                still_running = fiber.step()
                if still_running:
                    active_count += 1

        return active_count

    def run(self, max_ticks: int = 100) -> Dict[str, Any]:
        """Execute scheduler loop until fibers complete or tick boundary is met."""
        executed_ticks = 0
        while executed_ticks < max_ticks:
            active = self.step()
            executed_ticks += 1
            if active == 0:
                break

        return {
            "ticks_executed": executed_ticks,
            "total_runtime_ticks": self.current_tick,
            "active_fibers": sum(
                1 for f in self.fibers.values()
                if f.state not in (LoopState.STOPPED, LoopState.COMPLETED)
            ),
            "variable_state": dict(self.variables),
        }

    def pause_all(self) -> None:
        """Pause all running fibers."""
        for fiber in self.fibers.values():
            fiber.pause()

    def resume_all(self) -> None:
        """Resume all paused fibers."""
        for fiber in self.fibers.values():
            fiber.resume()

    def stop_all(self) -> None:
        """Halt all scheduled fibers."""
        for fiber in self.fibers.values():
            fiber.stop()

    def clear(self) -> None:
        """Wipe runtime state and fiber registry."""
        self.fibers.clear()
        self.variables.clear()
        self.event_log.clear()
        self.current_tick = 0

    def load_program_spec(self, spec: Dict[str, Any]) -> List[ForeverIfFiber]:
        """Construct executable fibers from declarative program dictionary."""
        initial_vars = spec.get("variables", {})
        for k, v in initial_vars.items():
            self.set_variable(k, v)

        created = []
        blocks = spec.get("blocks", [])
        for blk in blocks:
            b_type = blk.get("type")
            if b_type in ("control_forever_if", "control_forever_if_edge"):
                cond_expr = blk.get("condition", "True")
                statements = blk.get("do", [])
                mode = (
                    TriggerMode.EDGE_TRIGGERED
                    if b_type == "control_forever_if_edge"
                    else TriggerMode.LEVEL_TRIGGERED
                )

                def make_body(stmts: List[Dict[str, Any]]) -> Callable[[], None]:
                    def body_exec() -> None:
                        for s in stmts:
                            act = s.get("action")
                            if act == "set_var":
                                self.set_variable(s.get("name", "x"), s.get("value"))
                            elif act == "change_var":
                                self.change_variable(s.get("name", "x"), s.get("delta", 1))
                            elif act == "log_event":
                                self.event_log.append(s.get("payload", {}))
                            elif act == "stop_all":
                                self.stop_all()
                    return body_exec

                fiber = self.register_forever_if(
                    condition=cond_expr,
                    body=make_body(statements),
                    trigger_mode=mode,
                    max_cycles=blk.get("max_cycles", 100000),
                    fiber_id=blk.get("id"),
                )
                created.append(fiber)

        return created
