"""Unit and integration tests for OmniBlocks Forever If block subsystem."""

import unittest
from packages.omni_forever_if.blockly import OmniBlocksForeverIfIntegration
from packages.omni_forever_if.condition import ConditionEvaluator
from packages.omni_forever_if.fiber import ForeverIfFiber
from packages.omni_forever_if.manager import (
    ForeverIfEngine,
    boot_engine,
    compute_bounty_settlement,
)
from packages.omni_forever_if.models import LoopState, TriggerMode
from packages.omni_forever_if.runtime import OmniBlocksRuntime
from packages.omni_forever_if.sanitizer import BlockSanitizer
from packages.omni_forever_if.settlement import RewardSettlementCalculator


class TestConditionEvaluator(unittest.TestCase):
    """Validation test suite for safe condition evaluation."""

    def setUp(self) -> None:
        """Initialize evaluator instance for testing."""
        self.evaluator = ConditionEvaluator({"player_x": 15, "player_y": 20, "is_alive": True})

    def test_direct_booleans_and_names(self) -> None:
        """Verify evaluation of boolean literals and variables."""
        self.assertTrue(self.evaluator.evaluate(True))
        self.assertFalse(self.evaluator.evaluate(False))
        self.assertTrue(self.evaluator.evaluate("True"))
        self.assertFalse(self.evaluator.evaluate("False"))
        self.assertTrue(self.evaluator.evaluate("is_alive"))

    def test_relational_comparisons(self) -> None:
        """Verify relational operators."""
        self.assertTrue(self.evaluator.evaluate("player_x < 20"))
        self.assertTrue(self.evaluator.evaluate("player_x <= 15"))
        self.assertTrue(self.evaluator.evaluate("player_y > 10"))
        self.assertTrue(self.evaluator.evaluate("player_y >= 20"))
        self.assertTrue(self.evaluator.evaluate("player_x == 15"))
        self.assertTrue(self.evaluator.evaluate("player_x != 10"))
        self.assertFalse(self.evaluator.evaluate("player_x > 50"))

    def test_logical_operators(self) -> None:
        """Verify conjunction and disjunction operators."""
        self.assertTrue(self.evaluator.evaluate("player_x == 15 and player_y == 20"))
        self.assertFalse(self.evaluator.evaluate("player_x == 15 and player_y == 99"))
        self.assertTrue(self.evaluator.evaluate("player_x == 99 or player_y == 20"))
        self.assertFalse(self.evaluator.evaluate("not is_alive"))

    def test_arithmetic_within_conditions(self) -> None:
        """Verify arithmetic inside condition predicates."""
        self.assertTrue(self.evaluator.evaluate("player_x + 5 == player_y"))
        self.assertTrue(self.evaluator.evaluate("player_y - 5 == player_x"))
        self.assertTrue(self.evaluator.evaluate("player_x * 2 > player_y"))

    def test_registered_predicate_callbacks(self) -> None:
        """Verify custom registered predicate functions."""
        self.evaluator.register_predicate("sensor_triggered", lambda: True)
        self.assertTrue(self.evaluator.evaluate("sensor_triggered"))

    def test_invalid_syntax_handling(self) -> None:
        """Verify error handling on malformed syntax."""
        with self.assertRaises(Exception):
            self.evaluator.evaluate("player_x <<< 10")


