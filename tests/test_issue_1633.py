"""Comprehensive test suite for the parametric tinaco flower rainwater collector."""

import math
import unittest

from packages.tinaco_rainwater_collector import (
    BillOfMaterials,
    CADGeometryEngine,
    DrainOutlet,
    EngineeringDrawingGenerator,
    FlowerCollectorConfig,
    HydraulicEngine,
    MeasurementChecklist,
    Point3D,
    SettlementEngine,
    TinacoAdapter,
)


class TestCollectorModels(unittest.TestCase):
    """Validation test cases for data structures and geometric entities."""

    def test_default_config_validation(self):
        """Verify default configuration passes all validation checks."""
        config = FlowerCollectorConfig()
        errors = config.validate()
        self.assertEqual(len(errors), 0)
        self.assertGreater(config.catchment_area_m2, 1.5)
        self.assertGreater(config.total_height_mm, 300.0)

    def test_invalid_config_detection(self):
        """Verify geometric errors are detected during validation."""
        bad_config = FlowerCollectorConfig(
            petal_count=2,
            outer_diameter_mm=200.0,
            inner_funnel_diameter_mm=300.0,
            slope_angle_deg=2.0,
            wall_thickness_mm=1.0,
            tinaco_rim_min_mm=700.0,
            tinaco_rim_nominal_mm=500.0,
        )
        errors = bad_config.validate()
        self.assertGreaterEqual(len(errors), 5)

    def test_point3d_vector_math(self):
        """Verify 3D coordinate vector operations."""
        p1 = Point3D(1.0, 0.0, 0.0)
        p2 = Point3D(0.0, 1.0, 0.0)
        self.assertAlmostEqual(p1.distance_to(p2), math.sqrt(2.0))
        self.assertAlmostEqual(p1.dot(p2), 0.0)

        cross_prod = p1.cross(p2)
        self.assertAlmostEqual(cross_prod.x, 0.0)
        self.assertAlmostEqual(cross_prod.y, 0.0)
        self.assertAlmostEqual(cross_prod.z, 1.0)
        self.assertAlmostEqual(cross_prod.norm(), 1.0)

        norm_p1 = p1.normalized()
        self.assertAlmostEqual(norm_p1.norm(), 1.0)

        p_zero = Point3D(0.0, 0.0, 0.0).normalized()
        self.assertEqual(p_zero.z, 1.0)

    def test_drain_outlet_properties(self):
        """Verify hydraulic discharge bore area and filter mesh porosity."""
        outlet = DrainOutlet()
        self.assertAlmostEqual(outlet.drain_area_mm2, math.pi * (55.0**2), places=2)
        self.assertAlmostEqual(outlet.funnel_top_area_mm2, math.pi * (110.0**2), places=2)
        self.assertGreater(outlet.filter_mesh_open_area_ratio, 0.60)

    def test_tinaco_adapter_compatibility(self):
        """Verify clamp adapter fits standard 400 mm to 650 mm tinaco rims."""
        adapter = TinacoAdapter()
        self.assertTrue(adapter.is_compatible(400.0))
        self.assertTrue(adapter.is_compatible(450.0))
        self.assertTrue(adapter.is_compatible(600.0))
        self.assertTrue(adapter.is_compatible(650.0))
        self.assertFalse(adapter.is_compatible(380.0))
        self.assertFalse(adapter.is_compatible(700.0))


