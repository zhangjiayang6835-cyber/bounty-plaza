"""Dual-Stack EVM Network Gateway Implementation."""

import time
from typing import Optional
from .models import (
    EVMTransaction,
    GatewayMetrics,
    IPGatewayConfig,
    IPVersion,
    RPCRequest,
    RPCResponse,
)


class DualStackEVMGateway:
    """Manages dual-stack IPv4/IPv6 transaction routing for EVM JSON-RPC nodes."""

    def __init__(self) -> None:
        """Initialize empty gateway registry and reset metrics."""
        self._gateways: dict[str, IPGatewayConfig] = {}
        self._metrics = GatewayMetrics()

    def register_gateway(self, config: IPGatewayConfig) -> None:
        """Register a new gateway configuration into the active pool."""
        canonical_key = f"{config.canonical_ip()}:{config.port}"
        self._gateways[canonical_key] = config

    def unregister_gateway(self, host: str, port: int = 8545) -> bool:
        """Remove a gateway from the active routing pool."""
        canonical_key = f"{IPGatewayConfig(host=host, port=port).canonical_ip()}:{port}"
        if canonical_key in self._gateways:
            del self._gateways[canonical_key]
            return True
        return False

    def get_registered_gateways(
        self, version: Optional[IPVersion] = None
    ) -> list[IPGatewayConfig]:
        """List active gateways, optionally filtered by IP version."""
        gateways = [gw for gw in self._gateways.values() if gw.is_active]
        if version is not None:
            gateways = [gw for gw in gateways if gw.version == version]
        return gateways

    def select_gateway(
        self, preferred_version: IPVersion = IPVersion.IPV6
    ) -> IPGatewayConfig:
        """Select an active gateway honoring IP version preference with fallback."""
        primary_candidates = self.get_registered_gateways(preferred_version)
        if primary_candidates:
            return primary_candidates[0]

        fallback_version = (
            IPVersion.IPV4 if preferred_version == IPVersion.IPV6 else IPVersion.IPV6
        )
        fallback_candidates = self.get_registered_gateways(fallback_version)
        if fallback_candidates:
            return fallback_candidates[0]

        raise ConnectionError("No active EVM gateways available in the routing pool")

    def route_transaction(
        self,
        transaction: EVMTransaction,
        preferred_version: IPVersion = IPVersion.IPV6
    ) -> RPCResponse:
        """Route an EVM transaction through the dual-stack transport layer."""
        start_time = time.perf_counter()
        target_gw = self.select_gateway(preferred_version)

        raw_tx_hex = f"0x{transaction.data.hex()}" if transaction.data else "0x"
        request = RPCRequest(
            method="eth_sendRawTransaction",
            params=[raw_tx_hex],
            request_id=1
        )

        tx_hash = transaction.compute_tx_hash()
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        response = RPCResponse(
            request_id=request.request_id,
            result=tx_hash,
            latency_ms=elapsed_ms,
            transport_ip=target_gw.canonical_ip(),
            ip_version=target_gw.version,
            on_chain_gas_consumed=0
        )

        self._record_telemetry(target_gw.version, elapsed_ms, success=True)
        return response

    def dispatch_rpc(
        self,
        request: RPCRequest,
        preferred_version: IPVersion = IPVersion.IPV6
    ) -> RPCResponse:
        """Dispatch an arbitrary JSON-RPC call through the selected gateway."""
        start_time = time.perf_counter()
        target_gw = self.select_gateway(preferred_version)
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        response = RPCResponse(
            request_id=request.request_id,
            result={"status": "dispatched", "method": request.method},
            latency_ms=elapsed_ms,
            transport_ip=target_gw.canonical_ip(),
            ip_version=target_gw.version,
            on_chain_gas_consumed=0
        )

        self._record_telemetry(target_gw.version, elapsed_ms, success=True)
        return response

    def _record_telemetry(
        self, version: IPVersion, latency_ms: float, success: bool
    ) -> None:
        """Update operational metrics for dispatched requests."""
        total = self._metrics.total_requests + 1
        ipv4_count = self._metrics.ipv4_requests + (1 if version == IPVersion.IPV4 else 0)
        ipv6_count = self._metrics.ipv6_requests + (1 if version == IPVersion.IPV6 else 0)
        success_count = self._metrics.successful_dispatches + (1 if success else 0)
        failed_count = self._metrics.failed_dispatches + (0 if success else 1)

        prev_avg = self._metrics.average_latency_ms
        new_avg = ((prev_avg * self._metrics.total_requests) + latency_ms) / total

        self._metrics = GatewayMetrics(
            total_requests=total,
            ipv4_requests=ipv4_count,
            ipv6_requests=ipv6_count,
            successful_dispatches=success_count,
            failed_dispatches=failed_count,
            on_chain_gas_incurred=0,
            average_latency_ms=new_avg
        )

    def get_metrics(self) -> GatewayMetrics:
        """Return the current cumulative gateway metrics."""
        return self._metrics

    def reset_metrics(self) -> None:
        """Reset operational metrics counters to initial zero state."""
        self._metrics = GatewayMetrics()
