"""Tests for bounty discovery, token extraction, and normalization logic."""

import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.hunt_bounties import (
    clean_bounty_title,
    extract_amounts,
    is_not_own_repo,
    is_real_external,
    is_real_money,
)


class TestHuntBounties(unittest.TestCase):
    """Test suite verifying bounty hunter filtering and parsing invariants."""

    def test_extract_amounts_supports_floats_and_integers(self) -> None:
        """Verify token extraction handles decimal tokens like 0.99 USDC."""
        self.assertEqual(extract_amounts("Task reward: 0.99 USDC on Base"), [0.99])
        self.assertEqual(extract_amounts("Escrow locked: 1.00 USDC"), [1.0])
        self.assertEqual(extract_amounts("Payout: $500"), [500.0])
        self.assertEqual(extract_amounts("Value: 0.05 ETH"), [0.05])
        self.assertEqual(extract_amounts("Empty text with no rewards"), [])

    def test_clean_bounty_title_removes_duplicate_prefixes(self) -> None:
        """Verify repeated [Bounty] prefixes are collapsed to a single tag."""
        raw = "[Bounty] [Bounty] Fix Base RPC failover client"
        normalized = clean_bounty_title(raw)
        self.assertEqual(normalized, "[Bounty] Fix Base RPC failover client")

        untagged = "Fix Base RPC failover client"
        self.assertEqual(
            clean_bounty_title(untagged),
            "[Bounty] Fix Base RPC failover client",
        )

    def test_is_real_money_enforces_positive_threshold(self) -> None:
        """Verify funded bounty checks reject zero or unextractable amounts."""
        self.assertTrue(is_real_money({"title": "Fix bug (0.99 USDC)", "body": ""}))
        self.assertTrue(is_real_money({"title": "Implement feature", "body": "$100 USDC"}))
        self.assertFalse(is_real_money({"title": "Regular issue", "body": "No money mentioned"}))

    def test_is_not_own_repo_filtering(self) -> None:
        """Verify repository URL filtering excludes own repos."""
        self.assertFalse(
            is_not_own_repo({
                "html_url": "https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/10"
            })
        )
        self.assertTrue(
            is_not_own_repo({
                "html_url": "https://github.com/ethereum/solidity/issues/42"
            })
        )

    def test_is_real_external_filters_internals(self) -> None:
        """Verify external qualification rejects internal test issues."""
        external_item = {
            "title": "[Bounty] Implement client",
            "body": "Production issue for external contributor",
            "html_url": "https://github.com/external/repo/issues/1",
        }
        self.assertTrue(is_real_external(external_item))


if __name__ == "__main__":
    unittest.main()