class TestCADGeometryEngine(unittest.TestCase):
    """Validation test cases for 3D CAD modeling and file exporters."""

    def setUp(self):
        """Initialize CAD geometry engine before each test."""
        self.config = FlowerCollectorConfig()
        self.engine = CADGeometryEngine(self.config)

    def test_petal_generation_geometry(self):
        """Verify petals are correctly generated with positive drainage gradient."""
        petals = self.engine.build_petals()
        self.assertEqual(len(petals), 8)
        for petal in petals:
            self.assertEqual(petal.sweep_angle_deg, 45.0)
            self.assertEqual(petal.radial_length_mm, 590.0)
            self.assertTrue(petal.verify_drainage_gradient())
            self.assertGreater(petal.elevation_drop_mm, 100.0)

    def test_zero_gap_drainage_proof(self):
        """Verify analytical zero-gap proof between petals and central collector."""
        is_valid, max_rad_gap, max_vert_gap = self.engine.verify_zero_gap_drainage()
        self.assertTrue(is_valid)
        self.assertAlmostEqual(max_rad_gap, 0.0, places=4)
        self.assertAlmostEqual(max_vert_gap, 0.0, places=4)

    def test_mesh_triangulation(self):
        """Verify surface mesh generation produced valid triangles without NaNs."""
        facets = self.engine.generate_mesh_facets()
        self.assertGreater(len(facets), 100)
        for facet in facets:
            self.assertFalse(math.isnan(facet.normal.x))
            self.assertFalse(math.isnan(facet.normal.y))
            self.assertFalse(math.isnan(facet.normal.z))
            self.assertFalse(math.isnan(facet.v1.x))
            self.assertFalse(math.isnan(facet.v2.y))
            self.assertFalse(math.isnan(facet.v3.z))

    def test_stl_ascii_export(self):
        """Verify ASCII STL file contains standard syntax headers and facets."""
        stl_ascii = self.engine.export_stl_ascii()
        self.assertTrue(stl_ascii.startswith("solid TinacoFlowerCollector"))
        self.assertTrue(stl_ascii.strip().endswith("endsolid TinacoFlowerCollector"))
        self.assertIn("facet normal", stl_ascii)
        self.assertIn("vertex", stl_ascii)

    def test_stl_binary_export(self):
        """Verify binary STL byte stream conforms to specification."""
        stl_bytes = self.engine.export_stl_binary()
        self.assertGreater(len(stl_bytes), 84)
        header = stl_bytes[:80]
        self.assertTrue(header.startswith(b"Tinaco Flower Rainwater Collector"))
        expected_len = 84 + (len(self.engine.generate_mesh_facets()) * 50)
        self.assertEqual(len(stl_bytes), expected_len)

    def test_step_iso10303_21_export(self):
        """Verify STEP export adheres to ISO 10303-21 standard syntax."""
        step_text = self.engine.export_step_iso10303_21()
        self.assertTrue(step_text.startswith("ISO-10303-21;"))
        self.assertIn("HEADER;", step_text)
        self.assertIn("FILE_SCHEMA(('AUTOMOTIVE_DESIGN { 1 0 10303 214 1 1 1 1 }'));", step_text)
        self.assertIn("DATA;", step_text)
        self.assertIn("MANIFOLD_SOLID_BREP", step_text)
        self.assertIn("ADVANCED_BREP_SHAPE_REPRESENTATION", step_text)
        self.assertIn("CLOSED_SHELL", step_text)
        self.assertIn("CONICAL_SURFACE", step_text)
        self.assertIn("CYLINDRICAL_SURFACE", step_text)
        self.assertTrue(step_text.strip().endswith("END-ISO-10303-21;"))

    def test_bill_of_materials_generation(self):
        """Verify complete fabrication BOM is generated with all items."""
        bom = self.engine.generate_bill_of_materials()
        self.assertIsInstance(bom, BillOfMaterials)
        self.assertEqual(len(bom.items), 7)
        self.assertGreater(bom.total_mass_kg, 6.0)
        self.assertAlmostEqual(bom.estimated_hardware_cost_usd, 48.50)


