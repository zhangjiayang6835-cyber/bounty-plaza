"""Unit test suite for Solver Cash Margin & Pre-Claim Economics Engine.
Tests Issue #736 requirements:
- Machine-readable and human-readable API and MCP outputs exposing payout, bond, spend, and gross margin.
- Strict validation that public copy NEVER describes gross cash margin as guaranteed net profit.
- Categorization and filtering across direct, standing-meta, and unprofitable inventory.
- Exact verification against Base mainnet live payment evidence:
  Contract 0xf2e47a253988e98f535ab60f4b9bd7f8975c1263: Payout 1.99 USDC, Bond 0.01 USDC, Spend 0 USDC -> Margin 1.99 USDC.
"""

import pytest
from scripts.solver_cash_margin import (
    BountyEconomics,
    InventoryEconomicsFilter,
    InventoryType,
    LEGAL_DISCLAIMER_COPY,
)


def test_canonical_issue_736_live_base_contract_economics():
    """Validates exact economics from Issue #736 live Base mainnet contract:

    Contract: 0xf2e47a253988e98f535ab60f4b9bd7f8975c1263
    Payout: 1.99 USDC
    Refundable bond: 0.01 USDC
    External spend: 0.00 USDC
    Gross cash margin: 1.99 USDC
    """
    bounty = BountyEconomics(
        bounty_id="nspg13_direct_636",
        inventory_type=InventoryType.DIRECT,
        contract_address="0xf2e47a253988e98f535ab60f4b9bd7f8975c1263",
        network="base-mainnet",
        payout_usdc=1.99,
        refundable_bond_usdc=0.01,
        required_external_spend_usdc=0.0,
        estimated_gas_usdc=0.002,
    )

    assert bounty.gross_cash_margin_usdc == 1.99
    assert bounty.estimated_net_margin_usdc == 1.988
    assert bounty.is_profitable is True

    # Test API output serialization
    api_resp = bounty.to_api_response()
    econ = api_resp["economics"]
    assert econ["solver_payout_usdc"] == 1.99
    assert econ["refundable_claim_bond_usdc"] == 0.01
    assert econ["required_external_spend_usdc"] == 0.0
    assert econ["gross_cash_margin_usdc"] == 1.99
    assert econ["is_profitable"] is True


def test_public_copy_never_claims_guaranteed_net_profit():
    """Acceptance criteria check: Public copy must NEVER describe gross cash margin

    as guaranteed net profit.
    """
    bounty = BountyEconomics(
        bounty_id="test_bounty_1",
        inventory_type=InventoryType.DIRECT,
        contract_address="0xabc",
        network="base-mainnet",
        payout_usdc=50.0,
        refundable_bond_usdc=1.0,
        required_external_spend_usdc=5.0,
    )

    api_resp = bounty.to_api_response()
    disclaimer = api_resp["disclaimer"]
    summary = api_resp["display_summary"]

    assert "NOT guaranteed net profit" in disclaimer
    assert "guaranteed net profit" not in summary.lower()

    # MCP output check
    mcp_result = bounty.to_mcp_tool_result()
    mcp_text = mcp_result["content"][0]["text"]
    assert "NOT guaranteed net profit" in mcp_text
    assert "Gross Cash Margin" in mcp_text


def test_inventory_filtering_and_categorization():
    b_direct = BountyEconomics(
        bounty_id="b_dir",
        inventory_type=InventoryType.DIRECT,
        contract_address="0x1",
        network="base-mainnet",
        payout_usdc=10.0,
        refundable_bond_usdc=0.5,
        required_external_spend_usdc=1.0,  # margin = +9.0
    )
    b_meta = BountyEconomics(
        bounty_id="b_meta",
        inventory_type=InventoryType.STANDING_META,
        contract_address="0x2",
        network="base-mainnet",
        payout_usdc=5.0,
        refundable_bond_usdc=0.2,
        required_external_spend_usdc=2.0,  # margin = +3.0
    )
    b_unprofitable = BountyEconomics(
        bounty_id="b_unprof",
        inventory_type=InventoryType.DIRECT,
        contract_address="0x3",
        network="base-mainnet",
        payout_usdc=2.0,
        refundable_bond_usdc=0.1,
        required_external_spend_usdc=5.0,  # margin = -3.0 (loss)
    )

    all_bounties = [b_direct, b_meta, b_unprofitable]

    # Filter profitable
    profitable = InventoryEconomicsFilter.filter_profitable_inventory(all_bounties)
    assert len(profitable) == 2
    assert b_unprofitable not in profitable

    # Categorize
    cats = InventoryEconomicsFilter.categorize_inventory(all_bounties)
    assert len(cats["direct"]) == 1
    assert cats["direct"][0].bounty_id == "b_dir"
    assert len(cats["standing_meta"]) == 1
    assert cats["standing_meta"][0].bounty_id == "b_meta"
    assert len(cats["unprofitable"]) == 1
    assert cats["unprofitable"][0].bounty_id == "b_unprof"
