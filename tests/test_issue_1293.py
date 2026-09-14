"""Comprehensive test suite for Issue 1293 API child bounty seeder."""

import json
import pytest
from packages.agent_bounties_api_seeder.cli import main as cli_main, run_demo
from packages.agent_bounties_api_seeder.models import (
    ApiEndpointSpec,
    ApiExecutionReceipt,
    ApiHttpMethod,
    ApiResponseTelemetry,
    BountyEconomics,
    BountyStatus,
    DeterministicApiTaskVector,
    ParticipantRole,
    abi_encode_address,
    canonicalize_json_payload,
    compute_sha256_digest,
    validate_evm_address,
)
from packages.agent_bounties_api_seeder.seeder import ApiBountySeeder
from packages.agent_bounties_api_seeder.verifier import DeterministicApiModuleVerifier
from scripts.verify_issue_1293 import run_verification

PARENT_ADDR = "0xd15306a8cc4274ec46d913817ca4490c4fc41303"
CREATOR_ADDR = "0x52513a733d4b52282f2b4f5a91d965d38b64f3bb"
SOLVER_ADDR = "0x62f7793b28dfa508067b186144a23c49dd0bf02f"
VERIFIER_A = "0x380c1af742593dd88b6f20387e9ee693a0536731"
VERIFIER_B = "0x1518ccd19002ca3b69dc33aa4ade349f70be6446"


def test_validate_evm_address_valid() -> None:
    """Validate properly formatted EVM addresses convert to lowercase."""
    addr = "0x52513A733D4B52282F2B4F5A91D965D38B64F3BB"
    res = validate_evm_address(addr)
    assert res == addr.lower()
    assert len(res) == 42


def test_validate_evm_address_invalid() -> None:
    """Ensure invalid address formats raise ValueError."""
    with pytest.raises(ValueError):
        validate_evm_address("not_an_address")
    with pytest.raises(ValueError):
        validate_evm_address("0x123")
    with pytest.raises(ValueError):
        validate_evm_address(12345)  # type: ignore


def test_abi_encode_address() -> None:
    """Verify EVM address ABI encodes as 32-byte left-zero-padded word."""
    encoded = abi_encode_address(CREATOR_ADDR)
    assert encoded.startswith("0x")
    assert len(encoded) == 66
    assert encoded[2:26] == "0" * 24
    assert encoded[26:].lower() == CREATOR_ADDR[2:].lower()


def test_compute_sha256_digest() -> None:
    """Verify SHA-256 digest computation matches cryptographic truth."""
    known_payload = "deterministic_payload"
    expected = "c5d3305045fa2dfb1526a2c35ea88a92676c48cd024a0a307cfaed0386982af6"
    assert compute_sha256_digest(known_payload) == expected


def test_canonicalize_json_payload() -> None:
    """Verify JSON canonicalization eliminates extraneous spaces and sorts keys."""
    data = {"b": 2, "a": 1}
    serialized = canonicalize_json_payload(data)
    assert serialized == '{"a":1,"b":2}'


def test_bounty_economics_validation() -> None:
    """Enforce strict child bounty funding constraints."""
    econ = BountyEconomics(
        solver_reward_usdc=0.90,
        bond_usdc=0.10,
        total_funding_usdc=1.00,
    )
    assert econ.solver_reward_usdc == 0.90
    assert econ.bond_usdc == 0.10
    assert econ.total_funding_usdc == 1.00

    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.0, bond_usdc=0.10, total_funding_usdc=0.10)
    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.90, bond_usdc=-0.10, total_funding_usdc=0.80)
    with pytest.raises(ValueError):
        BountyEconomics(solver_reward_usdc=0.90, bond_usdc=0.10, total_funding_usdc=1.50)


def test_participant_registration() -> None:
    """Test participant registration on Base network."""
    seeder = ApiBountySeeder()
    p1 = seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    assert p1.address == CREATOR_ADDR.lower()
    assert p1.role == ParticipantRole.PARENT_CREATOR
    assert p1.registration_timestamp == 100

    p2 = seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, timestamp=110)
    assert p2.address == SOLVER_ADDR.lower()
    assert p2.role == ParticipantRole.CHILD_SOLVER


def test_duplicate_registration_same_role() -> None:
    """Duplicate registration with identical role returns existing participant."""
    seeder = ApiBountySeeder()
    p1 = seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    p2 = seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=105)
    assert p1 == p2


