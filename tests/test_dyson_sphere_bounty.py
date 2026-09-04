"""Unit tests for Dyson Sphere Engineering Department Meta-Bounty & Solar Dominion Subsystem.
Resolves Issue #785: [BOUNTY] [0000] [AGENTIC] [AI] Dyson Sphere Engineering Department ($15,000 USD).
Verifies Stefan-Boltzmann radiation capture, microwave beam link efficiency, radiative heat dissipation,
thermal overload simulation, and BYOND DreamMaker syntax definitions.
"""

import unittest
from scripts.dyson_sphere_bounty import (
    DysonHarvestingParams,
    DysonEngineeringSimulator,
    DysonBountyGenerator,
)


class TestDysonSphereBounty(unittest.TestCase):
    def setUp(self):
        self.params = DysonHarvestingParams(
            star_surface_temperature_k=5778.0,
            collector_temperature_k=1200.0,
            collector_area_sq_meters=2.5e6,
            emissivity_collector=0.94,
            beam_aperture_diameter_m=150.0,
            rectenna_diameter_m=80.0,
            beam_wavelength_m=0.0125,
            relay_distance_meters=3.6e7,
            radiator_fin_area_sq_m=5.0e4,
            coolant_temperature_k=650.0,
        )
        self.simulator = DysonEngineeringSimulator(params=self.params)
        self.generator = DysonBountyGenerator()

    def test_gross_captured_power_magnitude(self):
        # 1361 W/m^2 * 0.94 * 2.5e6 m^2 = 3.19835e9 W ≈ 3.20 GW
        gross_gw = self.params.gross_captured_power_gigawatts
        self.assertGreater(gross_gw, 3.10)
        self.assertLess(gross_gw, 3.30)

    def test_microwave_beam_efficiency_bound(self):
        eff = self.params.microwave_beam_efficiency
        self.assertGreaterEqual(eff, 0.10)
        self.assertLessEqual(eff, 0.925)

    def test_maximum_rejected_heat_capacity(self):
        # sigma * 0.90 * 5e4 * (650^4 - 2.725^4) / 1e6
        # sigma * 0.90 * 5e4 ≈ 2.5516e-3
        # 650^4 ≈ 1.78506e11
        # Q ≈ 2.5516e-3 * 1.78506e11 / 1e6 ≈ 455.5 MW
        cooling_mw = self.params.maximum_rejected_heat_megawatts
        self.assertGreater(cooling_mw, 400.0)
        self.assertLess(cooling_mw, 500.0)

    def test_station_power_calculation_single_ring(self):
        res = self.simulator.calculate_net_station_power(collector_rings=1)
        self.assertEqual(res["collector_rings"], 1)
        self.assertGreater(res["received_power_mw"], 300.0)
        self.assertGreater(res["net_surplus_mw"], 0.0)
        self.assertFalse(res["thermal_overload"])

    def test_station_power_thermal_overload_multiple_rings(self):
        # Over-scaling collector rings past thermal cooling limits
        res = self.simulator.calculate_net_station_power(collector_rings=10)
        self.assertTrue(res["thermal_overload"])
        self.assertGreater(res["thermal_waste_mw"], res["cooling_capacity_mw"])

    def test_bounty_document_structure_and_currencies(self):
        doc = self.generator.build_bounty_document()
        self.assertIn("Dyson Sphere Engineering Department", doc)
        self.assertIn("$10,000 USD", doc)
        self.assertIn("Stefan-Boltzmann", doc)
        self.assertIn("24 GHz microwave", doc)
        for curr in ["GBP", "USD", "BTC", "EUR", "MXN", "YEN", "KZT", "KGS", "MYR", "PKR", "KYD"]:
            self.assertIn(curr, doc)

    def test_byond_dreammaker_definitions(self):
        dm = self.generator.generate_byond_dm_definitions()
        self.assertIn("/datum/controller/subsystem/dyson", dm)
        self.assertIn("/obj/machinery/power/dyson_receiver", dm)
        self.assertIn("/obj/machinery/dyson_radiator", dm)
        self.assertIn("/obj/item/device/solar_flux_meter", dm)


if __name__ == "__main__":
    unittest.main()
