"""Comprehensive unit test suite for Issue 1295 MCP child bounty seeder."""

import json
import pytest
from packages.agent_bounties_mcp_seeder.cli import main as cli_main, run_demo
from packages.agent_bounties_mcp_seeder.models import (
    BountyEconomics,
    BountyStatus,
    DeterministicMcpTaskVector,
    McpExecutionReceipt,
    McpResponseTelemetry,
    McpToolDefinition,
    ParticipantRole,
    abi_encode_address,
    canonicalize_json_payload,
    compute_sha256_digest,
    validate_evm_address,
)
from packages.agent_bounties_mcp_seeder.seeder import McpBountySeeder
from packages.agent_bounties_mcp_seeder.verifier import DeterministicMcpModuleVerifier
from scripts.verify_issue_1295 import run_verification

PARENT_ADDR = "0x43d42cb227d76588ab16693f14efd6cff851fa7a"
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
        validate_evm_address("invalid_address")
    with pytest.raises(ValueError):
        validate_evm_address("0x123")
    with pytest.raises(ValueError):
        validate_evm_address("0x" + "g" * 40)
    with pytest.raises(ValueError):
        validate_evm_address(None)


def test_abi_encode_address() -> None:
    """Verify EVM address ABI encodes as 32-byte left-zero-padded word."""
    encoded = abi_encode_address(CREATOR_ADDR)
    assert encoded.startswith("0x")
    assert len(encoded) == 66
    assert encoded[2:26] == "0" * 24
    assert encoded[26:].lower() == CREATOR_ADDR[2:].lower()


def test_compute_sha256_digest() -> None:
    """Verify SHA-256 digest computation matches cryptographic truth."""
    known_payload = "mcp_deterministic_payload"
    expected = "900f69208ffa367e2eff7b055d9c0fe524ec479353d598cfac480472b819322f"
    assert compute_sha256_digest(known_payload) == expected


def test_canonicalize_json_payload() -> None:
    """Verify JSON canonicalization eliminates extraneous spaces and sorts keys."""
    data = {"z": 100, "a": "first", "m": [1, 2]}
    serialized = canonicalize_json_payload(data)
    assert serialized == '{"a":"first","m":[1,2],"z":100}'


def test_mcp_tool_definition_valid() -> None:
    """Validate proper MCP tool definition structure."""
    tool_def = McpToolDefinition(
        name="test_tool",
        description="A test tool",
        input_schema={"type": "object", "properties": {"arg": {"type": "string"}}},
    )
    assert tool_def.name == "test_tool"
    assert tool_def.description == "A test tool"
    assert tool_def.input_schema["type"] == "object"


def test_mcp_tool_definition_invalid() -> None:
    """Ensure invalid MCP tool definition fields raise ValueError."""
    with pytest.raises(ValueError):
        McpToolDefinition(name="", description="valid", input_schema={"type": "object"})
    with pytest.raises(ValueError):
        McpToolDefinition(name="valid", description="", input_schema={"type": "object"})
    with pytest.raises(ValueError):
        McpToolDefinition(name="valid", description="valid", input_schema="not_a_dict")
    with pytest.raises(ValueError):
        McpToolDefinition(name="valid", description="valid", input_schema={"type": "string"})


def test_deterministic_mcp_task_vector_validation() -> None:
    """Verify constraints on deterministic MCP task vector construction."""
    tool_def = McpToolDefinition(
        name="tool_a",
        description="desc",
        input_schema={"type": "object"},
    )
    task_vec = DeterministicMcpTaskVector(
        tool_definition=tool_def,
        arguments={"k": "v"},
        expected_text="hello",
        expected_schema_keys=("text", "type"),
        expected_response_digest="abc",
        max_latency_ms=100.0,
    )
    assert task_vec.tool_name == "tool_a"

    with pytest.raises(ValueError):
        DeterministicMcpTaskVector(
            tool_definition=tool_def,
            arguments={},
            expected_text="hello",
            expected_schema_keys=(),
            expected_response_digest="",
            max_latency_ms=100.0,
        )
    with pytest.raises(ValueError):
        DeterministicMcpTaskVector(
            tool_definition=tool_def,
            arguments={},
            expected_text="",
            expected_schema_keys=(),
            expected_response_digest="abc",
            max_latency_ms=100.0,
        )
    with pytest.raises(ValueError):
        DeterministicMcpTaskVector(
            tool_definition=tool_def,
            arguments={},
            expected_text="hello",
            expected_schema_keys=(),
            expected_response_digest="abc",
            max_latency_ms=0.0,
        )