class TestForeverIfFiber(unittest.TestCase):
    """Validation test suite for cooperative loop fiber execution."""

    def test_level_triggered_execution(self) -> None:
        """Verify continuous execution while condition remains true."""
        state = {"count": 0, "active": True}
        evaluator = ConditionEvaluator(state)

        def increment() -> None:
            state["count"] += 1
            if state["count"] >= 5:
                state["active"] = False

        fiber = ForeverIfFiber(
            condition="active",
            body=increment,
            evaluator=evaluator,
            trigger_mode=TriggerMode.LEVEL_TRIGGERED,
            max_cycles=20,
        )

        ticks = fiber.run(max_ticks=10)
        self.assertEqual(state["count"], 5)
        self.assertGreaterEqual(ticks, 5)

    def test_edge_triggered_execution(self) -> None:
        """Verify execution only on condition transition from false to true."""
        state = {"count": 0, "signal": False}
        evaluator = ConditionEvaluator(state)

        def bump() -> None:
            state["count"] += 1

        fiber = ForeverIfFiber(
            condition="signal",
            body=bump,
            evaluator=evaluator,
            trigger_mode=TriggerMode.EDGE_TRIGGERED,
            max_cycles=20,
        )

        fiber.step()
        self.assertEqual(state["count"], 0)

        state["signal"] = True
        fiber.step()
        self.assertEqual(state["count"], 1)

        fiber.step()
        self.assertEqual(state["count"], 1)

        state["signal"] = False
        fiber.step()
        self.assertEqual(state["count"], 1)

        state["signal"] = True
        fiber.step()
        self.assertEqual(state["count"], 2)

    def test_pause_resume_and_stop(self) -> None:
        """Verify lifecycle controls of loop fiber."""
        counter = {"val": 0}
        evaluator = ConditionEvaluator()

        def action() -> None:
            counter["val"] += 1

        fiber = ForeverIfFiber(
            condition=True,
            body=action,
            evaluator=evaluator,
            max_cycles=50,
        )

        fiber.step()
        self.assertEqual(counter["val"], 1)
        self.assertEqual(fiber.state, LoopState.RUNNING)

        fiber.pause()
        self.assertEqual(fiber.state, LoopState.PAUSED)
        fiber.step()
        self.assertEqual(counter["val"], 1)

        fiber.resume()
        self.assertEqual(fiber.state, LoopState.RUNNING)
        fiber.step()
        self.assertEqual(counter["val"], 2)

        fiber.stop()
        self.assertEqual(fiber.state, LoopState.STOPPED)
        alive = fiber.step()
        self.assertFalse(alive)
        self.assertEqual(counter["val"], 2)

    def test_max_cycle_protection(self) -> None:
        """Verify fiber safely halts when max cycle ceiling is reached."""
        count = {"val": 0}
        fiber = ForeverIfFiber(
            condition=True,
            body=lambda: count.update({"val": count["val"] + 1}),
            max_cycles=15,
        )
        fiber.run(max_ticks=30)
        self.assertEqual(fiber.state, LoopState.COMPLETED)
        self.assertEqual(count["val"], 15)

    def test_stats_and_reset(self) -> None:
        """Verify fiber statistics reporting and reset function."""
        fiber = ForeverIfFiber(
            condition=True,
            body=lambda: None,
            max_cycles=10,
        )
        fiber.run(max_ticks=5)
        stats = fiber.get_stats()
        self.assertEqual(stats.total_ticks, 5)
        self.assertEqual(stats.active_executions, 5)

        fiber.reset()
        self.assertEqual(fiber.state, LoopState.IDLE)
        self.assertEqual(fiber.total_ticks, 0)
        self.assertEqual(fiber.active_executions, 0)


