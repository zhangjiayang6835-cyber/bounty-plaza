"""Data models and cryptographic primitives for Agent Bounties MCP child seeder."""

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import re

ADDRESS_PATTERN = re.compile(r"^0x[0-9a-fA-F]{40}$")


class BountyStatus(str, Enum):
    """Lifecycle state machine status for agent bounties."""

    UNAVAILABLE = "unavailable"
    ESCROWED = "escrowed"
    READY_TO_EARN = "ready_to_earn"
    EXCLUSIVE_CLAIM = "exclusive_claim"
    SETTLED = "settled"
    RETIRED = "retired"


class ParticipantRole(str, Enum):
    """Participant role classification on Base network."""

    PARENT_CREATOR = "parent_creator"
    CHILD_SOLVER = "child_solver"
    VERIFIER_NODE = "verifier_node"


@dataclass(frozen=True)
class Participant:
    """Registered participant identity on Base network."""

    address: str
    role: ParticipantRole
    registration_timestamp: int
    active: bool = True

    def __post_init__(self) -> None:
        """Validate participant parameters."""
        validate_evm_address(self.address)
        if self.registration_timestamp <= 0:
            raise ValueError("Registration timestamp must be positive")


@dataclass(frozen=True)
class McpToolDefinition:
    """Specification of an MCP server tool."""

    name: str
    description: str
    input_schema: dict[str, object]

    def __post_init__(self) -> None:
        """Validate MCP tool definition fields."""
        if not self.name or not self.name.strip():
            raise ValueError("Tool name cannot be empty")
        if not self.description or not self.description.strip():
            raise ValueError("Tool description cannot be empty")
        if not isinstance(self.input_schema, dict):
            raise ValueError("Input schema must be a dictionary")
        if self.input_schema.get("type") != "object":
            raise ValueError("Input schema type must be object")


@dataclass(frozen=True)
class DeterministicMcpTaskVector:
    """Specification of deterministic MCP task execution."""

    tool_definition: McpToolDefinition
    arguments: dict[str, object]
    expected_text: str
    expected_schema_keys: tuple[str, ...]
    expected_response_digest: str
    max_latency_ms: float

    def __post_init__(self) -> None:
        """Validate MCP task constraints."""
        if not self.expected_response_digest:
            raise ValueError("Expected response digest must be provided")
        if not self.expected_text:
            raise ValueError("Expected text output must be provided")
        if self.max_latency_ms <= 0.0:
            raise ValueError("Maximum latency threshold must be positive")

    @property
    def tool_name(self) -> str:
        """Return target MCP tool name."""
        return self.tool_definition.name


@dataclass(frozen=True)
class BountyEconomics:
    """Financial parameters for bounty funding."""

    solver_reward_usdc: float
    bond_usdc: float
    total_funding_usdc: float

    def __post_init__(self) -> None:
        """Enforce strict child bounty funding constraints."""
        if self.solver_reward_usdc <= 0.0:
            raise ValueError("Solver reward must be greater than zero")
        if self.bond_usdc < 0.0:
            raise ValueError("Bond cannot be negative")
        expected_total = round(self.solver_reward_usdc + self.bond_usdc, 4)
        if round(self.total_funding_usdc, 4) != expected_total:
            raise ValueError("Total funding must match reward plus bond")


@dataclass(frozen=True)
class ChildMcpBountySpec:
    """Immutable parameters for a concrete MCP child bounty."""

    bounty_id: str
    parent_bounty_id: str
    title: str
    description: str
    economics: BountyEconomics
    verifier_type: str
    deadline_timestamp: int

    @property
    def solver_reward_usdc(self) -> float:
        """Return solver reward."""
        return self.economics.solver_reward_usdc

    @property
    def bond_usdc(self) -> float:
        """Return solver bond."""
        return self.economics.bond_usdc

    @property
    def total_funding_usdc(self) -> float:
        """Return total funding amount."""
        return self.economics.total_funding_usdc


@dataclass(frozen=True)
class McpResponseTelemetry:
    """MCP execution measurements including payload digest and latency."""

    tool_name: str
    arguments: dict[str, object]
    response_content: str
    response_digest: str
    is_error: bool
    latency_ms: float


