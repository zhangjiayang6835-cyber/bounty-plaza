import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))

from hunt_bounties import extract_amounts, is_real_money, REAL_MONEY, create_issue


class TestHuntBounties(unittest.TestCase):
    def test_issue_1633_body_extraction(self):
        """Test that 15.068098 USDC is extracted as 15, not 68098."""
        body = """
- **Current work state:** `verification_pending`
- **Current payment state:** `escrowed`
- **Current competition state:** `exclusive_claim`
- **Solver reward:** 15.068098 USDC
- **Entry/claim bond:** 2.00 USDC
- **Funding:** 17.068098 / 17.068098 USDC
- **Verifier:** signed_quorum (`signed_quorum`; ready: `true`)
"""
        amounts = extract_amounts(body)
        self.assertEqual(amounts, [15, 2, 17])
        self.assertNotIn(68098, amounts)

    def test_issue_1633_not_real_money_under_threshold(self):
        """Issue 1633 has max amount 17 (< 25), so it should not qualify as real bounty."""
        item = {
            "title": "[Bounty] Flower-shaped rainwater collector for a tinaco",
            "body": """
- **Solver reward:** 15.068098 USDC
- **Entry/claim bond:** 2.00 USDC
- **Funding:** 17.068098 / 17.068098 USDC
""",
        }
        self.assertFalse(is_real_money(item))

    def test_title_deduplication(self):
        """Titles with existing [Bounty] tags should not produce [Bounty] [Bounty]."""
        cases = [
            ("[Bounty] Flower-shaped rainwater collector", "[Bounty] Flower-shaped rainwater collector"),
            ("[Bounty] [Bounty] Nested bounty title", "[Bounty] Nested bounty title"),
            ("[bounty] Lowercase bounty prefix", "[Bounty] Lowercase bounty prefix"),
            ("Normal title without bounty tag", "[Bounty] Normal title without bounty tag"),
        ]
        import re
        for input_title, expected in cases:
            clean_title = re.sub(r"^(?:\[bounty\]\s*)+", "", input_title, flags=re.I).strip()
            result_title = f"[Bounty] {clean_title[:80]}"
            self.assertEqual(result_title, expected)

    def test_extract_amounts_currencies(self):
        """Test extraction across dollar amounts, crypto tokens, and various formats."""
        self.assertEqual(extract_amounts("$50"), [50])
        self.assertEqual(extract_amounts("$ 50"), [50])
        self.assertEqual(extract_amounts("$1,000"), [1000])
        self.assertEqual(extract_amounts("$1,000.50"), [1000])
        self.assertEqual(extract_amounts("$1,000.75"), [1001])
        self.assertEqual(extract_amounts("$100.00"), [100])
        self.assertEqual(extract_amounts("100 USDC"), [100])
        self.assertEqual(extract_amounts("100USDC"), [100])
        self.assertEqual(extract_amounts("50 USDT"), [50])
        self.assertEqual(extract_amounts("1,000 DAI"), [1000])
        self.assertEqual(extract_amounts("bounty: $500"), [500])
        self.assertEqual(extract_amounts("bounty of $1,000"), [1000])

    def test_real_money_regex(self):
        """Verify REAL_MONEY regex correctly matches real currency expressions."""
        self.assertTrue(REAL_MONEY.search("$100"))
        self.assertTrue(REAL_MONEY.search("15.068098 USDC"))
        self.assertTrue(REAL_MONEY.search("50 USDT"))
        self.assertTrue(REAL_MONEY.search("bounty: $50"))
        self.assertFalse(REAL_MONEY.search("bounty of 100 points"))
        self.assertFalse(REAL_MONEY.search("earn XP rewards"))


if __name__ == "__main__":
    unittest.main()
