"""Comprehensive test suite for Issue #1219 Wallet UX child bounty seeder."""

import json
import pytest
from packages.wallet_ux_seeder import (
    BlockAnchor,
    BountyEconomics,
    BountyStatus,
    CanonicalSettlementReceipt,
    ChildBountySpec,
    DEFAULT_CHILD_BOUNTY_ID,
    DEFAULT_EVM_PAYOUT,
    DEFAULT_PARENT_BOUNTY_ID,
    DEFAULT_STELLAR_PAYOUT,
    DEFAULT_VERIFIER_NODES,
    DeterministicModuleVerifier,
    EconomicMarginAnalysis,
    ExecutionReceipt,
    ParentProofPayload,
    Participant,
    ParticipantRole,
    QuorumVerification,
    WalletUXActionType,
    WalletUXBountySeeder,
    WalletUXComponentSpec,
    WalletUXTaskVector,
    abi_encode_address,
    cli_main,
    compute_sha256_digest,
    run_demo,
    validate_evm_address,
)
from packages.wallet_ux_seeder.seeder import main as seeder_main


def test_validate_evm_address_valid() -> None:
    """Verify standard EVM address validation and lowercase conversion."""
    raw = "0x7B056457D04BCDBB5851112D007168ABA30ADF49"
    expected = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    assert validate_evm_address(raw) == expected


def test_validate_evm_address_invalid() -> None:
    """Verify invalid EVM address strings raise ValueError."""
    with pytest.raises(ValueError):
        validate_evm_address("not-an-address")
    with pytest.raises(ValueError):
        validate_evm_address("0x1234")
    with pytest.raises(ValueError):
        validate_evm_address(12345)  # type: ignore[arg-type]


def test_abi_encode_address_layout() -> None:
    """Verify left-padded 32-byte Solidity ABI encoding of 20-byte address."""
    addr = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"
    encoded = abi_encode_address(addr)
    assert len(encoded) == 66
    assert encoded.startswith("0x")
    assert encoded[2:26] == "0" * 24
    assert encoded[26:] == addr[2:]


def test_compute_sha256_digest() -> None:
    """Verify cryptographic SHA-256 digest computation."""
    payload = "wallet-ux-payment-flow"
    digest = compute_sha256_digest(payload)
    assert len(digest) == 64
    assert digest == "602bfc00dce43743280f161a7c7e029404f83e485ea7889f3e09d3d2369c034b"


def test_participant_initialization_constraints() -> None:
    """Verify Participant model constructor validation."""
    valid_addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    p = Participant(valid_addr, ParticipantRole.PARENT_CREATOR, 100)
    assert p.address == valid_addr
    assert p.role == ParticipantRole.PARENT_CREATOR
    assert p.registration_timestamp == 100

    with pytest.raises(ValueError):
        Participant(valid_addr, ParticipantRole.PARENT_CREATOR, 0)


def test_bounty_economics_constraints() -> None:
    """Verify strict mathematical sum constraints on bounty funding."""
    econ = BountyEconomics(solver_reward_usdc=0.90, bond_usdc=0.10, total_funding_usdc=1.00)
    assert econ.solver_reward_usdc == 0.90
    assert econ.bond_usdc == 0.10
    assert econ.total_funding_usdc == 1.00

    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.0, bond_usdc=0.10, total_funding_usdc=0.10)

    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.90, bond_usdc=-0.10, total_funding_usdc=0.80)

    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.90, bond_usdc=0.10, total_funding_usdc=1.05)


def test_seeder_participant_registration_idempotence() -> None:
    """Verify participant registration idempotence and conflicting role rejection."""
    seeder = WalletUXBountySeeder()
    addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"

    p1 = seeder.register_participant(addr, ParticipantRole.PARENT_CREATOR, 100)
    p2 = seeder.register_participant(addr, ParticipantRole.PARENT_CREATOR, 100)
    assert p1 == p2

    with pytest.raises(ValueError, match="already registered with role"):
        seeder.register_participant(addr, ParticipantRole.CHILD_SOLVER, 200)


