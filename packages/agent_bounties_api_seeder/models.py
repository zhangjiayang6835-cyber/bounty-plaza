"""Data models and cryptographic primitives for Agent Bounties API child seeder."""

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


class ApiHttpMethod(str, Enum):
    """Standard HTTP methods for API task vector specifications."""

    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"


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
class ApiEndpointSpec:
    """HTTP route, method, and request body specification."""

    route: str
    method: ApiHttpMethod
    request_body: str

    def __post_init__(self) -> None:
        """Validate endpoint route."""
        if not self.route.startswith("/"):
            raise ValueError("Endpoint route must start with /")


@dataclass(frozen=True)
class DeterministicApiTaskVector:
    """Specification of deterministic API task execution."""

    endpoint: ApiEndpointSpec
    expected_status_code: int
    expected_schema: tuple[str, ...]
    expected_response_digest: str
    max_latency_ms: float

    def __post_init__(self) -> None:
        """Validate API task constraints."""
        if not self.expected_response_digest:
            raise ValueError("Expected response digest must be provided")
        if self.expected_status_code < 100 or self.expected_status_code > 599:
            raise ValueError("Invalid HTTP status code range")
        if self.max_latency_ms <= 0.0:
            raise ValueError("Maximum latency threshold must be positive")

    @property
    def endpoint_route(self) -> str:
        """Return endpoint route."""
        return self.endpoint.route

    @property
    def http_method(self) -> ApiHttpMethod:
        """Return HTTP method."""
        return self.endpoint.method

    @property
    def request_body(self) -> str:
        """Return request payload."""
        return self.endpoint.request_body


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
class ChildApiBountySpec:
    """Immutable parameters for a concrete API child bounty."""

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
class ApiResponseTelemetry:
    """HTTP response measurements including payload digest and latency."""

    status_code: int
    response_body: str
    response_digest: str
    latency_ms: float


@dataclass(frozen=True)
class ApiExecutionReceipt:
    """Cryptographic execution receipt of deterministic API run."""

    receipt_id: str
    bounty_id: str
    solver_address: str
    telemetry: ApiResponseTelemetry
    execution_timestamp: int

    @property
    def status_code(self) -> int:
        """Return HTTP status code."""
        return self.telemetry.status_code

    @property
    def response_body(self) -> str:
        """Return response payload."""
        return self.telemetry.response_body

    @property
    def response_digest(self) -> str:
        """Return response hash digest."""
        return self.telemetry.response_digest

    @property
    def latency_ms(self) -> float:
        """Return roundtrip latency in milliseconds."""
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