def test_bounty_economics_validation() -> None:
    """Enforce child bounty economics requirements."""
    econ = BountyEconomics(
        solver_reward_usdc=0.90,
        bond_usdc=0.10,
        total_funding_usdc=1.00,
    )
    assert econ.solver_reward_usdc == 0.90
    assert econ.bond_usdc == 0.10
    assert econ.total_funding_usdc == 1.00

    with pytest.raises(ValueError):
        BountyEconomics(0.0, 0.10, 0.10)
    with pytest.raises(ValueError):
        BountyEconomics(0.90, -0.05, 0.85)
    with pytest.raises(ValueError):
        BountyEconomics(0.90, 0.10, 1.05)


def test_participant_registration() -> None:
    """Verify participant registration and role assignment."""
    seeder = McpBountySeeder()
    p1 = seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    assert p1.address == CREATOR_ADDR.lower()
    assert p1.role == ParticipantRole.PARENT_CREATOR
    assert p1.active is True

    p1_dup = seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 105)
    assert p1_dup == p1

    with pytest.raises(ValueError):
        seeder.register_participant(CREATOR_ADDR, ParticipantRole.CHILD_SOLVER, 110)

    with pytest.raises(ValueError):
        seeder.register_participant("0x1234", ParticipantRole.CHILD_SOLVER, 100)

    with pytest.raises(ValueError):
        seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, -10)


def test_publish_child_terms() -> None:
    """Validate publishing terms initializes child in UNAVAILABLE state."""
    seeder = McpBountySeeder()
    spec = seeder.publish_child_terms(
        parent_bounty_id=PARENT_ADDR,
        title="MCP Tool Implementation",
        description="Implement tools/call RPC",
        reward_tuple=(0.90, 0.10),
        timestamp=100,
    )
    assert spec.parent_bounty_id == PARENT_ADDR.lower()
    assert spec.solver_reward_usdc == 0.90
    assert spec.bond_usdc == 0.10
    assert spec.total_funding_usdc == 1.00
    assert spec.verifier_type == "deterministic_module"
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.UNAVAILABLE


def test_fund_child_escrow_success_and_errors() -> None:
    """Verify escrow funding transitions state to READY_TO_EARN with validation."""
    seeder = McpBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(PARENT_ADDR, "Task", "Desc", (0.90, 0.10), 110)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 0.50, 120)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, SOLVER_ADDR, 1.00, 120)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 105)

    with pytest.raises(ValueError):
        seeder.fund_child_escrow("0x" + "1" * 40, CREATOR_ADDR, 1.00, 120)

    status = seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 120)
    assert status == BountyStatus.READY_TO_EARN
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.READY_TO_EARN


def test_claim_parent_bounty() -> None:
    """Verify parent bounty claiming constraints."""
    seeder = McpBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    spec = seeder.publish_child_terms(PARENT_ADDR, "Task", "Desc", (0.90, 0.10), 110)
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 120)

    assert seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, 130) is True

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.005, 130)

    with pytest.raises(ValueError):
        seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, 115)


def test_claim_child_bounty_and_anti_self_dealing() -> None:
    """Ensure child bounty claim enforces anti-self-dealing and role validation."""
    seeder = McpBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, 100)

    spec = seeder.publish_child_terms(PARENT_ADDR, "Task", "Desc", (0.90, 0.10), 110)
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 120)

    with pytest.raises(ValueError):
        seeder.claim_child_bounty(spec.bounty_id, CREATOR_ADDR, 0.10, 130)

    with pytest.raises(ValueError):
        seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.05, 130)

    with pytest.raises(ValueError):
        seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.10, 115)

    status = seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.10, 130)
    assert status == BountyStatus.EXCLUSIVE_CLAIM
    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.EXCLUSIVE_CLAIM