def test_publish_child_terms() -> None:
    """Verify publication of child bounty terms with correct default parameters."""
    seeder = WalletUXBountySeeder()
    parent = DEFAULT_PARENT_BOUNTY_ID

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent,
        title="Wallet UX Payment Flow",
        description="Render and verify wallet transaction confirmation modal",
        reward_tuple=(0.90, 0.10),
        timestamp=100,
    )

    assert spec.bounty_id.startswith("0x") and len(spec.bounty_id) == 42
    assert spec.parent_bounty_id == parent.lower()
    assert spec.total_funding_usdc == 1.00
    assert spec.solver_reward_usdc == 0.90
    assert spec.bond_usdc == 0.10
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.UNAVAILABLE


def test_fund_child_escrow_validation() -> None:
    """Verify escrow funding rules and role authorization."""
    seeder = WalletUXBountySeeder()
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(DEFAULT_PARENT_BOUNTY_ID, "Title", "Desc", timestamp=100)

    with pytest.raises(ValueError, match="Funder must have PARENT_CREATOR role"):
        seeder.fund_child_escrow(spec.bounty_id, solver, 1.00, 110)

    with pytest.raises(ValueError, match="Funding must be exactly 1.0 USDC"):
        seeder.fund_child_escrow(spec.bounty_id, creator, 0.99, 110)

    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.READY_TO_EARN
    assert seeder.registry.is_bounty_funded(spec.bounty_id) is True


def test_claim_parent_bounty_preconditions() -> None:
    """Verify parent claim rejects when child is unfunded or conditions unmet."""
    seeder = WalletUXBountySeeder()
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)

    spec = seeder.publish_child_terms(DEFAULT_PARENT_BOUNTY_ID, "Title", "Desc", timestamp=100)

    with pytest.raises(ValueError, match="Child bounty must be funded"):
        seeder.claim_parent_bounty(DEFAULT_PARENT_BOUNTY_ID, spec.bounty_id, creator, 0.01, 110)

    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)

    with pytest.raises(ValueError, match="strictly after child funding"):
        seeder.claim_parent_bounty(DEFAULT_PARENT_BOUNTY_ID, spec.bounty_id, creator, 0.01, 110)

    with pytest.raises(ValueError, match="at least 0.01 USDC bond"):
        seeder.claim_parent_bounty(DEFAULT_PARENT_BOUNTY_ID, spec.bounty_id, creator, 0.005, 120)

    seeder.claim_parent_bounty(DEFAULT_PARENT_BOUNTY_ID, spec.bounty_id, creator, 0.01, 120)


def test_anti_sybil_role_segregation() -> None:
    """Verify parent creator cannot claim child bounty as solver."""
    seeder = WalletUXBountySeeder()
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(DEFAULT_PARENT_BOUNTY_ID, "Title", "Desc", timestamp=100)
    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)

    with pytest.raises(ValueError, match="Solver must possess CHILD_SOLVER role"):
        seeder.claim_child_bounty(spec.bounty_id, creator, 0.10, 120)

    seeder.claim_child_bounty(spec.bounty_id, solver, 0.10, 120)
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.EXCLUSIVE_CLAIM


