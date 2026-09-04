"""Unit tests for Automated Upstream Agent Bounties Claim Dispatcher.
Resolves Issue #844: Claim NSPG13/agent-bounties#842 ($89 USD).
"""

import unittest
from scripts.claim_upstream_agent_bounties import (
    UpstreamClaimDispatcher,
    UpstreamClaimTarget,
)


class TestUpstreamClaimDispatcher(unittest.TestCase):
    def setUp(self):
        self.dispatcher = UpstreamClaimDispatcher(
            solver_address="0x740bbea2c8075e699c50c20ce71be0a88d6263ec"
        )

    def test_parse_claim_command(self):
        cmd1 = "Claim NSPG13/agent-bounties#842"
        res1 = self.dispatcher.parse_claim_command(cmd1)
        self.assertIsNotNone(res1)
        self.assertEqual(res1, ("NSPG13/agent-bounties", 842))

        cmd2 = "/claim zhangjiayang6835-cyber/bounty-plaza#835"
        res2 = self.dispatcher.parse_claim_command(cmd2)
        self.assertIsNotNone(res2)
        self.assertEqual(res2, ("zhangjiayang6835-cyber/bounty-plaza", 835))

        invalid = "Just a general comment"
        self.assertIsNone(self.dispatcher.parse_claim_command(invalid))

    def test_dispatch_claim_success(self):
        target = self.dispatcher.create_claim_target("NSPG13/agent-bounties", 842)
        result = self.dispatcher.dispatch_claim(target)

        self.assertTrue(result["success"])
        self.assertEqual(result["status"], "active")
        self.assertEqual(result["claim_key"], "NSPG13/agent-bounties#842")
        self.assertIn("https://github.com/NSPG13/agent-bounties/issues/842", result["target_url"])
        self.assertIn("/claim NSPG13/agent-bounties#842", result["claim_payload"])
        self.assertIn("0x740bbea2c8075e699c50c20ce71be0a88d6263ec", result["claim_payload"])

    def test_duplicate_claim_prevention(self):
        target = self.dispatcher.create_claim_target("NSPG13/agent-bounties", 842)
        res1 = self.dispatcher.dispatch_claim(target)
        self.assertTrue(res1["success"])

        # Second claim attempt while still active
        res2 = self.dispatcher.dispatch_claim(target)
        self.assertFalse(res2["success"])
        self.assertEqual(res2["status"], "already_claimed")
        self.assertIn("already active and locked", res2["message"])

    def test_release_and_reclaim(self):
        target = self.dispatcher.create_claim_target("NSPG13/agent-bounties", 842)
        self.dispatcher.dispatch_claim(target)

        released = self.dispatcher.release_claim("NSPG13/agent-bounties", 842)
        self.assertTrue(released)

        # After release, re-claiming is allowed
        res3 = self.dispatcher.dispatch_claim(target)
        self.assertTrue(res3["success"])


if __name__ == "__main__":
    unittest.main()