class TestHydraulicsEngine(unittest.TestCase):
    """Validation test cases for fluid dynamics and drainage capacity."""

    def setUp(self):
        """Initialize hydraulic engine before each test."""
        self.config = FlowerCollectorConfig()
        self.engine = HydraulicEngine(self.config)

    def test_hydraulic_analysis_results(self):
        """Verify peak storm drainage capacity and safety factor adequacy."""
        res = self.engine.analyze(rainfall_intensity_mm_per_hr=80.0)
        self.assertTrue(res.is_adequate)
        self.assertGreater(res.safety_factor, 100.0)
        self.assertLess(res.drainage_transit_time_sec, 1.5)
        self.assertAlmostEqual(res.catchment_area_m2, 1.5394, places=2)
        self.assertGreater(res.drain_capacity_liters_per_sec, 8.0)
        self.assertLess(res.peak_inflow_liters_per_sec, 0.1)

    def test_extreme_storm_event(self):
        """Verify drainage adequacy under extreme 150 mm/hr storm event."""
        res = self.engine.analyze(rainfall_intensity_mm_per_hr=150.0)
        self.assertTrue(res.is_adequate)
        self.assertGreater(res.safety_factor, 50.0)


class TestEngineeringDrawings(unittest.TestCase):
    """Validation test cases for vector SVG and ASCII drawing generators."""

    def setUp(self):
        """Initialize drawing generator before each test."""
        self.generator = EngineeringDrawingGenerator()

    def test_svg_drawing_structure(self):
        """Verify SVG drawing has valid tags, projections, and title block."""
        svg = self.generator.generate_svg_drawing()
        self.assertTrue(svg.startswith("<svg"))
        self.assertTrue(svg.strip().endswith("</svg>"))
        self.assertIn("VIEW A: TOP (PLAN) VIEW", svg)
        self.assertIn("VIEW B: SECTION A-A ELEVATION", svg)
        self.assertIn("ORGANIZATION: s6pa1rta3n-lab", svg)
        self.assertIn("DIAMETER = 1400 mm", svg)

    def test_ascii_blueprint_structure(self):
        """Verify ASCII schematic includes annotations and dimensions."""
        blueprint = self.generator.generate_ascii_blueprint()
        self.assertIn("PARAMETRIC FLOWER-SHAPED RAINWATER COLLECTOR", blueprint)
        self.assertIn("SLOPE:", blueprint)
        self.assertIn("TINACO TANK RIM:", blueprint)


class TestSettlementEngine(unittest.TestCase):
    """Validation test cases for smart contract escrow settlement calculations."""

    def setUp(self):
        """Initialize settlement engine before each test."""
        self.settlement = SettlementEngine()

    def test_settlement_ledger_accounting(self):
        """Verify nominal amounts, platform coins, and net cashout."""
        receipt = self.settlement.compute_settlement()
        self.assertEqual(receipt.issue_number, 1633)
        self.assertEqual(receipt.solver_reward_usdc, 15.068098)
        self.assertEqual(receipt.entry_bond_usdc, 2.0)
        self.assertEqual(receipt.total_funding_usdc, 17.068098)
        self.assertEqual(receipt.total_listing_coins, 18.835123)
        self.assertEqual(receipt.contributor_coins, 17.893367)
        self.assertEqual(receipt.net_cashout_usd, 12.883224)
        self.assertEqual(receipt.evm_payout_address, "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89")
        self.assertEqual(
            receipt.stellar_payout_address,
            "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
        )
        self.assertEqual(len(receipt.receipt_sha256), 64)

    def test_settlement_json_export(self):
        """Verify settlement receipt can be exported to valid JSON."""
        json_str = self.settlement.export_json()
        self.assertIn('"issue_number": 1633', json_str)
        self.assertIn('"receipt_sha256":', json_str)


class TestSiteMeasurementChecklist(unittest.TestCase):
    """Validation test cases for pre-build site inspection checklist."""

    def test_site_fitment_validation(self):
        """Verify site measurements ensure compatible mounting."""
        checklist = MeasurementChecklist()
        adapter = TinacoAdapter()
        self.assertTrue(checklist.validate_site_suitability(adapter))

        bad_checklist = MeasurementChecklist(overhead_clearance_mm=400.0)
        self.assertFalse(bad_checklist.validate_site_suitability(adapter))

        bad_rim_checklist = MeasurementChecklist(measured_rim_od_mm=750.0)
        self.assertFalse(bad_rim_checklist.validate_site_suitability(adapter))


if __name__ == "__main__":
    unittest.main()