def test_deterministic_verifier_consensus_and_rejection() -> None:
    """Verify 2-node consensus quorum passes valid runs and rejects invalid ones."""
    verifier = DeterministicModuleVerifier()
    assert verifier.threshold == 2
    assert verifier.is_authorized_node(DEFAULT_VERIFIER_NODES[0]) is True
    assert verifier.is_authorized_node("0x0000000000000000000000000000000000000001") is False

    comp = WalletUXComponentSpec(
        component_id="wallet-ux-payment-flow",
        component_name="WalletPaymentCard",
        target_flow=WalletUXActionType.CONFIRM_TRANSACTION,
        required_props=("recipient", "amount", "feeQuote"),
    )
    valid_payload = '{"render": "ok"}'
    valid_hash = compute_sha256_digest(valid_payload)

    task_vector = WalletUXTaskVector(
        component=comp,
        test_suite="headless-dom-regression",
        arguments=("--render",),
        expected_exit_code=0,
        expected_digest=valid_hash,
    )

    valid_receipt = ExecutionReceipt(
        receipt_id="rec-001",
        bounty_id="0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b",
        solver_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        exit_code=0,
        output_payload=valid_payload,
        output_digest=valid_hash,
        execution_timestamp=130,
    )

    q_pass = verifier.verify_execution(valid_receipt, task_vector, 140)
    assert q_pass.passed is True
    assert len(q_pass.signatures) == 2

    invalid_receipt = ExecutionReceipt(
        receipt_id="rec-002",
        bounty_id="0xe8c1d3f046f3e4690bef59ba4abd5d02d2a6984b",
        solver_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        exit_code=1,
        output_payload=valid_payload,
        output_digest=valid_hash,
        execution_timestamp=130,
    )
    q_fail = verifier.verify_execution(invalid_receipt, task_vector, 140)
    assert q_fail.passed is False
    assert len(q_fail.signatures) == 0


def test_full_settlement_and_proof_generation() -> None:
    """Verify canonical settlement receipt and Solidity ABI proof generation."""
    seeder = WalletUXBountySeeder()
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(DEFAULT_PARENT_BOUNTY_ID, "Title", "Desc", timestamp=100)
    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)
    seeder.claim_child_bounty(spec.bounty_id, solver, 0.10, 120)

    payload = '{"component": "WalletPaymentCard", "status": "APPROVED"}'
    task_vector = WalletUXTaskVector(
        component=WalletUXComponentSpec(
            component_id="wallet-payment-card",
            component_name="WalletPaymentCard",
            target_flow=WalletUXActionType.CONFIRM_TRANSACTION,
            required_props=("recipient",),
        ),
        test_suite="headless-dom-regression",
        arguments=("--render",),
        expected_exit_code=0,
        expected_digest=compute_sha256_digest(payload),
    )

    receipt = seeder.record_execution(spec.bounty_id, solver, payload, 0, 130)
    quorum, settlement, proof = seeder.settle_child_bounty(receipt, task_vector, 140)

    assert quorum.passed is True
    assert settlement.event_type == "BountySettled"
    assert settlement.payout_usdc == 0.90
    assert settlement.bounty_id == spec.bounty_id
    assert settlement.solver_address == solver.lower()
    assert settlement.anchor.block_number == 21890123
    assert settlement.anchor.transaction_hash.startswith("0x")

    assert proof.child_bounty_address == spec.bounty_id
    assert proof.encoded_abi == abi_encode_address(spec.bounty_id)
    assert len(proof.encoded_abi) == 66
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.SETTLED


def test_economic_margin_analysis() -> None:
    """Verify parent-child economic margins and payout routing."""
    seeder = WalletUXBountySeeder()
    analysis = seeder.calculate_economics(
        parent_reward_usdc=2.00,
        child_funding_usdc=1.00,
        parent_claim_bond_usdc=0.01,
    )

    assert analysis.parent_reward_usdc == 2.00
    assert analysis.child_funding_usdc == 1.00
    assert analysis.gross_profit_usdc == 1.00
    assert analysis.net_margin_percentage == 50.0
    assert analysis.payout_routing_evm == DEFAULT_EVM_PAYOUT
    assert analysis.payout_routing_stellar == DEFAULT_STELLAR_PAYOUT


def test_run_demo_and_cli() -> None:
    """Verify demo execution and CLI commands exit cleanly."""
    demo = run_demo()
    assert demo["quorum_passed"] is True
    assert demo["solver_payout_usdc"] == 0.90
    assert demo["gross_profit_usdc"] == 1.00
    assert demo["net_margin_percentage"] == 50.0
    assert demo["payout_routing_evm"] == DEFAULT_EVM_PAYOUT

    assert cli_main(["demo"]) == 0
    assert cli_main(["margin"]) == 0
    assert cli_main(["seed"]) == 0
    assert seeder_main() == 0
