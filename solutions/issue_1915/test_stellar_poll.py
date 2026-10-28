"""Unit tests for Issue #1915: Stellar confirmation polling under transient RPC errors."""

import unittest
from solutions.issue_1915.stellar_poll import (
    STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES,
    STELLAR_CONFIRMATION_RETRY_DELAY_MS,
    MockStellarRpcServer,
    SubmissionTimeoutError,
    poll_transaction_status,
)

FAKE_HASH = "0x9876543210abcdef9876543210abcdef9876543210abcdef9876543210abcdef"


class TestStellarPolling(unittest.TestCase):
    """Test suite verifying transient RPC tolerance and hash preservation."""

    def test_constants_match_spec(self):
        """Verify retry count and backoff constants mirror iris tolerance policy."""
        self.assertEqual(STELLAR_CONFIRMATION_MAX_CONSECUTIVE_RPC_FAILURES, 5)
        self.assertEqual(STELLAR_CONFIRMATION_RETRY_DELAY_MS, 1000)

    def test_rides_out_transient_failures_and_resolves(self):
        """Acceptance Criterion 1: throws N-1 transiently, then returns SUCCESS and resolves."""
        responses = [
            ConnectionResetError("connect ECONNRESET"),
            RuntimeError("503 Service Unavailable"),
            ConnectionError("socket hang up"),
            ConnectionResetError("connect ECONNRESET"),
            {"status": "SUCCESS"},
        ]
        server = MockStellarRpcServer(responses)

        res = poll_transaction_status(
            server=server,
            tx_hash=FAKE_HASH,
            sleep_fn=lambda _: None,
        )

        self.assertEqual(res, FAKE_HASH)
        self.assertEqual(server.call_count, 5)

    def test_rejects_with_submission_timeout_error_carrying_hash(self):
        """Acceptance Criterion 2: persistently throwing rejects with SubmissionTimeoutError carrying hash."""
        responses = [
            ConnectionRefusedError("connect ECONNREFUSED"),
            ConnectionRefusedError("connect ECONNREFUSED"),
            ConnectionRefusedError("connect ECONNREFUSED"),
            ConnectionRefusedError("connect ECONNREFUSED"),
            ConnectionRefusedError("connect ECONNREFUSED"),
            ConnectionRefusedError("connect ECONNREFUSED"),
        ]
        server = MockStellarRpcServer(responses)

        with self.assertRaises(SubmissionTimeoutError) as ctx:
            poll_transaction_status(
                server=server,
                tx_hash=FAKE_HASH,
                sleep_fn=lambda _: None,
            )

        err = ctx.exception
        self.assertEqual(err.hash, FAKE_HASH)
        self.assertIn("failed 5 consecutive times", str(err))
        self.assertEqual(server.call_count, 5)

    def test_terminal_failed_status_rejects_immediately(self):
        """Acceptance Criterion 3: FAILED status rejects immediately without retries."""
        server = MockStellarRpcServer([{"status": "FAILED"}])

        with self.assertRaises(RuntimeError) as ctx:
            poll_transaction_status(
                server=server,
                tx_hash=FAKE_HASH,
                sleep_fn=lambda _: None,
            )

        self.assertIn("failed", str(ctx.exception))
        self.assertEqual(server.call_count, 1)

    def test_deadline_timeout_preserves_hash(self):
        """When overall deadline passes without confirming, SubmissionTimeoutError carries hash."""
        # Simulated clock advancing past deadline
        simulated_time = [0.0]

        def fake_time():
            return simulated_time[0]

        def fake_sleep(sec):
            simulated_time[0] += sec

        server = MockStellarRpcServer([{"status": "PENDING"}] * 100)

        with self.assertRaises(SubmissionTimeoutError) as ctx:
            poll_transaction_status(
                server=server,
                tx_hash=FAKE_HASH,
                timeout_ms=5000,
                retry_delay_ms=1000,
                sleep_fn=fake_sleep,
                time_fn=fake_time,
            )

        self.assertEqual(ctx.exception.hash, FAKE_HASH)
        self.assertIn("timed out after 5000ms", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
