"""Data models for deterministic JSON-RPC failover and settlement verification."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RpcRequest:
    """Strongly-typed JSON-RPC 2.0 request payload."""

    method: str
    params: list[Any] = field(default_factory=list)
    request_id: int = 1
    jsonrpc: str = "2.0"

    def to_dict(self) -> dict[str, Any]:
        """Convert instance into JSON-serializable dictionary."""
        return {
            "jsonrpc": self.jsonrpc,
            "id": self.request_id,
            "method": self.method,
            "params": self.params,
        }


@dataclass(frozen=True)
class RpcResponse:
    """Standardized representation of JSON-RPC 2.0 response."""

    endpoint: str
    request_id: int
    result: Any = None
    error: dict[str, Any] | None = None
    raw_status: int = 200

    @property
    def is_success(self) -> bool:
        """Indicate whether the RPC returned a valid result without error."""
        return self.error is None


@dataclass(frozen=True)
class EndpointConfig:
    """Configuration options for a remote JSON-RPC endpoint."""

    url: str
    timeout_seconds: float = 5.0
    attempts: int = 2
    backoff_delay: float = 0.25
    expected_chain_id: int | None = 8453


@dataclass(frozen=True)
class SettlementTerms:
    """Canonical parameters for on-chain autonomous bounty settlement."""

    network: str
    contract_address: str
    solver_reward_usdc: float
    claim_bond_usdc: float
    total_funding_usdc: float
    verifier_type: str = "signed_quorum"
    quorum_threshold: int = 1

    @property
    def solver_reward_base_units(self) -> int:
        """Calculate micro-USDC integer value for solver reward."""
        return int(round(self.solver_reward_usdc * 1_000_000))

    @property
    def claim_bond_base_units(self) -> int:
        """Calculate micro-USDC integer value for claim bond."""
        return int(round(self.claim_bond_usdc * 1_000_000))

    @property
    def total_funding_base_units(self) -> int:
        """Calculate micro-USDC integer value for total funding escrow."""
        return int(round(self.total_funding_usdc * 1_000_000))
