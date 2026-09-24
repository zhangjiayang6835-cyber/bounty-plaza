"""Client implementation for deterministic JSON-RPC failover and Base chain validation."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

from __future__ import annotations

from typing import Any, Sequence

from packages.rpc_failover.models import (
    EndpointConfig,
    RpcRequest,
    RpcResponse,
)
from scripts._shared.rpc import (
    BASE_CHAIN_ID,
    BASE_RPC_ENDPOINTS,
    MAX_RETRIES,
    RpcError,
    TransportError,
    is_retryable_http_status,
    is_retryable_transport_output,
    ordered_base_rpc_endpoints,
    redact_rpc_endpoint,
    rpc,
    rpc_failover,
    select_working_base_rpc,
)


class RpcFailoverError(RuntimeError):
    """Raised when all configured RPC endpoints have failed failover attempts."""


class RpcClient:
    """Robust client managing Base RPC interactions with deterministic failover."""

    def __init__(
        self,
        default_endpoints: Sequence[str] | None = None,
        max_retries: int = MAX_RETRIES,
    ) -> None:
        """Initialize RPC client with configured endpoints and retry limits.

        Args:
            default_endpoints: Initial candidate endpoints to prioritize.
            max_retries: Maximum attempts per endpoint before failing over.
        """
        self.endpoints = (
            tuple(default_endpoints)
            if default_endpoints is not None
            else BASE_RPC_ENDPOINTS
        )
        self.max_retries = max_retries

    def get_working_endpoint(self) -> str:
        """Discover and return an operational Base mainnet RPC endpoint.

        Returns:
            Validated HTTPS endpoint reporting Base chain ID 8453.
        """
        return select_working_base_rpc(
            endpoints=self.endpoints, max_retries=self.max_retries
        )

    def execute(
        self,
        method: str,
        params: list[Any] | None = None,
        request_id: int = 1,
    ) -> Any:
        """Execute JSON-RPC query across endpoints with automatic failover.

        Args:
            method: Ethereum JSON-RPC method name.
            params: Parameters for method invocation.
            request_id: Identification integer for JSON-RPC payload.

        Returns:
            Decoded result field from RPC response.
        """
        actual_params = params if params is not None else []
        try:
            return rpc_failover(
                method=method,
                params=actual_params,
                request_id=request_id,
                endpoints=self.endpoints,
                max_retries=self.max_retries,
            )
        except RuntimeError as error:
            if isinstance(error, RpcError):
                raise
            raise RpcFailoverError(str(error)) from error


def rpc_call(
    endpoints: list[str] | tuple[str, ...],
    method: str,
    params: list[Any] | None = None,
    timeout: float = 5.0,
    request_id: int = 1,
    attempts_per_endpoint: int = 2,
) -> tuple[str, dict[str, Any]]:
    """Execute JSON-RPC request with deterministic sequential failover.

    Args:
        endpoints: Sequence of candidate RPC endpoints.
        method: Ethereum JSON-RPC method name.
        params: Arguments for JSON-RPC call.
        timeout: Maximum duration in seconds per request attempt.
        request_id: Sequential identifier for tracking requests.
        attempts_per_endpoint: Number of retry attempts per endpoint.

    Returns:
        Tuple of (selected_working_endpoint, raw_jsonrpc_response_dict).
    """
    actual_params = params if params is not None else []
    last_error: Exception | None = None

    for endpoint in endpoints:
        for attempt in range(1, attempts_per_endpoint + 1):
            try:
                result = rpc(
                    endpoint,
                    method,
                    actual_params,
                    request_id=request_id,
                    attempts=1,
                    timeout=timeout,
                )
                response = {
                    "jsonrpc": "2.0",
                    "id": request_id,
                    "result": result,
                }
                return endpoint, response
            except RpcError:
                raise
            except (TransportError, RuntimeError) as error:
                last_error = error
                if attempt >= attempts_per_endpoint:
                    break

    raise RpcFailoverError(
        f"All endpoints exhausted for method '{method}': {last_error}"
    ) from last_error


__all__ = [
    "BASE_CHAIN_ID",
    "BASE_RPC_ENDPOINTS",
    "EndpointConfig",
    "MAX_RETRIES",
    "RpcClient",
    "RpcError",
    "RpcFailoverError",
    "RpcRequest",
    "RpcResponse",
    "TransportError",
    "is_retryable_http_status",
    "is_retryable_transport_output",
    "ordered_base_rpc_endpoints",
    "redact_rpc_endpoint",
    "rpc",
    "rpc_call",
    "rpc_failover",
    "select_working_base_rpc",
]
