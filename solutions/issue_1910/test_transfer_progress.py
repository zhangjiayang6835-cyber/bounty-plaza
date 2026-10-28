"""Unit tests for Issue #1910: Structured Progress Callbacks for transfer()."""

import unittest
from solutions.issue_1910.transfer_progress import (
    PROGRESS_STAGES,
    TransferCoordinator,
    emit_progress,
)


class TestTransferProgress(unittest.TestCase):
    """Test suite for structured transfer progress callbacks."""

    def setUp(self):
        self.coordinator = TransferCoordinator()

    def test_progress_stages_constant(self):
        """Verify defined stages match specification."""
        self.assertEqual(
            PROGRESS_STAGES,
            (
                "recipient-check",
                "approve",
                "burn-submitted",
                "burn-confirmed",
                "attestation",
                "mint-submitted",
                "mint-confirmed",
            ),
        )

    def test_full_transfer_stage_sequence_and_payloads(self):
        """Acceptance Criterion 2: emits expected stage sequence in order with payloads."""
        events = []

        def on_progress(event):
            events.append(event)

        result = self.coordinator.execute_transfer(
            from_chain="arc",
            to_chain="stellar",
            amount="10",
            recipient="GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
            burn_tx_hash="0xburn123",
            mint_tx_hash="0xmint456",
            attestation_hash="0xattest789",
            on_progress=on_progress,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["burnTxHash"], "0xburn123")
        self.assertEqual(result["mintTxHash"], "0xmint456")

        stages = [e["stage"] for e in events]
        self.assertEqual(
            stages,
            [
                "recipient-check",
                "approve",
                "burn-submitted",
                "burn-confirmed",
                "attestation",
                "mint-submitted",
                "mint-confirmed",
            ],
        )

        # Check payloads
        burn_confirmed = next(e for e in events if e["stage"] == "burn-confirmed")
        self.assertEqual(burn_confirmed["burnTxHash"], "0xburn123")
        self.assertIn("timestamp", burn_confirmed)

        attestation = next(e for e in events if e["stage"] == "attestation")
        self.assertEqual(attestation["burnTxHash"], "0xburn123")
        self.assertEqual(attestation["attestationHash"], "0xattest789")

        mint_confirmed = next(e for e in events if e["stage"] == "mint-confirmed")
        self.assertEqual(mint_confirmed["burnTxHash"], "0xburn123")
        self.assertEqual(mint_confirmed["mintTxHash"], "0xmint456")

    def test_callback_exception_shielding(self):
        """Acceptance Criterion 3: Throwing from onProgress does not alter result or error behavior."""
        call_count = [0]

        def exploding_callback(event):
            call_count[0] += 1
            raise RuntimeError("Subscriber crashed intentionally!")

        result = self.coordinator.execute_transfer(
            from_chain="arc",
            to_chain="stellar",
            amount="50",
            recipient="GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
            burn_tx_hash="0xburn_safe",
            mint_tx_hash="0xmint_safe",
            on_progress=exploding_callback,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["burnTxHash"], "0xburn_safe")
        self.assertEqual(result["mintTxHash"], "0xmint_safe")
        self.assertEqual(call_count[0], 7)

    def test_omitted_callback_executes_normally(self):
        """Acceptance Criterion 4: No behavior change when onProgress is omitted."""
        result = self.coordinator.execute_transfer(
            from_chain="stellar",
            to_chain="arc",
            amount="100",
            recipient="0x1111111111111111111111111111111111111111",
            burn_tx_hash="0xburn_solo",
            mint_tx_hash="0xmint_solo",
            on_progress=None,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["burnTxHash"], "0xburn_solo")
        self.assertEqual(result["mintTxHash"], "0xmint_solo")

    def test_pending_transfer_stages(self):
        """Standard transfer without destination signer emits through attestation stage."""
        events = []

        result = self.coordinator.execute_transfer(
            from_chain="arc",
            to_chain="stellar",
            amount="25",
            recipient="GBBD47IF6LWK7P7MDEVSCWR7DPUWV3NY3DTQEVFL4NAT4AQH3ZLLFLA5",
            burn_tx_hash="0xburn_pending",
            on_progress=lambda e: events.append(e),
            is_fast_or_assisted=False,
        )

        self.assertEqual(result["status"], "pending")
        self.assertIsNone(result["mintTxHash"])
        stages = [e["stage"] for e in events]
        self.assertEqual(
            stages,
            [
                "recipient-check",
                "approve",
                "burn-submitted",
                "burn-confirmed",
                "attestation",
            ],
        )


if __name__ == "__main__":
    unittest.main()
