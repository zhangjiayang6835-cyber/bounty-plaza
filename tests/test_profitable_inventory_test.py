"""Unit test suite for End-to-End Profitable Inventory Contract Test.
Tests Issue #737 requirements:
- One canonical fixture covers API, MCP, discovery feed, and public website inventory.
- Asserts reward, bond, funding, status, terms validity, and verifier readiness across all 4 surfaces.
- Ensures a claimed bounty transitions cleanly, leaving claimable-only results without being treated as corrupt or unpaid.
- Live Base mainnet payment contract: 0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4
"""

import json
import pytest
from scripts.profitable_inventory_test import (
    BountyStatus,
    CanonicalBountyFixture,
    InventoryManager,
    InventorySurfaceRenderer,
)


def test_canonical_fixture_covers_all_four_surfaces():
    """Acceptance criterion 1: One fixture covers API, MCP, discovery feed,

    and public website inventory surfaces.
    """
    fixture = CanonicalBountyFixture()

    # 1. API Surface
    api_payload = InventorySurfaceRenderer.render_api_surface(fixture)
    assert api_payload["contract"] == "0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4"
    assert api_payload["network"] == "base-mainnet"
    assert api_payload["status"] == "claimable"
    assert api_payload["terms_valid"] is True
    assert api_payload["funding"]["confirmed"] == 2.00
    assert api_payload["funding"]["is_fully_funded"] is True
    assert api_payload["economics"]["solver_payout_usdc"] == 1.99
    assert api_payload["economics"]["refundable_bond_usdc"] == 0.01
    assert api_payload["economics"]["required_external_spend_usdc"] == 0.00
    assert api_payload["economics"]["gross_cash_margin_usdc"] == 1.99
    assert api_payload["verifier"]["suite"] == "sandboxed_regression_v1"
    assert api_payload["verifier"]["ready"] is True

    # 2. MCP Surface
    mcp_payload = InventorySurfaceRenderer.render_mcp_surface(fixture)
    assert "content" in mcp_payload
    mcp_text = mcp_payload["content"][0]["text"]
    assert "0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4" in mcp_text
    assert "$1.99 USDC" in mcp_text
    assert "$0.01 USDC" in mcp_text
    assert "CLAIMABLE" in mcp_text
    assert mcp_payload["metadata"]["economics"]["gross_cash_margin_usdc"] == 1.99

    # 3. Discovery Feed Surface
    feed_line = InventorySurfaceRenderer.render_discovery_feed(fixture)
    assert feed_line.startswith("<!-- agent-bounties/github-discovery-v1")
    assert "0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4" in feed_line
    assert '"solver_payout":1.99' in feed_line
    assert '"bond":0.01' in feed_line
    assert '"verifier_ready":true' in feed_line

    # 4. Public Website Surface
    web_payload = InventorySurfaceRenderer.render_public_website_inventory(fixture)
    assert web_payload["badge"] == "CLAIMABLE"
    assert "$1.99 USDC" in web_payload["reward_label"]
    assert "$0.01 USDC bond" in web_payload["bond_label"]
    assert web_payload["action_button_enabled"] is True
    assert "0xad4532e45d371ff5b5c40ebbf0c20687ed9e6fc4" in web_payload["target_url"]


def test_field_level_assertions_economic_and_verifier_integrity():
    """Acceptance criterion 2: Asserts reward, bond, funding, status,

    terms validity, and verifier readiness.
    """
    fixture = CanonicalBountyFixture()
    assert fixture.total_funding_usdc == 2.00
    assert fixture.confirmed_funding_usdc == 2.00
    assert fixture.solver_payout_usdc == 1.99
    assert fixture.refundable_bond_usdc == 0.01
    assert fixture.required_external_spend_usdc == 0.00
    assert fixture.status == BountyStatus.CLAIMABLE
    assert fixture.terms_valid is True
    assert fixture.verifier_ready is True
    assert fixture.verifier_suite == "sandboxed_regression_v1"
    assert fixture.verifier_quorum_threshold == 2


def test_claimed_bounty_clean_transition_and_unpaid_corrupt_protection():
    """Acceptance criterion 3: A claimed bounty leaves claimable-only results

    without being treated as corrupt or unpaid.
    """
    mgr = InventoryManager()
    bounty = CanonicalBountyFixture()
    mgr.add_bounty(bounty)

    # Initial state: 1 claimable bounty
    claimable_initial = mgr.get_claimable_inventory()
    assert len(claimable_initial) == 1
    assert claimable_initial[0].contract_address == bounty.contract_address

    # Claim action occurs
    success = mgr.claim_bounty(bounty.contract_address, solver_address="0xSolver123")
    assert success is True

    # After claim: bounty is NOT in claimable inventory
    claimable_after = mgr.get_claimable_inventory()
    assert len(claimable_after) == 0

    # Verification: bounty remains intact, valid, and fully funded (not corrupt, not unpaid)
    stored_bounty = mgr.bounties[bounty.contract_address]
    assert stored_bounty.status == BountyStatus.CLAIMED
    assert stored_bounty.terms_valid is True
    assert stored_bounty.confirmed_funding_usdc == 2.00
    assert stored_bounty.solver_payout_usdc == 1.99

    # Check website representation reflects CLAIMED state with disabled claim button
    web_claimed = InventorySurfaceRenderer.render_public_website_inventory(stored_bounty)
    assert web_claimed["badge"] == "CLAIMED"
    assert web_claimed["action_button_enabled"] is False
