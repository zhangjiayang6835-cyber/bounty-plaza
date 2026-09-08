"""Data models for the EVM Dual-Stack Network Gateway."""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import ipaddress
import re
from typing import Any, Optional


class IPVersion(str, Enum):
    """Supported Internet Protocol versions for network transport."""

    IPV4 = "IPv4"
    IPV6 = "IPv6"


@dataclass(frozen=True)
class IPGatewayConfig:
    """Network gateway host configuration for Ethereum RPC transport."""

    host: str
    port: int = 8545
    timeout_ms: float = 2000.0
    max_connections: int = 128
    is_active: bool = True

    def __post_init__(self) -> None:
        """Validate the IP address format strictly according to RFCs."""
        try:
            ipaddress.ip_address(self.host)
        except ValueError as exc:
            raise ValueError(f"Invalid IP address format: {self.host}") from exc

        if not 1 <= self.port <= 65535:
            raise ValueError(f"Port must be between 1 and 65535, got {self.port}")

    @property
    def version(self) -> IPVersion:
        """Return the IPVersion corresponding to the configured host."""
        ip_obj = ipaddress.ip_address(self.host)
        if isinstance(ip_obj, ipaddress.IPv6Address):
            return IPVersion.IPV6
        return IPVersion.IPV4

    def is_ipv6(self) -> bool:
        """Check whether the gateway host is an IPv6 address."""
        return self.version == IPVersion.IPV6

    def canonical_ip(self) -> str:
        """Return the RFC-canonical string representation of the IP address."""
        return str(ipaddress.ip_address(self.host))

    def is_honeypot_target_address(self) -> bool:
        """Check if this gateway matches the issue #1214 IPv6 test vector."""
        target = ipaddress.ip_address("2001:0db8:85a3::8a2e:0370:7334")
        return ipaddress.ip_address(self.host) == target


@dataclass(frozen=True)
class EVMTransaction:
    """Represents a discrete Ethereum Virtual Machine transaction."""

    sender: str
    recipient: str
    value_wei: int = 0
    gas_limit: int = 21000
    gas_price_wei: int = 1_000_000_000
    nonce: int = 0
    data: bytes = b""

    def __post_init__(self) -> None:
        """Validate transaction parameters and address format."""
        addr_pattern = re.compile(r"^0x[a-fA-F0-9]{40}$")
        if not addr_pattern.match(self.sender):
            raise ValueError(f"Invalid Ethereum sender address: {self.sender}")
        if not addr_pattern.match(self.recipient):
            raise ValueError(f"Invalid Ethereum recipient address: {self.recipient}")
        if self.gas_limit < 21000:
            raise ValueError("Gas limit cannot be less than standard 21000")
        if self.value_wei < 0 or self.gas_price_wei < 0 or self.nonce < 0:
            raise ValueError("Numerical values cannot be negative")

    def compute_tx_hash(self) -> str:
        """Compute deterministic transaction hash representation."""
        payload = (
            f"{self.nonce}:{self.sender}:"
            f"{self.recipient}:{self.value_wei}:{self.data.hex()}"
        ).encode("utf-8")
        digest = hashlib.sha256(payload).hexdigest()
        return f"0x{digest}"


@dataclass
class RPCRequest:
    """Ethereum JSON-RPC 2.0 request envelope."""

    method: str
    params: list[Any] = field(default_factory=list)
    request_id: int = 1
    jsonrpc: str = "2.0"


@dataclass
class RPCResponse:
    """Ethereum JSON-RPC 2.0 response envelope with network telemetry."""

    request_id: int
    result: Any = None
    error: Optional[dict[str, Any]] = None
    latency_ms: float = 0.0
    transport_ip: str = ""
    ip_version: IPVersion = IPVersion.IPV4
    on_chain_gas_consumed: int = 0


@dataclass
class GatewayMetrics:
    """Operational telemetry counters for the dual-stack gateway."""

    total_requests: int = 0
    ipv4_requests: int = 0
    ipv6_requests: int = 0
    successful_dispatches: int = 0
    failed_dispatches: int = 0
    on_chain_gas_incurred: int = 0
    average_latency_ms: float = 0.0
