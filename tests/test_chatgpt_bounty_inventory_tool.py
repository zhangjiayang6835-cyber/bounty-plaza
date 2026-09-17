"""Unit test suite for Public ChatGPT Bounty Inventory Tool (list_autonomous_bounties).
Tests Issue #738 requirements:
- A committed test invokes the public tool name used by the mounted ChatGPT app (list_autonomous_bounties).
- The test fails on the unknown-or-unavailable-tool response and passes after the fix.
- Returns claimable-only Base-mainnet inventory without INVALID_ARGUMENT.
- The response remains fail-closed about funding, verifier readiness, and BountySettled evidence.
- Verified against Base mainnet contract: 0xc13ccf6c6a03b53f836d433c5e628f06bbc1dbf4.
"""

import pytest
from scripts.chatgpt_bounty_inventory_tool import (
    BOUNTY_SETTLED_EVIDENCE_NOTICE,
    ChatGPTToolRegistry,
    ErrorCode,
    OnChainBountyItem,
    PublicBountyInventoryService,
    create_configured_chatgpt_registry,
)


def test_tool_fails_before_registration_unknown_tool():
    """Acceptance criterion 1 & 2: Proves test fails on unknown-or-unavailable-tool

    response prior to tool mount, and passes after registration.
    """
    empty_registry = ChatGPTToolRegistry()
    # Before registration: tool is unknown
    call_res = empty_registry.invoke_tool(
        "list_autonomous_bounties",
        {"network": "base-mainnet", "status": "claimable"}
    )
    assert call_res["ok"] is False
    assert call_res["error_code"] == ErrorCode.UNKNOWN_TOOL.value
    assert "unknown or unavailable" in call_res["message"]
    assert call_res["status_code"] == 404

    # After registration: tool is mounted and successfully callable
    configured_registry = create_configured_chatgpt_registry()
    success_res = configured_registry.invoke_tool(
        "list_autonomous_bounties",
        {"network": "base-mainnet", "status": "claimable"}
    )
    assert success_res["ok"] is True
    assert success_res["network"] == "base-mainnet"
    assert success_res["count"] >= 1


def test_canonical_base_mainnet_contract_evidence():
    """Acceptance criterion: Return claimable Base mainnet inventory without INVALID_ARGUMENT

    matching contract 0xc13ccf6c6a03b53f836d433c5e628f06bbc1dbf4.
    """
    registry = create_configured_chatgpt_registry()
    res = registry.invoke_tool(
        "list_autonomous_bounties",
        {"network": "base-mainnet", "status": "claimable"}
    )

    assert res["ok"] is True
    bounties = res["bounties"]
    assert len(bounties) >= 1

    canonical = next(b for b in bounties if b["contract_address"] == "0xc13ccf6c6a03b53f836d433c5e628f06bbc1dbf4")
    assert canonical["status"] == "claimable"
    assert canonical["funding"]["confirmed_usdc"] == 2.00
    assert canonical["funding"]["is_fully_funded"] is True
    assert canonical["economics"]["solver_payout_usdc"] == 1.99
    assert canonical["economics"]["refundable_bond_usdc"] == 0.01
    assert canonical["economics"]["gross_cash_margin_usdc"] == 1.99
    assert canonical["verifier"]["suite"] == "sandboxed_regression_v1"
    assert canonical["verifier"]["ready"] is True


def test_fail_closed_checks_funding_verifier_terms():
    """Acceptance criterion: The response remains fail-closed about funding,

    verifier readiness, and BountySettled evidence.
    """
    service = PublicBountyInventoryService()

    # 1. Add underfunded bounty (1.50 / 2.00 USDC)
    service.add_bounty(
        OnChainBountyItem(
            contract_address="0xUnderfunded",
            network="base-mainnet",
            status="claimable",
            confirmed_funding_usdc=1.50,
            required_funding_usdc=2.00,
            solver_payout_usdc=1.99,
            refundable_bond_usdc=0.01,
            required_external_spend_usdc=0.00,
            verifier_suite="sandboxed_regression_v1",
            verifier_ready=True,
        )
    )

    # 2. Add unready verifier bounty
    service.add_bounty(
        OnChainBountyItem(
            contract_address="0xUnreadyVerifier",
            network="base-mainnet",
            status="claimable",
            confirmed_funding_usdc=2.00,
            required_funding_usdc=2.00,
            solver_payout_usdc=1.99,
            refundable_bond_usdc=0.01,
            required_external_spend_usdc=0.00,
            verifier_suite="sandboxed_regression_v1",
            verifier_ready=False,  # Unready
        )
    )

    # 3. Add invalid terms bounty
    service.add_bounty(
        OnChainBountyItem(
            contract_address="0xInvalidTerms",
            network="base-mainnet",
            status="claimable",
            confirmed_funding_usdc=2.00,
            required_funding_usdc=2.00,
            solver_payout_usdc=1.99,
            refundable_bond_usdc=0.01,
            required_external_spend_usdc=0.00,
            verifier_suite="sandboxed_regression_v1",
            verifier_ready=True,
            is_terms_valid=False,  # Invalid
        )
    )

    res = service.list_autonomous_bounties({"network": "base-mainnet", "status": "claimable"})
    contracts = [b["contract_address"] for b in res["bounties"]]

    # Fail closed: none of the invalid bounties appear
    assert "0xUnderfunded" not in contracts
    assert "0xUnreadyVerifier" not in contracts
    assert "0xInvalidTerms" not in contracts

    # Evidence notice is present
    assert res["payment_evidence_notice"] == BOUNTY_SETTLED_EVIDENCE_NOTICE
    assert "BountySettled" in res["payment_evidence_notice"]


def test_invalid_argument_validation():
    """Acceptance criterion: Validate invalid inputs return clean INVALID_ARGUMENT

    without unhandled crashes.
    """
    registry = create_configured_chatgpt_registry()

    # Invalid network
    err_net = registry.invoke_tool("list_autonomous_bounties", {"network": "invalid-chain"})
    assert err_net["ok"] is False
    assert err_net["error_code"] == ErrorCode.INVALID_ARGUMENT.value
    assert "Unsupported network" in err_net["message"]

    # Negative limit
    err_lim = registry.invoke_tool("list_autonomous_bounties", {"limit": -5})
    assert err_lim["ok"] is False
    assert err_lim["error_code"] == ErrorCode.INVALID_ARGUMENT.value
    assert "positive integer" in err_lim["message"]