def test_record_mcp_execution_validation() -> None:
    """Verify execution recording requires exclusive claim and valid solver."""
    seeder = McpBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, 100)
    spec = seeder.publish_child_terms(PARENT_ADDR, "Task", "Desc", (0.90, 0.10), 110)

    telemetry = McpResponseTelemetry(
        tool_name="test",
        arguments={},
        response_content="{}",
        response_digest="abc",
        is_error=False,
        latency_ms=10.0,
    )

    with pytest.raises(ValueError):
        seeder.record_mcp_execution(spec.bounty_id, SOLVER_ADDR, telemetry, 140)

    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 120)
    seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.10, 130)

    other_solver = "0x" + "a" * 40
    seeder.register_participant(other_solver, ParticipantRole.CHILD_SOLVER, 100)
    with pytest.raises(ValueError):
        seeder.record_mcp_execution(spec.bounty_id, other_solver, telemetry, 140)

    receipt = seeder.record_mcp_execution(spec.bounty_id, SOLVER_ADDR, telemetry, 140)
    assert isinstance(receipt, McpExecutionReceipt)
    assert receipt.solver_address == SOLVER_ADDR.lower()
    assert receipt.tool_name == "test"
    assert receipt.arguments == {}
    assert receipt.response_content == "{}"
    assert receipt.response_digest == "abc"
    assert receipt.is_error is False
    assert receipt.latency_ms == 10.0


def test_deterministic_mcp_module_verifier_success() -> None:
    """Test successful 2-of-2 quorum verification."""
    verifier = DeterministicMcpModuleVerifier((VERIFIER_A, VERIFIER_B))
    assert len(verifier.get_registered_nodes()) == 2

    tool_def = McpToolDefinition("my_tool", "desc", {"type": "object"})
    expected_content = canonicalize_json_payload({"text": "output", "type": "text"})
    expected_digest = compute_sha256_digest(expected_content)

    task_vec = DeterministicMcpTaskVector(
        tool_definition=tool_def,
        arguments={"x": 1},
        expected_text="output",
        expected_schema_keys=("text", "type"),
        expected_response_digest=expected_digest,
        max_latency_ms=100.0,
    )

    telemetry = McpResponseTelemetry(
        tool_name="my_tool",
        arguments={"x": 1},
        response_content=expected_content,
        response_digest=expected_digest,
        is_error=False,
        latency_ms=25.0,
    )

    receipt = McpExecutionReceipt(
        receipt_id="r1",
        bounty_id="0x" + "b" * 40,
        solver_address=SOLVER_ADDR.lower(),
        telemetry=telemetry,
        execution_timestamp=140,
    )

    verification = verifier.verify_execution(receipt, task_vec, 150)
    assert verification.passed is True
    assert len(verification.signatures) == 2
    assert verification.threshold == 2


def test_deterministic_mcp_module_verifier_failures() -> None:
    """Test failure branches for quorum verification."""
    verifier = DeterministicMcpModuleVerifier((VERIFIER_A, VERIFIER_B))
    tool_def = McpToolDefinition("my_tool", "desc", {"type": "object"})
    expected_content = canonicalize_json_payload({"text": "output", "type": "text"})
    expected_digest = compute_sha256_digest(expected_content)

    task_vec = DeterministicMcpTaskVector(
        tool_definition=tool_def,
        arguments={},
        expected_text="output",
        expected_schema_keys=("text", "type"),
        expected_response_digest=expected_digest,
        max_latency_ms=50.0,
    )

    bad_tool_telemetry = McpResponseTelemetry(
        tool_name="wrong_tool",
        arguments={},
        response_content=expected_content,
        response_digest=expected_digest,
        is_error=False,
        latency_ms=20.0,
    )
    r_bad_tool = McpExecutionReceipt("r1", "0x" + "b" * 40, SOLVER_ADDR.lower(), bad_tool_telemetry, 140)
    assert verifier.verify_execution(r_bad_tool, task_vec, 150).passed is False

    err_telemetry = McpResponseTelemetry(
        tool_name="my_tool",
        arguments={},
        response_content=expected_content,
        response_digest=expected_digest,
        is_error=True,
        latency_ms=20.0,
    )
    r_err = McpExecutionReceipt("r2", "0x" + "b" * 40, SOLVER_ADDR.lower(), err_telemetry, 140)
    assert verifier.verify_execution(r_err, task_vec, 150).passed is False

    high_latency_telemetry = McpResponseTelemetry(
        tool_name="my_tool",
        arguments={},
        response_content=expected_content,
        response_digest=expected_digest,
        is_error=False,
        latency_ms=100.0,
    )
    r_latency = McpExecutionReceipt("r3", "0x" + "b" * 40, SOLVER_ADDR.lower(), high_latency_telemetry, 140)
    assert verifier.verify_execution(r_latency, task_vec, 150).passed is False

    bad_digest_telemetry = McpResponseTelemetry(
        tool_name="my_tool",
        arguments={},
        response_content=expected_content,
        response_digest="invalid_digest",
        is_error=False,
        latency_ms=20.0,
    )
    r_digest = McpExecutionReceipt("r4", "0x" + "b" * 40, SOLVER_ADDR.lower(), bad_digest_telemetry, 140)
    assert verifier.verify_execution(r_digest, task_vec, 150).passed is False

    bad_json_telemetry = McpResponseTelemetry(
        tool_name="my_tool",
        arguments={},
        response_content="not json",
        response_digest=compute_sha256_digest("not json"),
        is_error=False,
        latency_ms=20.0,
    )
    r_json = McpExecutionReceipt("r5", "0x" + "b" * 40, SOLVER_ADDR.lower(), bad_json_telemetry, 140)
    assert verifier.verify_execution(r_json, task_vec, 150).passed is False


