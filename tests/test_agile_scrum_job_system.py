"""Unit tests for Agile & SCRUM Station Role Management System.
Resolves Issue #673: [BOUNTY] [299$] [0.034568 BTC] Implement a Agile/SCRUM managment for station roles.
Upstream Reference: Iamgoofball/-tg-station#226.

Validates:
1. JobScrumProfile initialization across on-site, hybrid, and remote work modes.
2. Accurate overwork detection when working hours exceed standard shift or burnout reaches threshold.
3. Nutritional rice bowl recovery mechanics restoring stamina and mitigating burnout.
4. Morale companion / buffer stress mitigation factors.
5. AgileScrumSubsystem standup cycle, blocker resolution, sprint rollover, and BYOND DM code generation.
"""

import unittest
from scripts.agile_scrum_job_system import (
    AgileScrumSubsystem,
    JobScrumProfile,
    WorkMode,
)


class TestAgileScrumJobSystem(unittest.TestCase):
    def setUp(self):
        self.subsystem = AgileScrumSubsystem()
        self.atmos_worker = JobScrumProfile(
            job_title="Senior Atmospheric Technician",
            department="Atmospherics",
            work_mode=WorkMode.HYBRID,
            standard_shift_hours=8.0,
            story_points_committed=12,
        )

    def test_default_roster_initialization(self):
        """Verifies default station roles are registered with Agile profiles."""
        self.assertGreaterEqual(len(self.subsystem.roster), 7)
        self.assertIn("Atmospheric Technician", self.subsystem.roster)
        self.assertIn("Station Engineer", self.subsystem.roster)
        self.assertIn("Chief Medical Officer", self.subsystem.roster)

    def test_work_hour_logging_and_overwork_detection(self):
        """Verifies logging hours updates burnout index and triggers overwork flags."""
        self.assertFalse(self.atmos_worker.is_overworked)

        # Log 4 hours (normal shift)
        self.atmos_worker.log_work_hours(4.0)
        self.assertFalse(self.atmos_worker.is_overworked)
        self.assertGreater(self.atmos_worker.burnout_index, 0.0)

        # Log an additional 5 hours (total 9h > 8h standard shift)
        self.atmos_worker.log_work_hours(5.0)
        self.assertTrue(self.atmos_worker.is_overworked)
        self.assertEqual(self.atmos_worker.accumulated_hours, 9.0)

    def test_bowl_of_rice_nutritional_recovery(self):
        """Verifies consuming bowl of rice mitigates burnout and boosts KPI score."""
        self.atmos_worker.burnout_index = 60.0
        initial_kpi = self.atmos_worker.kpi_score

        # Consume rice bowl
        recovered = self.atmos_worker.consume_bowl_of_rice()
        self.assertTrue(recovered)
        self.assertEqual(self.atmos_worker.burnout_index, 35.0)
        self.assertGreater(self.atmos_worker.kpi_score, initial_kpi)

        # Second attempt without fresh bowl returns False
        second_attempt = self.atmos_worker.consume_bowl_of_rice()
        self.assertFalse(second_attempt)

    def test_morale_buffer_reduces_stress_accumulation(self):
        """Verifies companion morale buffer lowers the rate of burnout accumulation."""
        standard_worker = JobScrumProfile("Engineer A", "Eng", WorkMode.ON_SITE)
        buffered_worker = JobScrumProfile("Engineer B", "Eng", WorkMode.ON_SITE, has_morale_buffer=True)

        standard_worker.log_work_hours(6.0)
        buffered_worker.log_work_hours(6.0)

        self.assertLess(buffered_worker.burnout_index, standard_worker.burnout_index)

    def test_remote_work_accumulates_less_fatigue_than_onsite(self):
        """Verifies remote workers accumulate significantly less fatigue per hour."""
        onsite = JobScrumProfile("Field Mechanic", "Engineering", WorkMode.ON_SITE)
        remote = JobScrumProfile("Remote Ops Analyst", "Engineering", WorkMode.REMOTE_WORK)

        onsite.log_work_hours(8.0)
        remote.log_work_hours(8.0)

        self.assertLess(remote.burnout_index, onsite.burnout_index)

    def test_daily_standup_resolves_blockers_and_overwork(self):
        """Verifies daily standup identifies overworked crew and dispenses recovery."""
        worker = self.subsystem.roster["Atmospheric Technician"]
        worker.log_work_hours(10.0)  # Overworked
        worker.active_blockers.append("Ruptured tritium manifold on deck 3")

        standup_report = self.subsystem.conduct_daily_standup()
        self.assertGreaterEqual(standup_report["overworked_count"], 1)
        self.assertIn("Atmospheric Technician", standup_report["interventions_applied"])
        self.assertEqual(len(worker.active_blockers), 0)

    def test_sprint_cycle_rollover_resets_counters(self):
        """Verifies 100-tick sprint rollover increments sprint number and resets capacity."""
        initial_sprint = self.subsystem.sprint_number
        self.subsystem.process_sprint_tick(100)

        self.assertEqual(self.subsystem.sprint_number, initial_sprint + 1)
        self.assertEqual(self.subsystem.sprint_tick, 0)
        worker = self.subsystem.roster["Station Engineer"]
        self.assertEqual(worker.accumulated_hours, 0.0)
        self.assertTrue(worker.has_bowl_of_rice)

    def test_dm_code_generation_integrity(self):
        """Verifies BYOND DreamMaker code definitions include necessary procs and variables."""
        dm_code = self.subsystem.generate_dm_code()
        self.assertIn("/datum/controller/subsystem/agile_scrum", dm_code)
        self.assertIn("/datum/job", dm_code)
        self.assertIn("check_overwork()", dm_code)
        self.assertIn("consume_rice_bowl", dm_code)
        self.assertIn("standard_shift_hours", dm_code)


if __name__ == "__main__":
    unittest.main()
