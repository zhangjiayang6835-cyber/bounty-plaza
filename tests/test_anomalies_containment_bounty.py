"""Unit tests for Anomalies Containment Wing Meta-Bounty & Reality Stabilization Subsystem.
Resolves Issue #786: [BOUNTY] [0000] [AGENTIC] [AI] Anomalies Containment Wing ($15,000 USD).
Verifies Hume field differential restoration, SRA reality anchoring, Akiva radiation attenuation,
containment severity classification, and BYOND DreamMaker syntax definitions.
"""

import math
import unittest
from scripts.anomalies_containment_bounty import (
    RealityFieldParams,
    AnomaliesContainmentSimulator,
    AnomaliesBountyGenerator,
)


class TestAnomaliesContainmentBounty(unittest.TestCase):
    def setUp(self):
        self.params = RealityFieldParams(
            baseline_hume=1.000,
            sra_stabilization_rate=0.250,
            akiva_absorption_mu=0.450,
            sra_power_draw_kw=75.0,
            danger_hume_deviation=0.150,
        )
        self.simulator = AnomaliesContainmentSimulator(params=self.params)
        self.generator = AnomaliesBountyGenerator()

    def test_safe_hume_range(self):
        low, high = self.params.safe_hume_range
        self.assertEqual(low, 0.850)
        self.assertEqual(high, 1.150)

    def test_akiva_radiation_decay(self):
        # Distance zero/small -> A0
        a0 = 100.0
        decay_zero = self.simulator.calculate_akiva_decay(a0, 0.05)
        self.assertEqual(decay_zero, a0)

        # Distance 2 meters
        # geom = 4 * pi * 4 = 16 * pi ≈ 50.2655
        # atten = exp(-0.450 * 2) = exp(-0.9) ≈ 0.40657
        # result = (100 / 50.2655) * 0.40657 ≈ 0.8088
        decay_2m = self.simulator.calculate_akiva_decay(a0, 2.0)
        self.assertGreater(decay_2m, 0.70)
        self.assertLess(decay_2m, 0.90)

    def test_sra_active_restoration_under_moderate_flux(self):
        # Moderate anomaly flux of 0.05 Hume/tick
        # SRA active: restoration = 0.250 * (1.00 - 1.00) = 0 initially
        res1 = self.simulator.step_containment_cell(anomaly_flux=0.05, sra_active=True)
        self.assertLess(res1["local_hume"], 1.00)
        self.assertEqual(res1["containment_tier"], 1)
        self.assertFalse(res1["is_breached"])

        # Second step: Hume is < 1.00, so SRA applies positive restoration
        res2 = self.simulator.step_containment_cell(anomaly_flux=0.05, sra_active=True)
        self.assertGreaterEqual(res2["local_hume"], 0.85)

    def test_sra_inactive_triggers_breach(self):
        # Heavy anomaly flux without SRA stabilization
        for _ in range(15):
            res = self.simulator.step_containment_cell(anomaly_flux=0.08, sra_active=False)

        self.assertLess(res["local_hume"], 0.40)
        self.assertTrue(res["is_breached"])
        self.assertGreaterEqual(res["containment_tier"], 4)

    def test_bounty_document_structure_and_currencies(self):
        doc = self.generator.build_bounty_document()
        self.assertIn("Anomalies Containment Wing", doc)
        self.assertIn("$10,000 USD", doc)
        self.assertIn("Hume", doc)
        self.assertIn("Scranton Reality Anchor", doc)
        for curr in ["GBP", "USD", "BTC", "EUR", "MXN", "YEN", "KZT", "KGS", "MYR", "PKR", "KYD"]:
            self.assertIn(curr, doc)

    def test_byond_dreammaker_definitions(self):
        dm = self.generator.generate_byond_dm_definitions()
        self.assertIn("/datum/controller/subsystem/containment", dm)
        self.assertIn("/obj/machinery/scranton_anchor", dm)
        self.assertIn("/obj/item/device/kant_counter", dm)
        self.assertIn("/obj/structure/containment_seal", dm)


if __name__ == "__main__":
    unittest.main()
