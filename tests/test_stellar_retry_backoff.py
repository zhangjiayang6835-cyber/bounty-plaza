"""Unit tests for Stellar retry/backoff configuration (#1904)."""

import unittest
from src.stellar_retry_backoff import (
    DEFAULT_ALLOWANCE_ATTEMPTS,
    DEFAULT_ALLOWANCE_DELAY_MS,
    DEFAULT_RPC_LAG_ATTEMPTS,
    DEFAULT_RPC_LAG_DELAY_MS,
    StellarRetryOptions,
    retry_on_transient_rpc_lag,
    wait_for_allowance,
)


class TestStellarRetryBackoff(unittest.TestCase):
    """Verify Stellar retry and backoff configuration behavior."""

    def test_defaults_preserved(self):
        opts = StellarRetryOptions()
        self.assertEqual(opts.resolve(DEFAULT_ALLOWANCE_ATTEMPTS, DEFAULT_ALLOWANCE_DELAY_MS), (6, 1500))
        self.assertEqual(opts.resolve(DEFAULT_RPC_LAG_ATTEMPTS, DEFAULT_RPC_LAG_DELAY_MS), (3, 2000))

    def test_wait_for_allowance_custom_knobs(self):
        delays = []
        calls = {"n": 0}

        def fetch():
            calls["n"] += 1
            return 100 if calls["n"] >= 4 else 0

        res = wait_for_allowance(
            fetch,
            required_amount=100,
            options=StellarRetryOptions(attempts=5, delay_ms=250),
            sleep_ms=delays.append,
        )
        self.assertEqual(res, 100)
        self.assertEqual(calls["n"], 4)
        self.assertEqual(delays, [250, 250, 250])

    def test_retry_on_transient_rpc_lag_custom_knobs(self):
        delays = []
        calls = {"n": 0}

        def op():
            calls["n"] += 1
            if calls["n"] < 3:
                raise ConnectionError("transient Soroban RPC lag")
            return "tx_hash_ok"

        res = retry_on_transient_rpc_lag(
            op,
            is_transient_error=lambda e: isinstance(e, ConnectionError),
            options=StellarRetryOptions(attempts=4, delay_ms=400),
            sleep_ms=delays.append,
        )
        self.assertEqual(res, "tx_hash_ok")
        self.assertEqual(calls["n"], 3)
        self.assertEqual(delays, [400, 400])

    def test_invalid_options_rejected(self):
        with self.assertRaises(ValueError):
            StellarRetryOptions(attempts=0, delay_ms=100).resolve(6, 1500)
        with self.assertRaises(ValueError):
            StellarRetryOptions(attempts=True, delay_ms=100).resolve(6, 1500)
        with self.assertRaises(ValueError):
            StellarRetryOptions(attempts=3, delay_ms=-10).resolve(3, 2000)


if __name__ == "__main__":
    unittest.main()
