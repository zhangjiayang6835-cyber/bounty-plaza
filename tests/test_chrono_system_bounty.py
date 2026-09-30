"""Unit tests for Chrono System Meta-Bounty & Temporal Mechanics Subsystem.
Resolves Issue #788: [BOUNTY] [0000] [AGENTIC] [AI] Chrono System ($15,000 USD).
Verifies relativistic Lorentz dilation, entropy drift under damping, ring buffer rollback,
paradox severity classification, and BYOND DreamMaker syntax definitions.
"""

import math
import unittest
from scripts.chrono_system_bounty import (
    TemporalFieldParams,
    ChronoParadoxSimulator,
    ChronoBountyGenerator,
)


class TestChronoSystemBounty(unittest.TestCase):
    def setUp(self):
        self.params = TemporalFieldParams(
            chroniton_flux_rate=432.0,
            entropy_drift_coefficient=0.042,
            stabilizer_damping_ratio=0.88,
            temporal_velocity_ratio=0.60,
            buffer_snapshot_depth=120,
        )
        self.simulator = ChronoParadoxSimulator(params=self.params)
        self.generator = ChronoBountyGenerator()

    def test_lorentz_time_dilation_factor(self):
        # gamma_t = 1 / sqrt(1 - 0.60^2) = 1 / sqrt(0.64) = 1 / 0.8 = 1.25
        gamma = self.params.lorentz_dilation_factor
        self.assertAlmostEqual(gamma, 1.25, places=4)

    def test_effective_entropy_rate_with_damping(self):
        # 0.042 * (1 - 0.88) = 0.042 * 0.12 = 0.00504
        expected_rate = 0.042 * 0.12
        self.assertAlmostEqual(self.params.effective_entropy_rate, expected_rate, places=6)

    def test_simulation_advancement_and_tier_classification(self):
        # Advance under normal conditions (low entropy -> Tier 1)
        res1 = self.simulator.advance_time(ticks=10)
        self.assertEqual(res1["paradox_severity_tier"], 1)
        self.assertLess(res1["timeline_entropy"], 1.0)

        # Inject massive anomaly burst to trigger Tier 4 / 5
        res2 = self.simulator.advance_time(ticks=50, anomaly_burst=20.0)
        self.assertGreaterEqual(res2["paradox_severity_tier"], 4)
        self.assertGreater(res2["timeline_entropy"], 6.0)

    def test_ring_buffer_snapshot_depth_and_rollback(self):
        for tick in range(150):
            self.simulator.record_snapshot(tick, {"mob_count": 50, "power_grid": 100})

        # Buffer must cap at buffer_snapshot_depth (120)
        self.assertEqual(len(self.simulator.snapshots), 120)
        self.assertEqual(self.simulator.snapshots[-1]["tick"], 149)
        self.assertEqual(self.simulator.snapshots[0]["tick"], 30)

        # Rollback to tick 100
        success, snap = self.simulator.resolve_paradox_rollback(100)
        self.assertTrue(success)
        self.assertIsNotNone(snap)
        self.assertLessEqual(snap["tick"], 100)

    def test_bounty_document_structure_and_currencies(self):
        doc = self.generator.build_bounty_document()
        self.assertIn("Chrono System", doc)
        self.assertIn("$10,000 USD", doc)
        self.assertIn("closed timelike curve", doc.lower())
        self.assertIn("gamma_t = 1.2500", doc)
        for curr in ["GBP", "USD", "BTC", "EUR", "MXN", "YEN", "KZT", "KGS", "MYR", "PKR", "KYD"]:
            self.assertIn(curr, doc)

    def test_byond_dreammaker_definitions(self):
        dm = self.generator.generate_byond_dm_definitions()
        self.assertIn("/datum/controller/subsystem/chrono", dm)
        self.assertIn("/obj/item/device/chronometer", dm)
        self.assertIn("/obj/machinery/temporal_anchor", dm)
        self.assertIn("snapshot_buffer", dm)


if __name__ == "__main__":
    unittest.main()
