"""Unit tests for Automated Compatible Bounty Issue Creator Subsystem.
Verifies compatibility filtering, reward multiplier calculation, deduplication,
and markdown issue schema compliance for Issue #840 ($89 USD).
"""

import unittest
from scripts.automate_compatible_bounties import (
    CandidateBounty,
    CompatibleBountyAutomationEngine,
    COIN_MULTIPLIER,
)


class TestAutomateCompatibleBounties(unittest.TestCase):
    def setUp(self):
        self.engine = CompatibleBountyAutomationEngine(
            existing_source_urls={"https://github.com/example/existing-bounty"},
            min_prize_usd=25.0
        )

    def test_compatible_bounty_accepted(self):
        cand = CandidateBounty(
            source_platform="Base Mainnet",
            source_url="https://agentbounties.app/bounties/840",
            title="Shortest Deterministic Agent Earning Run",
            description="Write a deterministic runbook with predicate verification.",
            prize_usd=89.0,
            difficulty="Medium",
            verifier_type="deterministic_module",
            verifier_ready=True,
        )
        compat, reason = self.engine.is_compatible(cand)
        self.assertTrue(compat)
        self.assertEqual(reason, "Compatible")

    def test_coin_multiplier_calculation(self):
        cand = CandidateBounty(
            source_platform="Base Mainnet",
            source_url="https://agentbounties.app/bounties/840",
            title="Test Multiplier",
            description="Testing coins multiplier.",
            prize_usd=100.0,
        )
        self.assertEqual(cand.coin_reward, 125)  # 100 * 1.25
        payload = self.engine.format_issue_payload(cand)
        self.assertIn("125 coins", payload["body"])
        self.assertIn("$100.00", payload["body"])

    def test_reject_below_minimum_prize(self):
        cand = CandidateBounty(
            source_platform="Opire",
            source_url="https://opire.dev/task/123",
            title="Tiny Micro Task",
            description="A task under $25 USD threshold.",
            prize_usd=15.0,
        )
        compat, reason = self.engine.is_compatible(cand)
        self.assertFalse(compat)
        self.assertIn("below minimum threshold", reason)

    def test_reject_duplicate_source_url(self):
        cand = CandidateBounty(
            source_platform="GitHub",
            source_url="https://github.com/example/existing-bounty/",
            title="Duplicate Bounty",
            description="Duplicate URL test.",
            prize_usd=50.0,
        )
        compat, reason = self.engine.is_compatible(cand)
        self.assertFalse(compat)
        self.assertIn("already tracked", reason)

    def test_reject_unready_verifier(self):
        cand = CandidateBounty(
            source_platform="Base Mainnet",
            source_url="https://agentbounties.app/bounties/pending-verifier",
            title="Unready Verifier Bounty",
            description="Requires offline human dispute committee.",
            prize_usd=500.0,
            verifier_ready=False,
        )
        compat, reason = self.engine.is_compatible(cand)
        self.assertFalse(compat)
        self.assertIn("Verifier is not ready", reason)

    def test_reject_missing_fields(self):
        cand = CandidateBounty(
            source_platform="Base Mainnet",
            source_url="https://agentbounties.app/bounties/empty",
            title="",
            description="",
            prize_usd=100.0,
        )
        compat, reason = self.engine.is_compatible(cand)
        self.assertFalse(compat)
        self.assertIn("Missing title or description", reason)

    def test_batch_processing_and_deduplication(self):
        candidates = [
            CandidateBounty(
                source_platform="Base Mainnet",
                source_url="https://agentbounties.app/bounties/task-1",
                title="Task One",
                description="Valid task 1",
                prize_usd=89.0,
            ),
            CandidateBounty(
                source_platform="Base Mainnet",
                source_url="https://agentbounties.app/bounties/task-1",  # duplicate in same batch
                title="Task One Duplicate",
                description="Valid task 1 duplicate",
                prize_usd=89.0,
            ),
            CandidateBounty(
                source_platform="Base Mainnet",
                source_url="https://agentbounties.app/bounties/task-2",
                title="Task Two",
                description="Valid task 2",
                prize_usd=200.0,
            ),
            CandidateBounty(
                source_platform="GrantFox",
                source_url="https://grantfox.io/grants/low",
                title="Low Prize",
                description="Too low",
                prize_usd=10.0,
            ),
        ]
        result = self.engine.process_candidates(candidates)
        self.assertEqual(result["total_candidates"], 4)
        self.assertEqual(result["compatible_count"], 2)
        self.assertEqual(result["skipped_count"], 2)
        self.assertEqual(len(result["issues"]), 2)
        self.assertIn("Task One", result["issues"][0]["title"])
        self.assertIn("Task Two", result["issues"][1]["title"])


if __name__ == "__main__":
    unittest.main()
