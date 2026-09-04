"""Unit tests for Copperhead Create 8-Stage E2E Test Pipeline & Verification Engine.
Resolves Issue #686: [Bounty] Bounty: end-to-end test copperhead create (brief -> clean full run) + findings report ($50 USD).
Upstream Reference: chouhanindustries/copperhead#66.

Validates:
1. Complete 8-stage pipeline progression from natural-language brief to final dev plan.
2. Production of all critical intermediate artifacts (spec seed, arch, BOM, KiCad sch, pcb, gerbers, BSP header, plan).
3. Hardened ERC mitigation rejecting false-green passes on empty schematics.
4. Active sliding-window pruning of `.history/` directory to prevent unbounded disk growth.
5. Findings report generation and formatting.
"""

import os
import tempfile
import unittest

from scripts.copperhead_create_e2e_runner import (
    CopperheadE2EPipeline,
    HardwareBrief,
    PIPELINE_STAGES,
)


class TestCopperheadCreateE2ERunner(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.pipeline = CopperheadE2EPipeline(output_dir=self.tmp_dir)
        self.brief = HardwareBrief(
            project_name="RP2040-Sensor-Node",
            description="Compact RP2040 environmental telemetry node with USB-C, I2C sensor bus, and RGB status LED.",
        )

    def tearDown(self):
        import shutil
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_pipeline_stages_constant_completeness(self):
        """Verifies all 8 stages are defined in exact canonical order."""
        self.assertEqual(len(PIPELINE_STAGES), 8)
        self.assertEqual(
            PIPELINE_STAGES,
            [
                "spec-seed",
                "architecture",
                "part-selection",
                "schematic",
                "layout-draft",
                "outputs",
                "firmware",
                "dev-plan",
            ],
        )

    def test_full_pipeline_clean_run_execution(self):
        """Executes all 8 stages cleanly and verifies output artifacts."""
        result = self.pipeline.execute_full_pipeline(self.brief)
        self.assertTrue(result["all_stages_clean"])
        self.assertEqual(result["stages_completed"], 8)
        self.assertEqual(result["total_stages"], 8)
        self.assertTrue(os.path.exists(result["report_path"]))

        # Check key files
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "01_spec_seed.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "02_architecture.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "03_bom_selection.json")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "board.kicad_sch")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "board.kicad_pcb")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "board_config.h")))
        self.assertTrue(os.path.exists(os.path.join(self.tmp_dir, "08_bringup_dev_plan.md")))

    def test_hardened_erc_blocks_empty_bom(self):
        """Validates that empty BOM component list fails ERC rather than returning false-green."""
        # Run spec seed and arch
        self.pipeline.run_stage_spec_seed(self.brief)
        self.pipeline.run_stage_architecture()

        # Set empty part selection
        self.pipeline.checkpoints["part-selection"] = []

        # Schematic should fail ERC
        sch_record = self.pipeline.run_stage_schematic()
        self.assertEqual(sch_record.status, "FAILED")
        self.assertIn("Hardened ERC Failure", sch_record.error_message)
        self.assertEqual(sch_record.metrics["erc_errors"], 1)

    def test_history_pruning_bounds_disk_usage(self):
        """Validates that sliding-window snapshot retention keeps <= 5 files in .history."""
        hist_dir = os.path.join(self.tmp_dir, ".history")
        # Create 10 dummy snapshots
        for i in range(10):
            p = os.path.join(hist_dir, f"dummy_{i}.bak")
            with open(p, "w") as f:
                f.write(f"snap_{i}")

        self.pipeline._prune_history_directory()
        remaining_files = os.listdir(hist_dir)
        self.assertLessEqual(len(remaining_files), 5)

    def test_findings_report_contains_metrics_and_mitigations(self):
        """Verifies findings report markdown contains execution summary and root-cause analysis."""
        self.pipeline.execute_full_pipeline(self.brief)
        report_text = self.pipeline.generate_findings_report(clean_run=True)

        self.assertIn("CLEAN FULL RUN (8/8 STAGES)", report_text)
        self.assertIn("False-Green ERC on Empty Schematics", report_text)
        self.assertIn("Transactional Stage Checkpoints", report_text)
        self.assertIn("Bounded `.history/` Directory", report_text)
        self.assertIn("Manufacturability Signoff", report_text)


if __name__ == "__main__":
    unittest.main()
