"""Unit tests for Automated Top Target Claim Orchestrator Subsystem.
Resolves Issue #845: Claim Top Target Issue ($89 USD).
"""

import unittest
from scripts.claim_top_target import (
    TargetBounty,
    TopTargetClaimEngine,
)


class TestTopTargetClaimEngine(unittest.TestCase):
    def setUp(self):
        self.engine = TopTargetClaimEngine(lock_duration_hours=24)

    def test_priority_score_and_margin_calculation(self):
        bounty = TargetBounty(
            issue_number=842,
            title="Verification Complete: Runbook Schema",
            prize_usd=89.0,
            verifier_type="deterministic_module",
            is_claimed=False,
            proof_fee_usd=0.10,
            gas_fee_usd=0.01,
            settlement_latency_seconds=120.0,
        )
        self.assertAlmostEqual(bounty.net_margin_usd, 88.89, places=2)
        # Yield velocity: (88.89 / 120.0) * 60 * 1.5
        expected_score = (88.89 / 120.0) * 60.0 * 1.5
        self.assertAlmostEqual(bounty.priority_score, expected_score, places=2)

    def test_claimed_bounty_has_zero_priority(self):
        bounty = TargetBounty(
            issue_number=900,
            title="Already Claimed Bounty",
            prize_usd=1000.0,
            is_claimed=True,
        )
        self.assertEqual(bounty.priority_score, 0.0)

    def test_select_top_target_picks_highest_yield_unclaimed(self):
        candidates = [
            TargetBounty(
                issue_number=1,
                title="Slow Human Review Task",
                prize_usd=200.0,
                verifier_type="manual_committee",
                settlement_latency_seconds=86400.0,  # 24 hours
            ),
            TargetBounty(
                issue_number=2,
                title="Fast Base Mainnet Autonomous Bounty",
                prize_usd=89.0,
                verifier_type="deterministic_module",
                settlement_latency_seconds=60.0,  # 1 min
            ),
            TargetBounty(
                issue_number=3,
                title="Claimed High Value Bounty",
                prize_usd=5000.0,
                is_claimed=True,
            ),
        ]
        top = self.engine.select_top_target(candidates)
        self.assertIsNotNone(top)
        self.assertEqual(top.issue_number, 2)

    def test_generate_claim_payload(self):
        target = TargetBounty(
            issue_number=842,
            title="Fast Autonomous Verification",
            prize_usd=89.0,
        )
        payload = self.engine.generate_claim_payload(target, solver_id="wiliancolomboo-tech")
        self.assertEqual(payload["issue_number"], 842)
        self.assertIn("/claim zhangjiayang6835-cyber/bounty-plaza#842", payload["command"])
        self.assertIn("wiliancolomboo-tech", payload["comment_body"])

    def test_process_bounties_batch(self):
        raw_items = [
            {"number": 101, "title": "Bounty 1", "prize_usd": 50.0, "is_claimed": False, "settlement_latency_seconds": 100},
            {"number": 102, "title": "Bounty 2", "prize_usd": 150.0, "is_claimed": False, "settlement_latency_seconds": 100},
        ]
        result = self.engine.process_bounties(raw_items)
        self.assertTrue(result["selected"])
        self.assertEqual(result["total_candidates"], 2)
        self.assertEqual(result["top_target"]["issue_number"], 102)


if __name__ == "__main__":
    unittest.main()