def test_conflicting_role_registration() -> None:
    """Conflicting role registration for same address raises ValueError."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    with pytest.raises(ValueError):
        seeder.register_participant(CREATOR_ADDR, ParticipantRole.CHILD_SOLVER, timestamp=105)


def test_publish_child_terms() -> None:
    """Publishing terms sets initial UNAVAILABLE state and creates valid spec."""
    seeder = ApiBountySeeder()
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API: Deterministic Verification Endpoint",
        description="Run deterministic test vector over JSON API endpoint",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )
    assert spec.parent_bounty_id == PARENT_ADDR
    assert spec.total_funding_usdc == 1.00
    assert spec.solver_reward_usdc == 0.90
    assert spec.bond_usdc == 0.10
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.UNAVAILABLE


def test_fund_child_escrow_success() -> None:
    """Funding escrow transitions state to READY_TO_EARN."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )
    seeder.fund_child_escrow(
        child_bounty_id=spec.bounty_id,
        funder_address=CREATOR_ADDR,
        amount_usdc=1.00,
        timestamp=130,
    )
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.READY_TO_EARN


def test_fund_child_escrow_failures() -> None:
    """Verify funding error handling for unregistered funder and invalid inputs."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, SOLVER_ADDR, 1.00, timestamp=130)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 0.50, timestamp=130)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=110)


def test_parent_claim_success() -> None:
    """Parent claim succeeds when child is funded and claimer matches funder."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=130)

    seeder.claim_parent_bounty(
        parent_bounty_id=PARENT_ADDR,
        child_bounty_id=spec.bounty_id,
        claimer_address=CREATOR_ADDR,
        bond_usdc=0.01,
        timestamp=140,
    )


def test_parent_claim_failures() -> None:
    """Verify parent claim rejects invalid state, early timestamp, and bond issues."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, timestamp=105)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, timestamp=125)

    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=130)

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, timestamp=130)

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.005, timestamp=140)

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, SOLVER_ADDR, 0.01, timestamp=140)


def test_child_claim_anti_self_dealing() -> None:
    """Ensure parent creator cannot claim child bounty as solver."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=130)

    with pytest.raises(ValueError):
        seeder.claim_child_bounty(spec.bounty_id, CREATOR_ADDR, 0.10, timestamp=140)