@dataclass(frozen=True)
class McpExecutionReceipt:
    """Cryptographic execution receipt of deterministic MCP run."""

    receipt_id: str
    bounty_id: str
    solver_address: str
    telemetry: McpResponseTelemetry
    execution_timestamp: int

    @property
    def tool_name(self) -> str:
        """Return invoked tool name."""
        return self.telemetry.tool_name

    @property
    def arguments(self) -> dict[str, object]:
        """Return tool invocation arguments."""
        return self.telemetry.arguments

    @property
    def response_content(self) -> str:
        """Return response content payload."""
        return self.telemetry.response_content

    @property
    def response_digest(self) -> str:
        """Return response hash digest."""
        return self.telemetry.response_digest

    @property
    def is_error(self) -> bool:
        """Return error state flag."""
        return self.telemetry.is_error

    @property
    def latency_ms(self) -> float:
        """Return roundtrip execution latency in milliseconds."""
        return self.telemetry.latency_ms


@dataclass(frozen=True)
class QuorumVerification:
    """Consensus verification record from verifier quorum nodes."""

    bounty_id: str
    verifier_count: int
    threshold: int
    passed: bool
    signatures: tuple[str, ...]
    verification_digest: str
    timestamp: int


@dataclass(frozen=True)
class BlockAnchor:
    """Base network block and transaction anchor."""

    transaction_hash: str
    block_number: int


@dataclass(frozen=True)
class CanonicalSettlementReceipt:
    """Canonical event receipt proving on-chain bounty settlement."""

    event_type: str
    anchor: BlockAnchor
    timestamp: int
    bounty_id: str
    solver_address: str
    payout_usdc: float
    proof_hex: str

    @property
    def transaction_hash(self) -> str:
        """Return transaction hash."""
        return self.anchor.transaction_hash

    @property
    def block_number(self) -> int:
        """Return block number."""
        return self.anchor.block_number


@dataclass(frozen=True)
class ParentProofPayload:
    """Encoded payload submitted to parent bounty contract."""

    child_bounty_address: str
    encoded_abi: str
    discovery_feedback: str
    proof_digest: str


@dataclass(frozen=True)
class EconomicMarginAnalysis:
    """Economic accounting metrics for parent-child bounty arbitrage."""

    parent_reward_usdc: float
    child_funding_usdc: float
    parent_claim_bond_usdc: float
    gross_profit_usdc: float
    net_margin_percentage: float
    payout_routing_evm: str
    payout_routing_stellar: str


def validate_evm_address(address: str) -> str:
    """Validate 20-byte EVM address format and return canonical lowercase representation.

    Args:
        address: Hexadecimal EVM address string.

    Returns:
        Canonical 42-character lowercase hex address with 0x prefix.

    Raises:
        ValueError: If address format is invalid.
    """
    if not isinstance(address, str):
        raise ValueError("Address must be a string")
    cleaned = address.strip()
    if not ADDRESS_PATTERN.match(cleaned):
        raise ValueError(f"Invalid EVM address format: {address}")
    result = cleaned.lower()
    return result


def abi_encode_address(address: str) -> str:
    """Encode an EVM address into standard 32-byte ABI word (left zero-padded).

    Args:
        address: 20-byte EVM hex address.

    Returns:
        Hex-encoded string of 64 characters prefixed with 0x.
    """
    canonical = validate_evm_address(address)
    raw_hex = canonical[2:]
    padded_hex = raw_hex.rjust(64, "0")
    result = f"0x{padded_hex}"
    return result


def compute_sha256_digest(payload: str) -> str:
    """Compute SHA-256 cryptographic digest of string payload.

    Args:
        payload: String data to hash.

    Returns:
        Hexadecimal digest string.
    """
    digest_builder = hashlib.sha256()
    digest_builder.update(payload.encode("utf-8"))
    result = digest_builder.hexdigest()
    return result


def canonicalize_json_payload(data: dict) -> str:
    """Serialize dictionary to canonical JSON representation with sorted keys.

    Args:
        data: Python dictionary to serialize.

    Returns:
        Deterministic string representation.
    """
    serialized = json.dumps(data, sort_keys=True, separators=(",", ":"))
    return serialized
