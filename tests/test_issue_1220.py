"""Comprehensive test suite for Issue #1220 API child bounty seeder."""

import json
import pytest
from packages.api_child_bounty_seeder import (
    APIActionType,
    APIBountySeeder,
    APIEndpointSpec,
    APITaskVector,
    BlockAnchor,
    BountyEconomics,
    BountyStatus,
    CanonicalSettlementReceipt,
    ChildBountySpec,
    DEFAULT_CHILD_BOUNTY_ID,
    DEFAULT_EVM_PAYOUT,
    DEFAULT_PARENT_BOUNTY_ID,
    DEFAULT_PARENT_CONTRACT,
    DEFAULT_STELLAR_PAYOUT,
    DEFAULT_VERIFIER_NODES,
    DeterministicModuleVerifier,
    EconomicMarginAnalysis,
    ExecutionReceipt,
    ParentProofPayload,
    Participant,
    ParticipantRole,
    QuorumVerification,
    abi_encode_address,
    cli_main,
    compute_sha256_digest,
    run_demo,
    validate_evm_address,
)
from packages.api_child_bounty_seeder.seeder import main as seeder_main
from scripts.verify_issue_1220 import verify_issue_1220


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
        validate_evm_address("0xGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGGG")


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
    payload = "api-settlement-endpoint"
    digest = compute_sha256_digest(payload)
    assert len(digest) == 64
    assert digest == "91e7a158174af592ca11103e357e5810f9af747e6b18abf5c05f2e2f7cff83ca"


def test_participant_initialization_constraints() -> None:
    """Verify Participant model constructor validation."""
    valid_addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    p = Participant(valid_addr, ParticipantRole.PARENT_CREATOR, 100)
    assert p.address == valid_addr
    assert p.role == ParticipantRole.PARENT_CREATOR
    assert p.registration_timestamp == 100

    with pytest.raises(ValueError):
        Participant(valid_addr, ParticipantRole.PARENT_CREATOR, 0)


def test_api_endpoint_spec_constraints() -> None:
    """Verify APIEndpointSpec field constraints."""
    spec = APIEndpointSpec(
        endpoint_id="settlement-ep",
        route_path="/v1/settle",
        http_method="POST",
        action_type=APIActionType.SETTLE_PAYMENT,
        required_headers=("Content-Type",),
    )
    assert spec.endpoint_id == "settlement-ep"
    assert spec.route_path == "/v1/settle"

    with pytest.raises(ValueError, match="Endpoint ID cannot be empty"):
        APIEndpointSpec("", "/v1/settle", "POST", APIActionType.SETTLE_PAYMENT, ("Content-Type",))

    with pytest.raises(ValueError, match="Route path must start with forward slash"):
        APIEndpointSpec("id", "v1/settle", "POST", APIActionType.SETTLE_PAYMENT, ("Content-Type",))

    with pytest.raises(ValueError, match="HTTP method cannot be empty"):
        APIEndpointSpec("id", "/v1/settle", "", APIActionType.SETTLE_PAYMENT, ("Content-Type",))

    with pytest.raises(ValueError, match="Required headers cannot be empty"):
        APIEndpointSpec("id", "/v1/settle", "POST", APIActionType.SETTLE_PAYMENT, ())


def test_api_task_vector_constraints() -> None:
    """Verify APITaskVector initialization checks."""
    endpoint = APIEndpointSpec(
        endpoint_id="ep",
        route_path="/v1/test",
        http_method="GET",
        action_type=APIActionType.GET_HEALTH,
        required_headers=("Accept",),
    )
    vec = APITaskVector(
        endpoint=endpoint,
        test_runner="runner",
        arguments=("--run",),
        expected_status_code=200,
        expected_digest="abc",
    )
    assert vec.expected_status_code == 200

    with pytest.raises(ValueError, match="Test runner cannot be empty"):
        APITaskVector(endpoint, "", (), 200, "abc")

    with pytest.raises(ValueError, match="Expected digest must be provided"):
        APITaskVector(endpoint, "runner", (), 200, "")


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
    seeder = APIBountySeeder()
    addr = "0x7b056457d04bcdbb5851112d007168aba30adf49"

    p1 = seeder.register_participant(addr, ParticipantRole.PARENT_CREATOR, 100)
    p2 = seeder.register_participant(addr, ParticipantRole.PARENT_CREATOR, 100)
    assert p1 == p2

    with pytest.raises(ValueError, match="already registered with role"):
        seeder.register_participant(addr, ParticipantRole.CHILD_SOLVER, 200)


