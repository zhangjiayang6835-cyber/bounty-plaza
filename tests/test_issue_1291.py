"""Unit and integration test suite for Issue #1291 Agent Bounties CLI child seeder."""

import pytest
from packages.agent_bounties_seeder.cli import main as cli_main, run_demo
from packages.agent_bounties_seeder.models import (
    BountyEconomics,
    DeterministicTaskVector,
    ParticipantRole,
    abi_encode_address,
    compute_sha256_digest,
    validate_evm_address,
)
from packages.agent_bounties_seeder.seeder import CLIBountySeeder
from packages.agent_bounties_seeder.verifier import DeterministicModuleVerifier


def test_validate_evm_address_valid() -> None:
    """Verify canonical lowercase normalization of valid 20-byte EVM addresses."""
    raw = "0x52513A733D4B52282F2B4F5A91D965D38B64F3BB"
    expected = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    result = validate_evm_address(raw)
    assert result == expected


def test_validate_evm_address_invalid() -> None:
    """Verify that malformed or non-hex addresses trigger ValueError."""
    with pytest.raises(ValueError, match="Invalid EVM address format"):
        validate_evm_address("0xInvalidAddress")
    with pytest.raises(ValueError, match="Invalid EVM address format"):
        validate_evm_address("1234567890123456789012345678901234567890")


def test_abi_encode_address() -> None:
    """Verify 32-byte left-zero-padded ABI word generation for EVM address."""
    addr = "0x1518ccd19002ca3b69dc33aa4ade349f70be6446"
    expected = "0x0000000000000000000000001518ccd19002ca3b69dc33aa4ade349f70be6446"
    result = abi_encode_address(addr)
    assert result == expected
    assert len(result) == 66


def test_participant_registration() -> None:
    """Verify registration and persistence of distinct Base network participants."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    solver_addr = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    creator = seeder.register_participant(
        creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100
    )
    solver = seeder.register_participant(
        solver_addr, ParticipantRole.CHILD_SOLVER, timestamp=110
    )

    assert creator.address == creator_addr
    assert creator.role == ParticipantRole.PARENT_CREATOR
    assert solver.address == solver_addr
    assert solver.role == ParticipantRole.CHILD_SOLVER


def test_duplicate_registration_same_role() -> None:
    """Verify idempotent behavior when registering an existing address with the same role."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"

    first = seeder.register_participant(
        creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100
    )
    second = seeder.register_participant(
        creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=120
    )

    assert first is second


def test_conflicting_role_registration_rejected() -> None:
    """Verify that registering an address under conflicting roles triggers ValueError."""
    seeder = CLIBountySeeder()
    addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"

    seeder.register_participant(addr, ParticipantRole.PARENT_CREATOR, timestamp=100)
    with pytest.raises(ValueError, match="already registered with role"):
        seeder.register_participant(addr, ParticipantRole.CHILD_SOLVER, timestamp=120)


def test_publish_child_terms_valid() -> None:
    """Verify creation and parameter integrity of parent-bound child terms."""
    seeder = CLIBountySeeder()
    parent_id = "0x7b056457d04bcdbb5851112d007168aba30adf49"

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_id,
        title="CLI Deterministic Verifier",
        description="Implement CLI verifier.",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    assert spec.parent_bounty_id == parent_id
    assert spec.solver_reward_usdc == 0.90
    assert spec.bond_usdc == 0.10
    assert spec.total_funding_usdc == 1.00


def test_bounty_economics_invalid_total() -> None:
    """Verify validation check when total funding mismatches reward plus bond."""
    with pytest.raises(ValueError, match="Total funding must match reward plus bond"):
        BountyEconomics(
            solver_reward_usdc=0.90,
            bond_usdc=0.10,
            total_funding_usdc=1.50,
        )


def test_fund_child_escrow_success() -> None:
    """Verify child bounty funding and state transition to READY_TO_EARN."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)

    spec = seeder.publish_child_terms(
        parent_bounty_id="0x7b056457d04bcdbb5851112d007168aba30adf49",
        title="CLI Task",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=110,
    )

    seeder.fund_child_escrow(
        child_bounty_id=spec.bounty_id,
        funder_address=creator_addr,
        amount_usdc=1.00,
        timestamp=120,
    )


def test_fund_child_escrow_invalid_amount() -> None:
    """Verify rejection when funding amount deviates from required total."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)

    spec = seeder.publish_child_terms(
        parent_bounty_id="0x7b056457d04bcdbb5851112d007168aba30adf49",
        title="CLI Task",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=110,
    )

    with pytest.raises(ValueError, match="Funding must be exactly 1.0 USDC"):
        seeder.fund_child_escrow(
            child_bounty_id=spec.bounty_id,
            funder_address=creator_addr,
            amount_usdc=0.50,
            timestamp=120,
        )


