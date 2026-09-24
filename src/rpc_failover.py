"""Compatibility module providing deterministic RPC failover entrypoints."""

from __future__ import annotations


from packages.rpc_failover.client import (
    BASE_CHAIN_ID,
    BASE_RPC_ENDPOINTS,
    RpcClient,
    RpcError,
    RpcFailoverError,
    TransportError,
    ordered_base_rpc_endpoints,
    redact_rpc_endpoint,
    rpc,
    rpc_call,
    rpc_failover,
    select_working_base_rpc,
)
from packages.rpc_failover.models import (
    EndpointConfig,
    RpcRequest,
    RpcResponse,
    SettlementTerms,
)
from packages.rpc_failover.settlement import SettlementReconciler


__all__ = [
    "BASE_CHAIN_ID",
    "BASE_RPC_ENDPOINTS",
    "EndpointConfig",
    "RpcClient",
    "RpcError",
    "RpcFailoverError",
    "RpcRequest",
    "RpcResponse",
    "SettlementReconciler",
    "SettlementTerms",
    "TransportError",
    "ordered_base_rpc_endpoints",
    "redact_rpc_endpoint",
    "rpc",
    "rpc_call",
    "rpc_failover",
    "select_working_base_rpc",
]
