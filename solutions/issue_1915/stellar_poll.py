"""Stellar Confirmation Polling Engine with Transient RPC Fault Tolerance.

Resolves Issue #1915 (and Parabola-org/parabola#1):
Preserve burnTxHash when Stellar confirmation polling hits transient RPC errors.
Surfaces burnTxHash via SubmissionTimeoutError when RPC fails persistently.
"""

import time
from typing import Any, Callable, Dict, Optional

STELLAR_CONFIRMATION_TIMEOUT_MS = 60_000
STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES = 5
STELLAR_CONFIRMATION_RETRY_DELAY_MS = 1_000


class SubmissionTimeoutError(Exception):
    """Thrown when a submitted transaction confirmation times out or RPC persistently fails.

    Carries the broadcast transaction hash so callers never lose their handle
    on an in-flight transaction.
    """

    def __init__(self, message: str, tx_hash: str) -> None:
        super().__init__(message)
        self.hash = tx_hash


class MockStellarRpcServer:
    """Mock or adapter interface for Soroban RPC server."""

    def __init__(self, responses: Optional[list] = None) -> None:
        self.responses = list(responses) if responses is not None else []
        self.call_count = 0

    def get_transaction(self, tx_hash: str) -> Dict[str, Any]:
        """Fetch transaction status by hash."""
        self.call_count += 1
        if not self.responses:
            return {"status": "SUCCESS"}
        resp = self.responses.pop(0)
        if isinstance(resp, Exception):
            raise resp
        return resp


def poll_transaction_status(
    server: Any,
    tx_hash: str,
    timeout_ms: int = STELLAR_CONFIRMATION_TIMEOUT_MS,
    retry_delay_ms: int = STELLAR_CONFIRMATION_RETRY_DELAY_MS,
    max_consecutive_failures: int = STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES,
    sleep_fn: Optional[Callable[[float], None]] = None,
    time_fn: Optional[Callable[[], float]] = None,
) -> str:
    """Poll transaction status until confirmed, rejected, or timed out.

    Tolerates transient RPC errors (connection reset, 5xx) with bounded
    consecutive-failure retries. Surfaces the transaction hash via
    SubmissionTimeoutError if retries are exhausted or the timeout is reached.
    Terminal 'FAILED' statuses reject immediately.
    """
    if sleep_fn is None:
        sleep_fn = time.sleep
    if time_fn is None:
        time_fn = time.time

    start_time = time_fn()
    deadline = start_time + (timeout_ms / 1000.0)
    retry_delay_sec = retry_delay_ms / 1000.0
    consecutive_rpc_failures = 0

    while time_fn() < deadline:
        try:
            result = server.get_transaction(tx_hash)
            consecutive_rpc_failures = 0
        except Exception as err:
            consecutive_rpc_failures += 1
            if consecutive_rpc_failures >= max_consecutive_failures:
                msg = (
                    f"Stellar RPC failed {consecutive_rpc_failures} consecutive times "
                    f"polling transaction {tx_hash}: {err}"
                )
                raise SubmissionTimeoutError(msg, tx_hash=tx_hash) from err
            sleep_fn(retry_delay_sec)
            continue

        status = result.get("status")
        if status == "SUCCESS":
            return tx_hash
        if status == "FAILED":
            raise RuntimeError(f"Stellar transaction {tx_hash} failed")

        sleep_fn(retry_delay_sec)

    timeout_msg = f"Stellar transaction {tx_hash} confirmation timed out after {timeout_ms}ms"
    raise SubmissionTimeoutError(timeout_msg, tx_hash=tx_hash)
