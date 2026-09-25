#!/usr/bin/env python3
"""
Regression suite for Bounty Issue #1660:
"Record the real network fee in the ledger, not only the capped estimate"

Upstream semantics mapped onto scripts/coin.py:
  - fee_micro (capped estimate)  ->  redeem_requests.coin_value = amount * RATE  (UNCHANGED)
  - fee_lamports (real fee)      ->  new nullable fee_actual column, recorded at pay time
  - forward-only migration       ->  idempotent ALTER TABLE ADD COLUMN in init_db()

Run:
    python3 -m unittest tests/test_issue_1660.py
"""

import io
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from types import SimpleNamespace

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))

import coin  # noqa: E402


def run_cmd(func, **kwargs):
    """Invoke a coin.py command handler, capturing stdout. Must never raise."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc = func(SimpleNamespace(**kwargs))
    return rc, buf.getvalue()


class Issue1660Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="coin_issue_1660_")
        self._old_dir, self._old_path = coin.DB_DIR, coin.DB_PATH
        coin.DB_DIR = self.tmp
        coin.DB_PATH = os.path.join(self.tmp, "coins.db")
        coin.init_db()

    def tearDown(self):
        coin.DB_DIR, coin.DB_PATH = self._old_dir, self._old_path
        import shutil
        shutil.rmtree(self.tmp, ignore_errors=True)

    def seed_user(self, username="alice", balance=100):
        conn = coin.get_db()
        conn.execute("INSERT INTO accounts (username, balance) VALUES (?, ?)", (username, balance))
        conn.commit()
        conn.close()

    def make_approved_request(self, amount=10):
        """Drive the real redeem -> approve pipeline; returns request id."""
        rc, _ = run_cmd(coin.cmd_redeem, user="alice", amount=amount,
                        address="usdt:TTest123", auto=False, json=False, note="")
        self.assertEqual(rc, 0, "redeem should succeed")
        rc, out = run_cmd(coin.cmd_approve, id=1)
        self.assertEqual(rc, 0, f"approve should succeed, got: {out}")
        return 1

    def fetch_request(self, req_id=1):
        conn = coin.get_db()
        row = conn.execute("SELECT * FROM redeem_requests WHERE id = ?", (req_id,)).fetchone()
        conn.close()
        return row

    def fetch_tx(self, username="alice"):
        conn = coin.get_db()
        row = conn.execute(
            "SELECT * FROM transactions WHERE from_user = ? ORDER BY id DESC LIMIT 1",
            (username,)).fetchone()
        conn.close()
        return row


class Test01NormalFlow(Issue1660Base):
    """Standard flow: a paid redemption records the real fee next to the estimate."""

    def test_real_fee_recorded_beside_unchanged_estimate(self):
        self.seed_user()
        req_id = self.make_approved_request(amount=10)

        real_fee = 0.002004  # mirrors the issue's measured real network fee
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=real_fee, json=False, note="")
        self.assertEqual(rc, 0, f"pay with fee should succeed, got: {out}")

        req = self.fetch_request(req_id)
        self.assertEqual(req["status"], "paid")
        self.assertAlmostEqual(req["fee_actual"], real_fee, places=9)
        # capped estimate kept exactly as before: amount * RATE
        self.assertAlmostEqual(req["coin_value"], 10 * coin.RATE, places=9)

        tx = self.fetch_tx()
        self.assertIsNotNone(tx, "ledger transaction must exist")
        self.assertEqual(tx["status"], "completed")
        self.assertAlmostEqual(tx["fee_actual"], real_fee, places=9)

        # balance was deducted exactly once through the pipeline
        conn = coin.get_db()
        bal = conn.execute("SELECT balance FROM accounts WHERE username = 'alice'").fetchone()[0]
        conn.close()
        self.assertEqual(bal, 90)

    def test_pay_json_output_includes_fee_and_estimate(self):
        self.seed_user()
        req_id = self.make_approved_request(amount=5)
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=0.5, json=True, note="")
        self.assertEqual(rc, 0)
        import json
        payload = json.loads(out.strip().splitlines()[-1])
        self.assertTrue(payload["ok"])
        self.assertAlmostEqual(payload["fee_actual"], 0.5)
        self.assertAlmostEqual(payload["cash_value"], round(5 * coin.RATE, 2))


class Test02BoundaryHandling(Issue1660Base):
    """Null, negative, NaN and Inf fees must be handled gracefully — zero crashes."""

    def _new_approved(self):
        self.seed_user()
        return self.make_approved_request(amount=10)

    def test_negative_fee_rejected(self):
        req_id = self._new_approved()
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=-0.5, json=False, note="")
        self.assertEqual(rc, 1)
        self.assertIn("ERROR", out)
        self.assertEqual(self.fetch_request(req_id)["status"], "approved")  # unchanged

    def test_nan_fee_rejected(self):
        req_id = self._new_approved()
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=float("nan"), json=False, note="")
        self.assertEqual(rc, 1)
        self.assertIn("ERROR", out)
        self.assertEqual(self.fetch_request(req_id)["status"], "approved")

    def test_inf_fee_rejected(self):
        req_id = self._new_approved()
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=float("inf"), json=False, note="")
        self.assertEqual(rc, 1)
        self.assertIn("ERROR", out)
        self.assertEqual(self.fetch_request(req_id)["status"], "approved")

    def test_no_fee_still_works_and_stays_null(self):
        req_id = self._new_approved()
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=None, json=False, note="")
        self.assertEqual(rc, 0, f"pay without fee must keep working, got: {out}")
        self.assertIsNone(self.fetch_request(req_id)["fee_actual"])

    def test_zero_fee_is_valid(self):
        req_id = self._new_approved()
        rc, _ = run_cmd(coin.cmd_pay, id=req_id, fee=0.0, json=False, note="")
        self.assertEqual(rc, 0)
        self.assertEqual(self.fetch_request(req_id)["fee_actual"], 0.0)


class Test03ContractIntegrity(Issue1660Base):
    """Type-safe guards and graceful failures on invalid references/inputs."""

    def test_validate_fee_contract(self):
        self.assertIsNone(coin.validate_fee(None))
        self.assertIsNone(coin.validate_fee(0))
        self.assertIsNone(coin.validate_fee(0.002004))
        self.assertIsNotNone(coin.validate_fee("0.5"))     # wrong type
        self.assertIsNotNone(coin.validate_fee(True))      # bool is not a fee
        self.assertIsNotNone(coin.validate_fee(-1))        # negative
        self.assertIsNotNone(coin.validate_fee(float("nan")))
        self.assertIsNotNone(coin.validate_fee(float("inf")))

    def test_pay_nonexistent_request_graceful(self):
        rc, out = run_cmd(coin.cmd_pay, id=999, fee=0.1, json=False, note="")
        self.assertEqual(rc, 1)
        self.assertIn("ERROR", out)

    def test_pay_already_paid_request_graceful(self):
        self.seed_user()
        req_id = self.make_approved_request(amount=10)
        rc, _ = run_cmd(coin.cmd_pay, id=req_id, fee=0.1, json=False, note="")
        self.assertEqual(rc, 0)
        rc, out = run_cmd(coin.cmd_pay, id=req_id, fee=0.2, json=False, note="")
        self.assertEqual(rc, 1)  # no double-processing, no crash
        self.assertIn("ERROR", out)
        # original fee must not be overwritten by the rejected second pay
        self.assertAlmostEqual(self.fetch_request(req_id)["fee_actual"], 0.1, places=9)

    def test_approve_nonexistent_graceful(self):
        rc, out = run_cmd(coin.cmd_approve, id=999)
        self.assertEqual(rc, 1)
        self.assertIn("ERROR", out)

    def test_redeem_boundary_amounts_graceful(self):
        self.seed_user()
        for bad in (0, -5):
            rc, out = run_cmd(coin.cmd_redeem, user="alice", amount=bad,
                              address="usdt:TTest123", auto=False, json=False, note="")
            self.assertEqual(rc, 1, f"amount={bad} must be rejected")
            self.assertIn("ERROR", out)


class Test04IntegrationConsistency(Issue1660Base):
    """Forward-only migration: existing rows untouched; estimate math unchanged."""

    LEGACY_SCHEMA = """
        CREATE TABLE transactions (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            tx_type     TEXT NOT NULL,
            from_user   TEXT,
            to_user     TEXT,
            amount      INTEGER NOT NULL,
            reason      TEXT,
            ref_id      TEXT,
            prev_hash   TEXT NOT NULL,
            hash        TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'completed',
            created_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
        CREATE TABLE redeem_requests (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            username    TEXT NOT NULL,
            amount      INTEGER NOT NULL,
            coin_value  REAL NOT NULL,
            address     TEXT NOT NULL,
            status      TEXT NOT NULL DEFAULT 'pending',
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
        );
    """

    def test_migration_is_forward_only_and_preserves_rows(self):
        # Build a legacy (pre-#1660) database without fee_actual columns
        legacy_path = os.path.join(self.tmp, "legacy.db")
        raw = sqlite3.connect(legacy_path)
        raw.executescript(self.LEGACY_SCHEMA)
        raw.execute(
            "INSERT INTO redeem_requests (username, amount, coin_value, address, status) "
            "VALUES ('bob', 7, ?, 'paypal:bob@x.com', 'paid')", (7 * 0.72,))
        raw.commit()
        raw.close()

        coin.DB_PATH = legacy_path
        coin.init_db()
        coin.init_db()  # idempotent: running the migration twice must not fail

        conn = coin.get_db()
        req_cols = {r["name"] for r in conn.execute("PRAGMA table_info(redeem_requests)")}
        tx_cols = {r["name"] for r in conn.execute("PRAGMA table_info(transactions)")}
        self.assertIn("fee_actual", req_cols)
        self.assertIn("fee_actual", tx_cols)

        row = conn.execute("SELECT * FROM redeem_requests WHERE username = 'bob'").fetchone()
        conn.close()
        self.assertIsNotNone(row, "existing rows must survive migration")
        self.assertIsNone(row["fee_actual"], "existing rows stay NULL and valid")
        self.assertEqual(row["status"], "paid")
        self.assertAlmostEqual(row["coin_value"], 7 * 0.72, places=9)

    def test_capped_estimate_unchanged_for_same_input(self):
        # The conservative estimate must be bit-identical before/after the change:
        # RATE untouched, coin_value = amount * RATE.
        self.assertEqual(coin.RATE, 0.72)
        self.assertAlmostEqual(10 * coin.RATE, 7.2, places=9)

        self.seed_user()
        rc, _ = run_cmd(coin.cmd_redeem, user="alice", amount=10,
                        address="usdt:TTest123", auto=False, json=False, note="")
        self.assertEqual(rc, 0)
        req = self.fetch_request(1)
        self.assertAlmostEqual(req["coin_value"], 7.2, places=9)
        self.assertIsNone(req["fee_actual"])  # fee unknown until pay time

    def test_full_pipeline_history_shows_fee(self):
        self.seed_user()
        req_id = self.make_approved_request(amount=10)
        rc, _ = run_cmd(coin.cmd_pay, id=req_id, fee=0.002004, json=False, note="")
        self.assertEqual(rc, 0)
        rc, out = run_cmd(coin.cmd_history)
        self.assertEqual(rc, 0)
        self.assertIn("0.002004", out)  # real fee visible in ledger report


if __name__ == "__main__":
    unittest.main()
