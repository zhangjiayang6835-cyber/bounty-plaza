"""High-level orchestration manager for OmniBlocks Forever If block subsystem."""

import sys
from typing import Any, Callable, Dict, List, Optional, Union
from packages.omni_forever_if.blockly import OmniBlocksForeverIfIntegration
from packages.omni_forever_if.fiber import ForeverIfFiber
from packages.omni_forever_if.models import BountySettlement, FiberStats, TriggerMode
from packages.omni_forever_if.runtime import OmniBlocksRuntime
from packages.omni_forever_if.sanitizer import BlockSanitizer
from packages.omni_forever_if.settlement import RewardSettlementCalculator


class ForeverIfEngine:
    """Unified management facade coordinating visual definitions and runtime execution."""

    def __init__(self) -> None:
        """Initialize runtime container and visual integration layer."""
        self.runtime: OmniBlocksRuntime = OmniBlocksRuntime()
        self.integration: OmniBlocksForeverIfIntegration = OmniBlocksForeverIfIntegration()

    def set_variable(self, name: str, value: Any) -> None:
        """Set global variable in execution runtime."""
        self.runtime.set_variable(name, value)

    def get_variable(self, name: str, default: Any = None) -> Any:
        """Get global variable from execution runtime."""
        return self.runtime.get_variable(name, default)

    def create_forever_if(
        self,
        condition: Union[str, bool, Callable[[], bool]],
        body: Callable[[], Any],
        trigger_mode: TriggerMode = TriggerMode.LEVEL_TRIGGERED,
        max_cycles: int = 100000,
        fiber_id: Optional[str] = None,
    ) -> ForeverIfFiber:
        """Register a new Forever If loop block in the runtime."""
        return self.runtime.register_forever_if(
            condition=condition,
            body=body,
            trigger_mode=trigger_mode,
            max_cycles=max_cycles,
            fiber_id=fiber_id,
        )

    def step(self) -> int:
        """Step all active fibers by one tick."""
        return self.runtime.step()

    def run(self, max_ticks: int = 100) -> Dict[str, Any]:
        """Execute scheduled fibers up to max ticks."""
        return self.runtime.run(max_ticks=max_ticks)

    def stop_all(self) -> None:
        """Halt all scheduled fibers."""
        self.runtime.stop_all()

    def get_stats(self) -> List[FiberStats]:
        """Retrieve execution statistics across all fibers."""
        return self.runtime.list_fibers()

    def get_block_definitions(self) -> List[Dict[str, Any]]:
        """Retrieve visual Blockly block schemas."""
        return self.integration.get_block_definitions()

    def generate_python(self, block_type: str, params: Dict[str, Any]) -> str:
        """Emit Python code for visual block configuration."""
        return self.integration.generate_python_code(block_type, params)

    def generate_javascript(self, block_type: str, params: Dict[str, Any]) -> str:
        """Emit JavaScript code for visual block configuration."""
        return self.integration.generate_javascript_code(block_type, params)

    def generate_toolbox(self) -> str:
        """Emit XML toolbox snippet for Blockly editor."""
        return self.integration.generate_toolbox_xml()

    def compute_bounty(self, reward_usd: float = 100.0) -> BountySettlement:
        """Compute financial payout settlement according to reward policy."""
        return RewardSettlementCalculator.calculate_settlement(reward_usd)

    def validate_code(self, source_code: str) -> List[str]:
        """Verify code safety and absence of prohibited operations."""
        return BlockSanitizer.validate_code(source_code)


def boot_engine() -> ForeverIfEngine:
    """Convenience factory function initializing a new engine instance."""
    return ForeverIfEngine()


def compute_bounty_settlement(reward_usd: float = 100.0) -> BountySettlement:
    """Convenience function calculating bounty settlement for issue rewards."""
    return RewardSettlementCalculator.calculate_settlement(reward_usd)


def _smoke_check() -> int:
    """Execute internal sanity verification."""
    engine = boot_engine()
    engine.set_variable("counter", 0)
    engine.create_forever_if(
        condition="counter < 3",
        body=lambda: engine.runtime.change_variable("counter", 1),
        max_cycles=10,
    )
    res = engine.run(max_ticks=5)
    if res["variable_state"]["counter"] != 3:
        return 1
    settlement = compute_bounty_settlement(100.0)
    if settlement.contributor_payout_usd != 82.80:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_smoke_check())
