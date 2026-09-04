"""Unit tests for Multiversal Transit Hub Meta-Bounty & Dimensional Mechanics Subsystem.
Resolves Issue #787: [BOUNTY] [0000] [AGENTIC] [AI] Multiversal Transit Hub ($15,000 USD).
Verifies Calabi-Yau metric dilation, exotic throat stability, phase coherence routing,
sector bridge operations, and BYOND DreamMaker syntax definitions.
"""

import math
import unittest
from scripts.multiversal_transit_bounty import (
    MultiversePhysicsParams,
    MultiverseRoutingEngine,
    MultiverseBountyGenerator,
)


class TestMultiversalTransitBounty(unittest.TestCase):
    def setUp(self):
        self.params = MultiversePhysicsParams(
            brane_distance_parsecs=4.25,
            bulk_propagation_speed=1.0,
            warp_coupling_kappa=0.15,
            portal_throat_radius_meters=3.5,
            exotic_energy_density=-0.420,
            phase_coherence_threshold=0.95,
        )
        self.engine = MultiverseRoutingEngine(params=self.params)
        self.generator = MultiverseBountyGenerator()

    def test_transit_latency_calculation(self):
        # phi = 0.420, dilation = sqrt(1 + 0.15 * 0.420^2) = sqrt(1 + 0.02646) = sqrt(1.02646) ≈ 1.01314
        # latency = 4.25 * 1.01314 ≈ 4.3058
        latency = self.params.transit_latency_seconds
        self.assertGreater(latency, 4.25)
        self.assertLess(latency, 4.35)

    def test_throat_stability_index(self):
        # abs(-0.420) / 0.45 = 0.9333...
        self.assertAlmostEqual(self.params.throat_stability_index, 0.420 / 0.45, places=3)
        self.assertGreaterEqual(self.params.throat_stability_index, 0.75)

    def test_phase_alignment_coherence(self):
        # Identical phase angle (0 vs 0) -> cos(0) = 1.0
        c_identical = self.engine.calculate_phase_alignment(0.0, 0.0)
        self.assertAlmostEqual(c_identical, 1.0)

        # Opposite phase angle (0 vs pi) -> cos(pi / 2) = 0.0
        c_opposite = self.engine.calculate_phase_alignment(0.0, math.pi)
        self.assertAlmostEqual(c_opposite, 0.0, places=5)

        # Mirror phase angle (0 vs pi / 2) -> cos(pi / 4) ≈ 0.7071
        c_mirror = self.engine.calculate_phase_alignment(0.0, math.pi / 2)
        self.assertAlmostEqual(c_mirror, math.cos(math.pi / 4), places=4)

    def test_open_gate_between_sectors(self):
        # Open gate from Prime to Mirror
        res = self.engine.open_gate("sector_prime", "sector_mirror")
        self.assertTrue(res["success"])
        status = res["gate_status"]
        self.assertEqual(status["source"], "Prime Reality")
        self.assertEqual(status["target"], "Mirror Timeline")
        self.assertAlmostEqual(status["coherence"], math.cos(math.pi / 4), places=3)
        self.assertTrue(status["stability"] >= 0.75)

    def test_open_gate_invalid_sector(self):
        res = self.engine.open_gate("sector_prime", "sector_nonexistent")
        self.assertFalse(res["success"])
        self.assertIn("Invalid sector", res["reason"])

    def test_bounty_document_structure_and_currencies(self):
        doc = self.generator.build_bounty_document()
        self.assertIn("Multiversal Transit Hub", doc)
        self.assertIn("$10,000 USD", doc)
        self.assertIn("Calabi-Yau", doc)
        self.assertIn("rho_exotic = -0.42", doc)
        for curr in ["GBP", "USD", "BTC", "EUR", "MXN", "YEN", "KZT", "KGS", "MYR", "PKR", "KYD"]:
            self.assertIn(curr, doc)

    def test_byond_dreammaker_definitions(self):
        dm = self.generator.generate_byond_dm_definitions()
        self.assertIn("/datum/controller/subsystem/multiverse", dm)
        self.assertIn("/obj/machinery/dimensional_gate", dm)
        self.assertIn("/obj/item/device/reality_tether", dm)
        self.assertIn("active_portals", dm)


if __name__ == "__main__":
    unittest.main()