class TestBlocklyIntegration(unittest.TestCase):
    """Validation test suite for visual block definitions and code generation."""

    def test_block_definitions(self) -> None:
        """Verify Blockly block definitions schema."""
        definitions = OmniBlocksForeverIfIntegration.get_block_definitions()
        self.assertGreaterEqual(len(definitions), 4)
        block_types = [d["type"] for d in definitions]
        self.assertIn("control_forever_if", block_types)
        self.assertIn("control_forever_if_edge", block_types)
        self.assertIn("control_stop_forever_if", block_types)
        self.assertIn("logic_condition_expr", block_types)

    def test_python_code_generation(self) -> None:
        """Verify Python code emission for visual blocks."""
        py_loop = OmniBlocksForeverIfIntegration.generate_python_code(
            "control_forever_if",
            {"CONDITION": "score > 100", "DO": "player.speed += 2"},
        )
        self.assertIn("while True:", py_loop)
        self.assertIn("if score > 100:", py_loop)
        self.assertIn("player.speed += 2", py_loop)

        py_edge = OmniBlocksForeverIfIntegration.generate_python_code(
            "control_forever_if_edge",
            {"CONDITION": "button_pressed", "DO": "trigger_sound()"},
        )
        self.assertIn("while True:", py_edge)
        self.assertIn("trigger_sound()", py_edge)

        py_stop = OmniBlocksForeverIfIntegration.generate_python_code(
            "control_stop_forever_if",
            {"FIBER": "main_loop"},
        )
        self.assertEqual(py_stop, "main_loop.stop()")

        py_cond = OmniBlocksForeverIfIntegration.generate_python_code(
            "logic_condition_expr",
            {"LEFT": "health", "OP": "LTE", "RIGHT": "0"},
        )
        self.assertEqual(py_cond, "health <= 0")

    def test_javascript_code_generation(self) -> None:
        """Verify JavaScript code emission for visual blocks."""
        js_loop = OmniBlocksForeverIfIntegration.generate_javascript_code(
            "control_forever_if",
            {"CONDITION": "active === true", "DO": "renderFrame();"},
        )
        self.assertIn("while (true) {", js_loop)
        self.assertIn("if (active === true)", js_loop)
        self.assertIn("renderFrame();", js_loop)

        js_stop = OmniBlocksForeverIfIntegration.generate_javascript_code(
            "control_stop_forever_if",
            {"FIBER": "task"},
        )
        self.assertEqual(js_stop, "task.stop();")

    def test_toolbox_generation(self) -> None:
        """Verify XML toolbox generation."""
        toolbox_xml = OmniBlocksForeverIfIntegration.generate_toolbox_xml()
        self.assertIn('<category name="Forever If Control"', toolbox_xml)
        self.assertIn('block type="control_forever_if"', toolbox_xml)

    def test_block_spec_parsing(self) -> None:
        """Verify parsing block specification into structured node."""
        node = OmniBlocksForeverIfIntegration.parse_block_node({
            "id": "blk_01",
            "type": "control_forever_if",
            "condition": "x > 5",
            "statements": [{"action": "set_var", "name": "flag", "value": True}],
        })
        self.assertEqual(node.block_id, "blk_01")
        self.assertEqual(node.condition_expr, "x > 5")
        self.assertEqual(len(node.statements), 1)


class TestOmniBlocksRuntime(unittest.TestCase):
    """Validation test suite for runtime execution scheduler."""

    def test_runtime_variable_management(self) -> None:
        """Verify variable manipulation APIs in runtime."""
        runtime = OmniBlocksRuntime()
        runtime.set_variable("coins", 50)
        self.assertEqual(runtime.get_variable("coins"), 50)

        updated = runtime.change_variable("coins", 25)
        self.assertEqual(updated, 75)
        self.assertEqual(runtime.get_variable("coins"), 75)

    def test_declarative_program_loading(self) -> None:
        """Verify loading declarative block program and stepping execution."""
        runtime = OmniBlocksRuntime()
        program = {
            "variables": {"counter": 0, "finished": False},
            "blocks": [
                {
                    "id": "loop_1",
                    "type": "control_forever_if",
                    "condition": "counter < 4",
                    "max_cycles": 10,
                    "do": [
                        {"action": "change_var", "name": "counter", "delta": 1},
                    ],
                }
            ],
        }

        fibers = runtime.load_program_spec(program)
        self.assertEqual(len(fibers), 1)

        result = runtime.run(max_ticks=10)
        self.assertEqual(result["variable_state"]["counter"], 4)
        self.assertEqual(result["ticks_executed"], 10)

    def test_multi_fiber_coordination(self) -> None:
        """Verify simultaneous execution of multiple forever if fibers."""
        runtime = OmniBlocksRuntime()
        runtime.set_variable("a", 0)
        runtime.set_variable("b", 0)

        runtime.register_forever_if(
            condition="a < 3",
            body=lambda: runtime.change_variable("a", 1),
            max_cycles=10,
            fiber_id="fiber_a",
        )
        runtime.register_forever_if(
            condition="b < 5",
            body=lambda: runtime.change_variable("b", 1),
            max_cycles=10,
            fiber_id="fiber_b",
        )

        runtime.run(max_ticks=10)
        self.assertEqual(runtime.get_variable("a"), 3)
        self.assertEqual(runtime.get_variable("b"), 5)


