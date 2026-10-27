"""Configurable retry and backoff knobs for Stellar allowance wait and RPC-lag recovery (#1904)."""

from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Optional, TypeVar

T = TypeVar("T")

DEFAULT_ALLOWANCE_ATTEMPTS = 6
DEFAULT_ALLOWANCE_DELAY_MS = 1500
DEFAULT_RPC_LAG_ATTEMPTS = 3
DEFAULT_RPC_LAG_DELAY_MS = 2000


@dataclass(frozen=True)
class StellarRetryOptions:
    """Validated retry configuration for Stellar recovery loops."""

    attempts: Optional[int] = None
    delay_ms: Optional[int] = None

    def resolve(self, default_attempts: int, default_delay_ms: int) -> tuple[int, int]:
        """Return (attempts, delay_ms) preserving exact defaults when omitted."""
        resolved_attempts = default_attempts if self.attempts is None else self.attempts
        resolved_delay = default_delay_ms if self.delay_ms is None else self.delay_ms
        if isinstance(resolved_attempts, bool) or not isinstance(resolved_attempts, int) or resolved_attempts < 1:
            raise ValueError("stellarRetryAttempts must be a positive integer >= 1")
        if isinstance(resolved_delay, bool) or not isinstance(resolved_delay, int) or resolved_delay < 0:
            raise ValueError("stellarRetryDelayMs must be a non-negative integer >= 0")
        return resolved_attempts, resolved_delay


def wait_for_allowance(
    fetch_allowance: Callable[[], int],
    required_amount: int,
    options: Optional[StellarRetryOptions] = None,
    sleep_ms: Optional[Callable[[int], None]] = None,
) -> int:
    """Poll allowance up to configured attempts and delay, preserving 6 x 1500ms defaults."""
    opts = options or StellarRetryOptions()
    attempts, delay_ms = opts.resolve(DEFAULT_ALLOWANCE_ATTEMPTS, DEFAULT_ALLOWANCE_DELAY_MS)
    sleeper = sleep_ms or (lambda _ms: None)

    last_allowance = 0
    for idx in range(attempts):
        last_allowance = fetch_allowance()
        if last_allowance >= required_amount:
            return last_allowance
        if idx + 1 < attempts:
            sleeper(delay_ms)
    raise TimeoutError(f"Insufficient Stellar allowance after {attempts} attempts: {last_allowance} < {required_amount}")


def retry_on_transient_rpc_lag(
    operation: Callable[[], T],
    is_transient_error: Callable[[Exception], bool],
    options: Optional[StellarRetryOptions] = None,
    sleep_ms: Optional[Callable[[int], None]] = None,
) -> T:
    """Retry transient Soroban RPC-lag errors, preserving 3 x 2000ms defaults."""
    opts = options or StellarRetryOptions()
    attempts, delay_ms = opts.resolve(DEFAULT_RPC_LAG_ATTEMPTS, DEFAULT_RPC_LAG_DELAY_MS)
    sleeper = sleep_ms or (lambda _ms: None)

    for idx in range(attempts):
        try:
            return operation()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if idx + 1 >= attempts or not is_transient_error(exc):
                raise
            sleeper(delay_ms)
    raise RuntimeError("Unreachable retry state")
