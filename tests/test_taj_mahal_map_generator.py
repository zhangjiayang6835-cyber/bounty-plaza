"""Unit tests for Taj Mahal BYOND DreamMaker Map (.dmm) & Architectural Engine.
Resolves Issue #664: [BOUNTY] [EASY AI TASK] [OPIRE] [$10000] Add the Taj Mahal.
Upstream Reference: Iamgoofball/-tg-station#162.

Validates:
1. Symmetrical architectural layout including Central Bulbous Dome, 4 Corner Minarets, Charbagh Gardens, and Pietra Dura Inlays.
2. Valid BYOND DMM v2 format compilation with correct grid coordinate bounds.
3. 22-year project timeline scheduling and daily milestone mapping (8,035 days / 22 years).
4. Asset export pipeline creating .dmm map file and DM object definitions.
"""

import os
import tempfile
import unittest

from scripts.taj_mahal_map_generator import (
    DAYS_IN_PROJECT,
    TOTAL_PROJECT_YEARS,
    ProjectSchedule22Years,
    TajMahalDMMBuilder,
)


class TestTajMahalMapGenerator(unittest.TestCase):
    def setUp(self):
        self.builder = TajMahalDMMBuilder(grid_size=32)
        self.scheduler = ProjectSchedule22Years()

    def test_architectural_features_completeness(self):
        """Verifies dome, 4 minarets, pietra dura inlays, and charbagh gardens are present."""
        feature_names = [f.name for f in self.builder.features]
        self.assertIn("Central Bulbous Dome", feature_names)
        self.assertIn("Four Free-Standing Minarets", feature_names)
        self.assertIn("Pietra Dura Floral Inlays", feature_names)
        self.assertIn("Charbagh Quad Garden & Reflection Pools", feature_names)

        # Check 4 corner minarets
        minaret_feat = next(f for f in self.builder.features if "Minarets" in f.name)
        self.assertEqual(len(minaret_feat.coordinates), 4)

    def test_dmm_serialization_format_and_syntax(self):
        """Verifies serialized output complies with BYOND DreamMaker Map v2 structure."""
        dmm_text = self.builder.serialize_to_dmm()
        self.assertIn("// Format: BYOND DMM v2", dmm_text)
        self.assertIn("/turf/open/floor/mineral/marble/dome", dmm_text)
        self.assertIn("/obj/structure/minaret_tower", dmm_text)
        self.assertIn("/turf/open/floor/stone/pietra_dura", dmm_text)
        self.assertIn("/turf/open/water/reflection_pool", dmm_text)
        self.assertIn("(1,1,1) = {\"", dmm_text)

    def test_22_year_project_scheduling_timeline(self):
        """Verifies 22-year schedule spans 8035 days with proper phase transitions."""
        self.assertEqual(self.scheduler.total_days, DAYS_IN_PROJECT)
        self.assertEqual(TOTAL_PROJECT_YEARS, 22)

        # Day 0: Plinth
        day0 = self.scheduler.get_milestone_for_day(0)
        self.assertEqual(day0["year"], 1)
        self.assertIn("Plinth", day0["phase"])
        self.assertEqual(day0["progress_percentage"], 0.0)

        # Year 10 (Day ~3650): Dome
        day3650 = self.scheduler.get_milestone_for_day(3650)
        self.assertEqual(day3650["year"], 11)
        self.assertIn("Dome", day3650["phase"])

        # Final Day (8035): Complete
        day_final = self.scheduler.get_milestone_for_day(DAYS_IN_PROJECT)
        self.assertTrue(day_final["is_completed"])
        self.assertEqual(day_final["progress_percentage"], 100.0)
        self.assertIn("Charbagh", day_final["phase"])

    def test_asset_export_creates_dmm_and_dm_files(self):
        """Verifies export_assets writes .dmm and .dm files to specified directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = self.builder.export_assets(target_dir=tmpdir)
            self.assertTrue(os.path.exists(result["dmm_path"]))
            self.assertTrue(os.path.exists(result["dm_path"]))
            self.assertGreater(result["file_size"], 500)
            self.assertEqual(result["features_count"], 4)

            # Check .dm content
            with open(result["dm_path"], "r", encoding="utf-8") as f:
                dm_content = f.read()
                self.assertIn("/obj/structure/minaret_tower", dm_content)
                self.assertIn("/turf/open/floor/mineral/marble/dome", dm_content)


if __name__ == "__main__":
    unittest.main()
