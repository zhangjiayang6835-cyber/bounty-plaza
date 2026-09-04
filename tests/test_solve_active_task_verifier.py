"""Unit tests for Active Task Verification Solver.
Resolves Issue #843 ($89 USD): Solve Active Task #842.
"""

import unittest
from scripts.solve_active_task_verifier import (
    ActiveTaskVerificationSolver,
    CANONICAL_SCHEMA,
    CANONICAL_TASK_ID,
)


class TestActiveTaskVerificationSolver(unittest.TestCase):
    def setUp(self):
        self.solver = ActiveTaskVerificationSolver()

    def test_solve_standard_runbook_success(self):
        result = self.solver.solve()
        self.assertTrue(result["success"])
        self.assertTrue(result["schema_verified"])
        self.assertEqual(result["steps_count"], 6)
        self.assertEqual(result["active_competitions_count"], 5)
        self.assertEqual(len(result["artifact_sha256"]), 64)
        self.assertEqual(len(result["schema_errors"]), 0)

    def test_reject_invalid_schema(self):
        invalid_runbook = {
            "schema_version": "invalid-version",
            "steps": [{"id": "step1", "operation": "op1"}],
        }
        result = self.solver.solve(candidate_runbook=invalid_runbook)
        self.assertFalse(result["success"])
        self.assertFalse(result["schema_verified"])
        self.assertGreater(len(result["schema_errors"]), 0)

    def test_inventory_parsing_filters_inactive(self):
        custom_inv = {
            "network": "base-mainnet",
            "items": [
                {"id": "b1", "title": "Bounty 1", "prize_usdc": 89.0, "state": "active"},
                {"id": "b2", "title": "Bounty 2", "prize_usdc": 99.0, "state": "settled"},
                {"id": "b3", "title": "Bounty 3", "prize_usdc": 50.0, "state": "active"},
                {"id": "b4", "title": "Bounty 4", "prize_usdc": 89.0, "state": "active"},
                {"id": "b5", "title": "Bounty 5", "prize_usdc": 120.0, "state": "active"},
                {"id": "b6", "title": "Bounty 6", "prize_usdc": 67.0, "state": "active"},
            ]
        }
        result = self.solver.solve(mock_inventory=custom_inv)
        self.assertTrue(result["success"])
        self.assertEqual(result["active_competitions_count"], 5)


if __name__ == "__main__":
    unittest.main()
