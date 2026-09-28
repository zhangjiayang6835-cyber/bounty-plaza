"""
test_fee_ledger.py — Comprehensive Test Suite for Issue #1660
Verifies:
1. Exact confirmed network fee (fee_lamports) stored in database and ledger.
2. Conservative fee_micro ceiling calculation remains strictly untouched.
3. Forward-only database migration preserves existing rows.
4. Backward compatibility with legacy records and missing lamports parameters.
"""

import unittest
from src.fee_ledger import (
    lamports_to_micro_ceil,
    PayResult,
    SpendEntry,
    SpendLedgerDB,
    SOL_USD_CEILING_PRICE
)


class TestFeeLedger(unittest.TestCase):
    def test_lamports_to_micro_ceil(self):
        """Verify conservative ceiling price conversion: 5010 lamports at $400/SOL."""
        fee_micro = lamports_to_micro_ceil(5_010, sol_usd_price=400.0)
        self.assertEqual(fee_micro, 2_004)
        self.assertEqual(lamports_to_micro_ceil(1, sol_usd_price=400.0), 1)
        self.assertEqual(lamports_to_micro_ceil(0, sol_usd_price=400.0), 0)

    def test_forward_only_migration_safety(self):
        """Verify forward-only migration adds column without affecting existing rows."""
        db = SpendLedgerDB(":memory:")
        db.reserve("call-legacy-01", "P1", "inference", 15_000)
        db.settle("call-legacy-01", 15_000, 2_004, tx_signature="sig-legacy-01")

        legacy = db.get_entry("call-legacy-01")
        self.assertIsNotNone(legacy)
        self.assertEqual(legacy.fee_micro, 2_004)
        self.assertIsNone(legacy.fee_lamports)

        migrated = db.apply_migration_0011()
        self.assertTrue(migrated)

        migrated_again = db.apply_migration_0011()
        self.assertFalse(migrated_again)

        legacy_post = db.get_entry("call-legacy-01")
        self.assertIsNotNone(legacy_post)
        self.assertEqual(legacy_post.amount_micro, 15_000)
        self.assertEqual(legacy_post.fee_micro, 2_004)
        self.assertIsNone(legacy_post.fee_lamports)
        self.assertEqual(legacy_post.status, "settled")
        db.close()

    def test_settle_preserves_both_fee_lamports_and_fee_micro(self):
        """Verify factual fee_lamports stored side-by-side with conservative fee_micro."""
        db = SpendLedgerDB(":memory:")
        db.apply_migration_0011()
        db.reserve("call-tx-02", "P2", "inference", 20_000)
        settled = db.settle(
            entry_id="call-tx-02",
            amount_micro=18_000,
            fee_micro=2_004,
            fee_lamports=5_010,
            tx_signature="tx-sig-solana-confirmed-999"
        )
        self.assertEqual(settled.id, "call-tx-02")
        self.assertEqual(settled.amount_micro, 18_000)
        self.assertEqual(settled.fee_micro, 2_004)
        self.assertEqual(settled.fee_lamports, 5_010)
        self.assertEqual(settled.tx_signature, "tx-sig-solana-confirmed-999")
        self.assertEqual(settled.status, "settled")

        fetched = db.get_entry("call-tx-02")
        self.assertIsNotNone(fetched)
        self.assertEqual(fetched.fee_lamports, 5_010)
        self.assertEqual(fetched.fee_micro, 2_004)
        db.close()

    def test_fee_micro_invariance(self):
        """Verify fee_micro is identical whether fee_lamports is passed or omitted."""
        db = SpendLedgerDB(":memory:")
        db.apply_migration_0011()
        db.reserve("call-with-lamports", "P1", "inference", 10_000)
        e1 = db.settle("call-with-lamports", 10_000, fee_micro=2_004, fee_lamports=5_010)

        db.reserve("call-without-lamports", "P1", "inference", 10_000)
        e2 = db.settle("call-without-lamports", 10_000, fee_micro=2_004)

        self.assertEqual(e1.fee_micro, 2_004)
        self.assertEqual(e2.fee_micro, 2_004)
        self.assertEqual(e1.fee_lamports, 5_010)
        self.assertIsNone(e2.fee_lamports)
        db.close()

    def test_pay_result_dataclass(self):
        """Verify PayResult model properly accepts and retains fee_lamports."""
        res = PayResult(
            kind="paid",
            payer_wallet="HKMMpctYvofRCSF2uGnqfEGWcmMhD8A86xFqgmWTvcq9",
            signature="tx-sig-xyz",
            amount_micro=10_000,
            fee_micro=2_004,
            fee_lamports=5_010
        )
        self.assertEqual(res.fee_lamports, 5_010)
        self.assertEqual(res.fee_micro, 2_004)
        self.assertEqual(res.amount_micro, 10_000)


if __name__ == "__main__":
    unittest.main()

