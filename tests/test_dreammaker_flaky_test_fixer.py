"""Unit tests for DreamMaker SS13 Flaky Unit Test Fixer & Deterministic Test Harness.
Resolves Issue #691: [BOUNTY] 1000 USD - Fix all flaky unit tests ($1,000 USD).
Verifies idempotent qdel teardown, atom lifecycle cleanup, leak-free teardown,
and a 50-run consecutive pass streak without flakes.
"""

import unittest
from scripts.dreammaker_flaky_test_fixer import (
    DreamMakerTestEnvironment,
    FlakyUnitTestFixer,
    TARGET_STREAK,
)


class TestDreamMakerFlakyTestFixer(unittest.TestCase):
    def setUp(self):
        self.env = DreamMakerTestEnvironment()
        self.fixer = FlakyUnitTestFixer(env=self.env)

    def test_single_create_and_destroy_run_passes(self):
        passed, msg = self.fixer.run_create_and_destroy_test()
        self.assertTrue(passed)
        self.assertEqual(msg, "PASS")
        self.assertEqual(len(self.env.active_atoms), 0)

    def test_idempotent_qdel_prevents_double_free_or_corruption(self):
        atom_id = self.env.create_atom("/obj/item/weapon/tool/crowbar")
        self.assertIn(atom_id, self.env.active_atoms)

        # First qdel
        first_qdel = self.env.qdel(atom_id, force_hard_del=False)
        self.assertTrue(first_qdel)
        record = self.env.active_atoms[atom_id]
        self.assertTrue(bool(record.qdel_flags & 2))

        # Second qdel call should be safely idempotent
        second_qdel = self.env.qdel(atom_id, force_hard_del=False)
        self.assertTrue(second_qdel)

        # Garbage collection sweep
        collected = self.env.process_garbage_collection()
        self.assertEqual(collected, 1)
        self.assertNotIn(atom_id, self.env.active_atoms)

    def test_timer_registry_cleanup_on_tick_advancement(self):
        self.env.timer_registry["timer_event_1"] = 5
        self.env.timer_registry["timer_event_2"] = 15
        self.env.advance_ticks(10)  # world_time becomes 10

        self.assertNotIn("timer_event_1", self.env.timer_registry)
        self.assertIn("timer_event_2", self.env.timer_registry)

    def test_fifty_run_consecutive_streak_benchmark(self):
        result = self.fixer.run_streak_benchmark(target_streak=TARGET_STREAK)
        self.assertTrue(result["all_passed"])
        self.assertEqual(result["completed_streak"], 50)
        self.assertEqual(result["total_runs"], 50)
        self.assertEqual(len(result["failures"]), 0)


if __name__ == "__main__":
    unittest.main()