def test_publish_child_terms() -> None:
    """Verify publication of child bounty terms with correct default parameters."""
    seeder = APIBountySeeder()
    parent = DEFAULT_PARENT_BOUNTY_ID

    spec = seeder.publish_child_terms(
        parent_bounty_id=parent,
        title="API Settlement Component",
        description="Deterministic API verification",
    )
    assert spec.parent_bounty_id == parent
    assert spec.total_funding_usdc == 1.00
    assert spec.solver_reward_usdc == 0.90
    assert spec.bond_usdc == 0.10
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.UNAVAILABLE


def test_fund_child_escrow_lifecycle() -> None:
    """Verify state transition to READY_TO_EARN and rejection of invalid funding attempts."""
    seeder = APIBountySeeder()
    parent = DEFAULT_PARENT_BOUNTY_ID
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(parent, "Task", "Desc")

    with pytest.raises(ValueError, match="Funder role must be PARENT_CREATOR"):
        seeder.fund_child_escrow(spec.bounty_id, solver, 1.00, 110)

    with pytest.raises(ValueError, match="must equal child funding"):
        seeder.fund_child_escrow(spec.bounty_id, creator, 0.50, 110)

    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.READY_TO_EARN
    assert seeder.registry.is_bounty_funded(spec.bounty_id) is True


def test_parent_claim_prerequisites() -> None:
    """Verify parent claim requires funded child escrow and positive bond."""
    seeder = APIBountySeeder()
    parent = DEFAULT_PARENT_BOUNTY_ID
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    spec = seeder.publish_child_terms(parent, "Task", "Desc")

    with pytest.raises(ValueError, match="must be funded before parent claim"):
        seeder.claim_parent_bounty(parent, spec.bounty_id, creator, 0.01, 105)

    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)

    with pytest.raises(ValueError, match="must be strictly greater than child funding"):
        seeder.claim_parent_bounty(parent, spec.bounty_id, creator, 0.01, 109)

    with pytest.raises(ValueError, match="Parent claim bond must be at least 0.01 USDC"):
        seeder.claim_parent_bounty(parent, spec.bounty_id, creator, 0.005, 115)

    seeder.claim_parent_bounty(parent, spec.bounty_id, creator, 0.01, 115)