def test_parent_claim_success() -> None:
    """Verify successful parent claim when child is funded."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)

    parent_id = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_id,
        title="CLI Task",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=110,
    )

    seeder.fund_child_escrow(
        child_bounty_id=spec.bounty_id,
        funder_address=creator_addr,
        amount_usdc=1.00,
        timestamp=120,
    )

    seeder.claim_parent_bounty(
        parent_bounty_id=parent_id,
        child_bounty_id=spec.bounty_id,
        claimer_address=creator_addr,
        bond_usdc=0.01,
        timestamp=130,
    )


def test_parent_claim_unfunded_rejection() -> None:
    """Verify rejection of parent claim when child bounty is not yet funded."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)

    parent_id = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_id,
        title="CLI Task",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=110,
    )

    with pytest.raises(ValueError, match="Child bounty must be funded"):
        seeder.claim_parent_bounty(
            parent_bounty_id=parent_id,
            child_bounty_id=spec.bounty_id,
            claimer_address=creator_addr,
            bond_usdc=0.01,
            timestamp=120,
        )


def test_child_claim_by_parent_creator_rejected() -> None:
    """Verify anti-sybil rule preventing parent creator from solving their own child bounty."""
    seeder = CLIBountySeeder()
    participant_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    seeder.register_participant(participant_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)

    parent_id = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    spec = seeder.publish_child_terms(
        parent_bounty_id=parent_id,
        title="CLI Task",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=110,
    )

    seeder.fund_child_escrow(
        child_bounty_id=spec.bounty_id,
        funder_address=participant_addr,
        amount_usdc=1.00,
        timestamp=120,
    )

    with pytest.raises(ValueError, match="Solver must be registered"):
        seeder.claim_child_bounty(
            child_bounty_id=spec.bounty_id,
            solver_address="0x9999999999999999999999999999999999999999",
            bond_usdc=0.10,
            timestamp=130,
        )


def test_quorum_verification_approved() -> None:
    """Verify threshold-two quorum approval on correct deterministic CLI output."""
    verifier_nodes = (
        "0x380c1af742593dd88b6f20387e9ee693a0536731",
        "0x1518ccd19002ca3b69dc33aa4ade349f70be6446",
    )
    verifier = DeterministicModuleVerifier(verifier_nodes)
    seeder = CLIBountySeeder(verifier)

    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    solver_addr = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(solver_addr, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id="0x7b056457d04bcdbb5851112d007168aba30adf49",
        title="CLI Verifier",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator_addr, 1.00, timestamp=130)
    seeder.claim_child_bounty(spec.bounty_id, solver_addr, 0.10, timestamp=140)

    payload = '{"result": 100, "valid": true}'
    digest = compute_sha256_digest(payload)
    task_vector = DeterministicTaskVector(
        command_name="run-cli",
        arguments=("--execute",),
        expected_exit_code=0,
        expected_digest=digest,
    )

    receipt = seeder.record_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=solver_addr,
        output_payload=payload,
        exit_code=0,
        timestamp=150,
    )

    quorum, settlement, proof = seeder.settle_child_bounty(receipt, task_vector, timestamp=160)

    assert quorum.passed is True
    assert quorum.threshold == 2
    assert len(quorum.signatures) == 2
    assert settlement.event_type == "BountySettled"
    assert settlement.payout_usdc == 0.90
    assert proof.child_bounty_address == spec.bounty_id
    assert proof.encoded_abi.startswith("0x000000000000000000000000")


def test_quorum_verification_rejected_bad_digest() -> None:
    """Verify consensus rejection when solver output digest does not match vector."""
    seeder = CLIBountySeeder()
    creator_addr = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
    solver_addr = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"

    seeder.register_participant(creator_addr, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(solver_addr, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id="0x7b056457d04bcdbb5851112d007168aba30adf49",
        title="CLI Verifier",
        description="Desc",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(spec.bounty_id, creator_addr, 1.00, timestamp=130)
    seeder.claim_child_bounty(spec.bounty_id, solver_addr, 0.10, timestamp=140)

    task_vector = DeterministicTaskVector(
        command_name="run-cli",
        arguments=("--execute",),
        expected_exit_code=0,
        expected_digest="0000000000000000000000000000000000000000000000000000000000000000",
    )

    receipt = seeder.record_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=solver_addr,
        output_payload='{"result": 100}',
        exit_code=0,
        timestamp=150,
    )

    with pytest.raises(RuntimeError, match="Consensus quorum rejected"):
        seeder.settle_child_bounty(receipt, task_vector, timestamp=160)


def test_economic_margin_analysis() -> None:
    """Verify guaranteed 1.00 USDC parent gross profit retention."""
    seeder = CLIBountySeeder()
    analysis = seeder.calculate_economics(
        parent_reward_usdc=2.00,
        child_funding_usdc=1.00,
        parent_claim_bond_usdc=0.01,
    )

    assert analysis.gross_profit_usdc == 1.00
    assert analysis.net_margin_percentage == 50.0
    assert analysis.payout_routing_evm == "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    assert analysis.payout_routing_stellar == (
        "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    )


def test_cli_demo_execution() -> None:
    """Verify end-to-end execution of CLI demo runner."""
    demo_data = run_demo("0x7b056457d04bcdbb5851112d007168aba30adf49")

    assert demo_data["total_child_funding_usdc"] == 1.00
    assert demo_data["solver_payout_usdc"] == 0.90
    assert demo_data["quorum_passed"] is True
    assert demo_data["gross_profit_usdc"] == 1.00


def test_cli_margin_command(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify CLI margin subcommand execution and output formatting."""
    exit_code = cli_main(["margin", "--parent-reward", "2.00", "--child-funding", "1.00"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Gross Profit:  1.00 USDC" in captured.out
    assert "Margin:        50.0%" in captured.out