def test_child_claim_success() -> None:
    """Independent solver locks exclusive claim on child bounty."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, timestamp=110)
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API Task",
        description="Endpoint test",
        timestamp=120,
    )
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=130)

    seeder.claim_child_bounty(
        child_bounty_id=spec.bounty_id,
        solver_address=SOLVER_ADDR,
        bond_usdc=0.10,
        timestamp=140,
    )
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.EXCLUSIVE_CLAIM


def test_api_task_vector_validation() -> None:
    """Validate task vector constraint checking."""
    endpoint_spec = ApiEndpointSpec(
        route="/v1/api/endpoint",
        method=ApiHttpMethod.POST,
        request_body="{}",
    )
    task = DeterministicApiTaskVector(
        endpoint=endpoint_spec,
        expected_status_code=200,
        expected_schema=("ok",),
        expected_response_digest="abc123digest",
        max_latency_ms=100.0,
    )
    assert task.http_method == ApiHttpMethod.POST
    assert task.expected_status_code == 200

    with pytest.raises(ValueError):
        invalid_endpoint = ApiEndpointSpec(
            route="invalid_route",
            method=ApiHttpMethod.GET,
            request_body="",
        )
        DeterministicApiTaskVector(
            endpoint=invalid_endpoint,
            expected_status_code=200,
            expected_schema=(),
            expected_response_digest="abc",
            max_latency_ms=100.0,
        )


def test_verifier_quorum_consensus_success() -> None:
    """Quorum verifier passes when digest, status code, latency, and schema conform."""
    verifier = DeterministicApiModuleVerifier((VERIFIER_A, VERIFIER_B))
    payload = json.dumps({"status": "active", "code": 0})
    digest = compute_sha256_digest(payload)

    telemetry = ApiResponseTelemetry(
        status_code=200,
        response_body=payload,
        response_digest=digest,
        latency_ms=30.0,
    )
    receipt = ApiExecutionReceipt(
        receipt_id="rec001",
        bounty_id=PARENT_ADDR,
        solver_address=SOLVER_ADDR,
        telemetry=telemetry,
        execution_timestamp=150,
    )
    endpoint = ApiEndpointSpec(
        route="/v1/status",
        method=ApiHttpMethod.GET,
        request_body="",
    )
    vector = DeterministicApiTaskVector(
        endpoint=endpoint,
        expected_status_code=200,
        expected_schema=("status", "code"),
        expected_response_digest=digest,
        max_latency_ms=100.0,
    )

    verification = verifier.verify_execution(receipt, vector, timestamp=160)
    assert verification.passed is True
    assert len(verification.signatures) == 2


def test_verifier_quorum_failures() -> None:
    """Quorum verifier fails when criteria are violated."""
    verifier = DeterministicApiModuleVerifier((VERIFIER_A, VERIFIER_B))
    payload = json.dumps({"status": "active"})
    digest = compute_sha256_digest(payload)

    telemetry = ApiResponseTelemetry(
        status_code=500,
        response_body=payload,
        response_digest=digest,
        latency_ms=30.0,
    )
    receipt = ApiExecutionReceipt(
        receipt_id="rec001",
        bounty_id=PARENT_ADDR,
        solver_address=SOLVER_ADDR,
        telemetry=telemetry,
        execution_timestamp=150,
    )
    endpoint = ApiEndpointSpec(
        route="/v1/status",
        method=ApiHttpMethod.GET,
        request_body="",
    )
    vector = DeterministicApiTaskVector(
        endpoint=endpoint,
        expected_status_code=200,
        expected_schema=("status",),
        expected_response_digest=digest,
        max_latency_ms=100.0,
    )

    verification = verifier.verify_execution(receipt, vector, timestamp=160)
    assert verification.passed is False


def test_full_lifecycle_settlement() -> None:
    """Execute complete API child bounty lifecycle from registration to settlement."""
    seeder = ApiBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, timestamp=100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, timestamp=110)

    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="API: Verification Service",
        description="Verify service output",
        reward_tuple=(0.90, 0.10),
        timestamp=120,
    )

    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, timestamp=130)
    seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, timestamp=140)
    seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.10, timestamp=150)

    payload_data = {"status": "success", "result": "ok"}
    payload_body = canonicalize_json_payload(payload_data)
    payload_digest = compute_sha256_digest(payload_body)

    endpoint = ApiEndpointSpec(
        route="/v1/execute",
        method=ApiHttpMethod.POST,
        request_body='{"test":true}',
    )
    task_vector = DeterministicApiTaskVector(
        endpoint=endpoint,
        expected_status_code=200,
        expected_schema=("status", "result"),
        expected_response_digest=payload_digest,
        max_latency_ms=200.0,
    )

    telemetry = ApiResponseTelemetry(
        status_code=200,
        response_body=payload_body,
        response_digest=payload_digest,
        latency_ms=25.0,
    )
    receipt = seeder.record_api_execution(
        child_bounty_id=spec.bounty_id,
        solver_address=SOLVER_ADDR,
        telemetry=telemetry,
        timestamp=160,
    )

    quorum, settlement, proof = seeder.settle_child_bounty(receipt, task_vector, timestamp=170)

    assert quorum.passed is True
    assert settlement.payout_usdc == 0.90
    assert settlement.solver_address == SOLVER_ADDR.lower()
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.SETTLED
    assert proof.encoded_abi.startswith("0x")
    assert len(proof.encoded_abi) == 66


def test_economic_margin_analysis() -> None:
    """Verify economic metrics reflect 50.0% gross margin on 2.00 USDC parent reward."""
    seeder = ApiBountySeeder()
    margin = seeder.calculate_economics(
        parent_reward_usdc=2.00,
        child_funding_usdc=1.00,
        parent_claim_bond_usdc=0.01,
    )
    assert margin.parent_reward_usdc == 2.00
    assert margin.child_funding_usdc == 1.00
    assert margin.gross_profit_usdc == 1.00
    assert margin.net_margin_percentage == 50.0
    assert margin.payout_routing_evm == "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    expected_stellar = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"
    assert margin.payout_routing_stellar == expected_stellar


def test_cli_execution() -> None:
    """Verify CLI subcommands return success codes."""
    assert cli_main(["margin", "--parent-reward", "2.00", "--child-funding", "1.00"]) == 0
    assert (
        cli_main(
            [
                "seed",
                "--parent",
                PARENT_ADDR,
                "--title",
                "API Task",
                "--description",
                "Desc",
            ]
        )
        == 0
    )
    assert cli_main(["demo", "--parent", PARENT_ADDR]) == 0


def test_verification_script() -> None:
    """Verify standalone verification script returns zero."""
    assert run_verification() == 0


def test_run_demo_output() -> None:
    """Verify run_demo output structure and fields."""
    result = run_demo(PARENT_ADDR)
    assert result["total_child_funding_usdc"] == 1.00
    assert result["solver_payout_usdc"] == 0.90
    assert result["gross_profit_usdc"] == 1.00
    assert result["quorum_passed"] is True