def test_child_claim_anti_self_dealing_and_bonds() -> None:
    """Verify child claim enforces distinct solver identity and minimum bond."""
    seeder = APIBountySeeder()
    parent = DEFAULT_PARENT_BOUNTY_ID
    creator = "0x7b056457d04bcdbb5851112d007168aba30adf49"
    solver = "0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5"

    seeder.register_participant(creator, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(solver, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(parent, "Task", "Desc")
    seeder.fund_child_escrow(spec.bounty_id, creator, 1.00, 110)

    with pytest.raises(ValueError, match="Solver role must be CHILD_SOLVER"):
        seeder.claim_child_bounty(spec.bounty_id, creator, 0.10, 120)

    with pytest.raises(ValueError, match="less than required"):
        seeder.claim_child_bounty(spec.bounty_id, solver, 0.05, 120)

    seeder.claim_child_bounty(spec.bounty_id, solver, 0.10, 120)
    assert seeder.registry.bounty_states[spec.bounty_id] == BountyStatus.EXCLUSIVE_CLAIM


def test_verifier_consensus_evaluation() -> None:
    """Verify 2-of-2 node quorum consensus validation and failure modes."""
    verifier = DeterministicModuleVerifier(DEFAULT_VERIFIER_NODES, threshold=2)
    assert verifier.is_authorized_node("0x380c1af742593dd88b6f20387e9ee693a0536731") is True
    assert verifier.is_authorized_node("0x0000000000000000000000000000000000000001") is False

    endpoint = APIEndpointSpec(
        endpoint_id="api-ep",
        route_path="/v1/settle",
        http_method="POST",
        action_type=APIActionType.SETTLE_PAYMENT,
        required_headers=("Content-Type",),
    )
    task_vec = APITaskVector(
        endpoint=endpoint,
        test_runner="runner",
        arguments=("--strict",),
        expected_status_code=200,
        expected_digest=compute_sha256_digest("valid-payload"),
    )

    valid_receipt = ExecutionReceipt(
        receipt_id="0x01",
        bounty_id="0xa8f37b9215091c6e61f25e98b04a80693a20147b",
        solver_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        status_code=200,
        output_payload="valid-payload",
        output_digest=compute_sha256_digest("valid-payload"),
        execution_timestamp=1000,
    )
    res_valid = verifier.verify_execution(valid_receipt, task_vec, 1010)
    assert res_valid.passed is True
    assert len(res_valid.signatures) == 2

    mismatch_status_receipt = ExecutionReceipt(
        receipt_id="0x02",
        bounty_id="0xa8f37b9215091c6e61f25e98b04a80693a20147b",
        solver_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        status_code=500,
        output_payload="valid-payload",
        output_digest=compute_sha256_digest("valid-payload"),
        execution_timestamp=1000,
    )
    res_status = verifier.verify_execution(mismatch_status_receipt, task_vec, 1010)
    assert res_status.passed is False
    assert len(res_status.signatures) == 0

    mismatch_digest_receipt = ExecutionReceipt(
        receipt_id="0x03",
        bounty_id="0xa8f37b9215091c6e61f25e98b04a80693a20147b",
        solver_address="0x95222290dd7278aa3ddd389cc1e1d165cc4bafe5",
        status_code=200,
        output_payload="tampered-payload",
        output_digest=compute_sha256_digest("tampered-payload"),
        execution_timestamp=1000,
    )
    res_digest = verifier.verify_execution(mismatch_digest_receipt, task_vec, 1010)
    assert res_digest.passed is False


def test_verifier_construction_errors() -> None:
    """Verify verifier initialization error checking for duplicate nodes or invalid thresholds."""
    with pytest.raises(ValueError, match="Verifier nodes must be distinct"):
        DeterministicModuleVerifier(
            ("0x380c1af742593dd88b6f20387e9ee693a0536731", "0x380c1af742593dd88b6f20387e9ee693a0536731"),
            threshold=1,
        )

    with pytest.raises(ValueError, match="Threshold must be positive and not exceed node count"):
        DeterministicModuleVerifier(DEFAULT_VERIFIER_NODES, threshold=3)

    with pytest.raises(ValueError, match="Threshold must be positive and not exceed node count"):
        DeterministicModuleVerifier(DEFAULT_VERIFIER_NODES, threshold=0)


def test_end_to_end_settlement_and_proof() -> None:
    """Verify complete lifecycle from initialization to settlement and ABI proof extraction."""
    demo = run_demo()
    assert demo["total_child_funding_usdc"] == 1.00
    assert demo["solver_payout_usdc"] == 0.90
    assert demo["quorum_passed"] is True
    assert demo["gross_profit_usdc"] == 1.00
    assert demo["net_margin_percentage"] == 50.0
    assert demo["payout_routing_evm"] == DEFAULT_EVM_PAYOUT
    assert demo["payout_routing_stellar"] == DEFAULT_STELLAR_PAYOUT


def test_cli_interface_all_commands(capsys: pytest.CaptureFixture[str]) -> None:
    """Verify CLI execution paths for seed, margin, and demo commands."""
    ret_demo = cli_main(["demo"])
    assert ret_demo == 0
    captured_demo = capsys.readouterr()
    assert "gross_profit_usdc" in captured_demo.out

    ret_margin = cli_main(["margin", "--parent-reward=2.0", "--child-funding=1.0"])
    assert ret_margin == 0
    captured_margin = capsys.readouterr()
    assert "Gross Profit:  1.00 USDC" in captured_margin.out

    ret_seed = cli_main(["seed", "--title=Test API Child Bounty"])
    assert ret_seed == 0
    captured_seed = capsys.readouterr()
    assert "Test API Child Bounty" in captured_seed.out


def test_seeder_main_execution() -> None:
    """Verify seeder.py main execution wrapper."""
    sys_argv_backup = list(__import__("sys").argv)
    __import__("sys").argv = ["seeder.py", "margin"]
    code = seeder_main()
    __import__("sys").argv = sys_argv_backup
    assert code == 0


def test_verify_issue_1220_script_direct() -> None:
    """Verify verify_issue_1220 execution script returns 0."""
    code = verify_issue_1220()
    assert code == 0