class TestRewardSettlement(unittest.TestCase):
    """Validation test suite for REWARD_POLICY.md compliance."""

    def test_exact_100_dollar_issue_settlement(self) -> None:
        """Verify exact reward calculations for Issue #1559 ($100)."""
        settlement = compute_bounty_settlement(100.0)
        self.assertEqual(settlement.reward_usd, 100.0)
        self.assertEqual(settlement.platform_coins, 125.0)
        self.assertEqual(settlement.contributor_ratio, 0.92)
        self.assertEqual(settlement.contributor_coins, 115.0)
        self.assertEqual(settlement.redemption_rate_usd, 0.72)
        self.assertEqual(settlement.contributor_payout_usd, 82.80)
        self.assertEqual(settlement.platform_fee_usd, 17.20)
        self.assertEqual(settlement.omb_tokens, 828.0)

    def test_brackets_and_redemption_eligibility(self) -> None:
        """Verify tiered revenue split brackets across reward ranges."""
        self.assertEqual(RewardSettlementCalculator.get_contributor_ratio(30.0), 0.95)
        self.assertEqual(RewardSettlementCalculator.get_contributor_ratio(100.0), 0.92)
        self.assertEqual(RewardSettlementCalculator.get_contributor_ratio(350.0), 0.90)
        self.assertEqual(RewardSettlementCalculator.get_contributor_ratio(750.0), 0.87)
        self.assertEqual(RewardSettlementCalculator.get_contributor_ratio(2000.0), 0.85)

        self.assertTrue(RewardSettlementCalculator.is_eligible_for_redemption(125.0))
        self.assertTrue(RewardSettlementCalculator.is_eligible_for_redemption(100.0))
        self.assertFalse(RewardSettlementCalculator.is_eligible_for_redemption(80.0))


class TestSecuritySanitizer(unittest.TestCase):
    """Validation test suite for AST security inspector."""

    def test_safe_code_passes(self) -> None:
        """Verify clean code passes inspection without violations."""
        safe_code = """
def compute(x, y):
    return x * y + 10
result = compute(5, 6)
"""
        violations = BlockSanitizer.validate_code(safe_code)
        self.assertEqual(len(violations), 0)

    def test_forbidden_calls_rejected(self) -> None:
        """Verify dynamic evaluation and execution calls are detected."""
        eval_code = "eval('1 + 1')"
        violations = BlockSanitizer.validate_code(eval_code)
        self.assertGreater(len(violations), 0)

        exec_code = "exec('x = 5')"
        violations_exec = BlockSanitizer.validate_code(exec_code)
        self.assertGreater(len(violations_exec), 0)

    def test_forbidden_imports_rejected(self) -> None:
        """Verify prohibited module imports are detected."""
        import_code = "import subprocess"
        violations = BlockSanitizer.validate_code(import_code)
        self.assertGreater(len(violations), 0)

        pickle_code = "import pickle"
        violations_pickle = BlockSanitizer.validate_code(pickle_code)
        self.assertGreater(len(violations_pickle), 0)


class TestForeverIfEngineFacade(unittest.TestCase):
    """Validation test suite for top-level engine facade."""

    def test_facade_end_to_end(self) -> None:
        """Verify complete flow through ForeverIfEngine facade."""
        engine = boot_engine()
        engine.set_variable("target_score", 0)

        fiber = engine.create_forever_if(
            condition="target_score < 4",
            body=lambda: engine.runtime.change_variable("target_score", 1),
            max_cycles=10,
            fiber_id="facade_loop",
        )

        run_res = engine.run(max_ticks=10)
        self.assertEqual(run_res["variable_state"]["target_score"], 4)
        stats = engine.get_stats()
        self.assertEqual(len(stats), 1)
        self.assertEqual(stats[0].fiber_id, "facade_loop")

        definitions = engine.get_block_definitions()
        self.assertGreaterEqual(len(definitions), 4)

        settlement = engine.compute_bounty(100.0)
        self.assertEqual(settlement.contributor_payout_usd, 82.80)


if __name__ == "__main__":
    unittest.main()
