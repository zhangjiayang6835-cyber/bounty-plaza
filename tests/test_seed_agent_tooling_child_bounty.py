"""Tests for useful agent-tooling child bounty seeding and compliance engine.
Validates Issue #498 resolution for NSPG13/agent-bounties#217 / Base Mainnet (EIP-155:8453 autonomous-v1).
"""

import pytest
import sys
from pathlib import Path

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.seed_agent_tooling_child_bounty import (
    AgentToolingEngine,
    AgentToolCategory,
    ToolInterfaceSchema,
    AgentToolingSubmissionPayload,
    BountyLifecycle,
)


def test_seed_and_fund_tooling_bounty():
    engine = AgentToolingEngine()
    bounty = engine.seed_tooling_bounty(
        creator="0xToolCreatorWallet111",
        tool_name="web3_balance_checker_mcp",
        category=AgentToolCategory.MCP_SERVER,
        solver_reward=0.90,
        verifier_reward=0.10,
        claim_bond=0.10,
    )

    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED
    assert bounty.current_funding_usdc == 0.0

    # Partial deposit
    res1 = engine.deposit_funding(bounty.bounty_id, 0.40, "0xTxDeposit1")
    assert not res1["funded"]
    assert bounty.status == BountyLifecycle.ACTIVATION_BLOCKED

    # Full funding deposit
    res2 = engine.deposit_funding(bounty.bounty_id, 0.60, "0xTxDeposit2")
    assert res2["funded"]
    assert bounty.status == BountyLifecycle.CLAIMABLE_LIVE


def test_claim_anti_self_claim_and_bond_validation():
    engine = AgentToolingEngine()
    bounty = engine.seed_tooling_bounty(
        creator="0xCreatorWallet222",
        tool_name="solana_tx_parser_cli",
        category=AgentToolCategory.CLI_HARNESS,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xFundTx2")

    # Anti-self-claim
    with pytest.raises(ValueError, match="Creator cannot self-claim"):
        engine.claim_bounty(bounty.bounty_id, "0xCreatorWallet222", 0.10)

    # Insufficient bond
    with pytest.raises(ValueError, match="Bond 0.08 below required 0.1"):
        engine.claim_bounty(bounty.bounty_id, "0xIndependentDev333", 0.08)

    # Valid exclusive claim
    res = engine.claim_bounty(bounty.bounty_id, "0xIndependentDev333", 0.10)
    assert res["status"] == BountyLifecycle.EXCLUSIVE_CLAIM.value
    assert res["claimant"] == "0xIndependentDev333"


def test_successful_tool_compliance_and_settlement():
    engine = AgentToolingEngine()
    bounty = engine.seed_tooling_bounty(
        creator="0xCreatorWallet444",
        tool_name="safe_transaction_batcher_sdk",
        category=AgentToolCategory.SDK_ADAPTER,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xFundTx4")
    engine.claim_bounty(bounty.bounty_id, "0xWinningSolver555", 0.10)

    schema = ToolInterfaceSchema(
        tool_name="batch_safe_execute",
        description="Encodes and submits atomic multisig batch transactions to Safe v1.4 contracts.",
        input_schema={"type": "object", "properties": {"calls": {"type": "array"}}},
        output_schema={"type": "object", "properties": {"safe_tx_hash": {"type": "string"}}},
    )

    def mock_functional_pass() -> bool:
        return True

    payload = AgentToolingSubmissionPayload(
        tool_schema=schema,
        category=AgentToolCategory.SDK_ADAPTER,
        code_hash="0x1234567890abcdef1234567890abcdef12345678",
        functional_test_thunk=mock_functional_pass,
        solver_wallet="0xWinningSolver555",
        signature="0xsig555",
    )

    settle_res = engine.submit_and_settle(bounty.bounty_id, payload)
    assert settle_res["status"] == BountyLifecycle.SETTLED.value
    assert settle_res["settled"] is True
    assert settle_res["solver_payout_usdc"] == 1.00
    assert settle_res["verifier_payout_usdc"] == 0.10
    assert bounty.settlement_tx_hash is not None


def test_invalid_tool_schema_or_failed_tests_rejection():
    engine = AgentToolingEngine()
    bounty = engine.seed_tooling_bounty(
        creator="0xCreatorWallet666",
        tool_name="faulty_automation_worker",
        category=AgentToolCategory.AUTOMATION_WORKER,
    )
    engine.deposit_funding(bounty.bounty_id, 1.00, "0xFundTx6")
    engine.claim_bounty(bounty.bounty_id, "0xSolver666", 0.10)

    # Defective schema (missing type)
    bad_schema = ToolInterfaceSchema(
        tool_name="bad_tool",
        description="Bad tool with invalid schema",
        input_schema={},
        output_schema={},
    )

    def failing_thunk() -> bool:
        return False

    payload = AgentToolingSubmissionPayload(
        tool_schema=bad_schema,
        category=AgentToolCategory.AUTOMATION_WORKER,
        code_hash="0xabcdefabcdefabcdefabcdefabcdefabcdefabcd",
        functional_test_thunk=failing_thunk,
        solver_wallet="0xSolver666",
        signature="0xsig666",
    )

    res = engine.submit_and_settle(bounty.bounty_id, payload)
    assert res["status"] == BountyLifecycle.REJECTED.value
    assert res["settled"] is False
    assert "failed schema validation criteria" in res["error"]