def test_verify_and_settle_lifecycle() -> None:
    """Verify entire settlement transition, proof generation, and margin analysis."""
    seeder = McpBountySeeder()
    seeder.register_participant(CREATOR_ADDR, ParticipantRole.PARENT_CREATOR, 100)
    seeder.register_participant(SOLVER_ADDR, ParticipantRole.CHILD_SOLVER, 100)
    spec = seeder.publish_child_terms(PARENT_ADDR, "Task", "Desc", (0.90, 0.10), 110)
    seeder.fund_child_escrow(spec.bounty_id, CREATOR_ADDR, 1.00, 120)
    seeder.claim_parent_bounty(PARENT_ADDR, spec.bounty_id, CREATOR_ADDR, 0.01, 125)
    seeder.claim_child_bounty(spec.bounty_id, SOLVER_ADDR, 0.10, 130)

    tool_def = McpToolDefinition("my_tool", "desc", {"type": "object"})
    content = canonicalize_json_payload({"text": "done", "type": "text"})
    digest = compute_sha256_digest(content)

    task_vec = DeterministicMcpTaskVector(
        tool_definition=tool_def,
        arguments={},
        expected_text="done",
        expected_schema_keys=("text", "type"),
        expected_response_digest=digest,
        max_latency_ms=100.0,
    )

    telemetry = McpResponseTelemetry("my_tool", {}, content, digest, False, 15.0)
    receipt = seeder.record_mcp_execution(spec.bounty_id, SOLVER_ADDR, telemetry, 140)

    settlement, proof, margin = seeder.verify_and_settle(spec.bounty_id, receipt, task_vec, 150)

    assert seeder.bounty_states[spec.bounty_id] == BountyStatus.SETTLED
    assert settlement.payout_usdc == 0.90
    assert settlement.event_type == "BountySettled"
    assert settlement.transaction_hash.startswith("0x")
    assert settlement.block_number == 21890123
    assert settlement.proof_hex == abi_encode_address(spec.bounty_id)

    assert proof.child_bounty_address == spec.bounty_id
    assert proof.encoded_abi == abi_encode_address(spec.bounty_id)
    assert len(proof.encoded_abi) == 66

    assert margin.parent_reward_usdc == 2.00
    assert margin.child_funding_usdc == 1.00
    assert margin.gross_profit_usdc == 1.00
    assert margin.net_margin_percentage == 50.0


def test_cli_execution() -> None:
    """Verify all CLI subcommands produce valid zero-exit output."""
    assert cli_main(["demo"]) == 0
    assert cli_main(["verify"]) == 0
    assert cli_main(["margin", "--parent-reward", "2.00", "--child-funding", "1.00"]) == 0
    assert (
        cli_main(
            [
                "seed",
                "--parent",
                PARENT_ADDR,
                "--title",
                "CLI Seed Test",
                "--description",
                "CLI Desc",
            ]
        )
        == 0
    )


def test_standalone_verification_script() -> None:
    """Ensure scripts/verify_issue_1295.py passes completely."""
    result = run_verification()
    assert result["status"] == "success"
    assert result["bounty_status"] == "settled"
    assert result["quorum_passed"] is True
    assert result["solver_payout_usdc"] == 0.90
    assert result["bond_refund_usdc"] == 0.10
    assert result["parent_reward_usdc"] == 2.00
    assert result["gross_profit_usdc"] == 1.00
    assert result["net_margin_percentage"] == 50.0
