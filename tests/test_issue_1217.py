#!/usr/bin/env python3
"""
Regression test suite for Issue #1217:
Defensive parameter safeguards, boundary validation, and bounty reward calculation in scripts/coin.py.
"""

import io
import json
import math
import os
import sqlite3
import subprocess
import sys
import unittest
import shutil
import tempfile
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace

# Ensure scripts directory is on sys.path
SCRIPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts")
if SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, SCRIPTS_DIR)

import coin

TEST_TMPDIR = None
ORIGINAL_COIN_DB = None


def setUpModule():
    global TEST_TMPDIR, ORIGINAL_COIN_DB
    TEST_TMPDIR = tempfile.mkdtemp()
    test_db = os.path.join(TEST_TMPDIR, "coins.db")
    ORIGINAL_COIN_DB = coin.DB_PATH
    coin.DB_PATH = test_db
    os.environ["COIN_DB_PATH"] = test_db
    coin.init_db()


def tearDownModule():
    global TEST_TMPDIR, ORIGINAL_COIN_DB
    if ORIGINAL_COIN_DB:
        coin.DB_PATH = ORIGINAL_COIN_DB
    os.environ.pop("COIN_DB_PATH", None)
    if TEST_TMPDIR and os.path.exists(TEST_TMPDIR):
        shutil.rmtree(TEST_TMPDIR)


class TestBountyFunctionBoundaries(unittest.TestCase):
    """Verify that bounty() handles null, non-numeric, negative, and invalid boundary inputs safely."""

    def test_01_bounty_none_input(self):
        result = coin.bounty(None)
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result)
        self.assertEqual(result.get("bounty_usd"), 0.0)

    def test_02_bounty_empty_string(self):
        result = coin.bounty("")
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result)

    def test_03_bounty_invalid_string(self):
        result = coin.bounty("invalid_amount")
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result)

    def test_04_bounty_negative_and_zero(self):
        for val in (-100, -1, 0, -0.5):
            result = coin.bounty(val)
            self.assertIsInstance(result, dict)
            self.assertFalse(result.get("ok"))
            self.assertIn("error", result)

    def test_05_bounty_nan_and_inf(self):
        for val in (float("nan"), float("inf"), float("-inf")):
            result = coin.bounty(val)
            self.assertIsInstance(result, dict)
            self.assertFalse(result.get("ok"))

    def test_06_bounty_boolean_input(self):
        for val in (True, False):
            result = coin.bounty(val)
            self.assertIsInstance(result, dict)
            self.assertFalse(result.get("ok"))

    def test_07_bounty_no_args(self):
        result = coin.bounty()
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"))

    def test_08_bounty_below_min_threshold(self):
        result = coin.bounty(10)
        self.assertIsInstance(result, dict)
        self.assertFalse(result.get("ok"))
        self.assertIn("error", result)


class TestBountyCalculationContracts(unittest.TestCase):
    """Verify bounty calculations strictly match REWARD_POLICY.md and BOUNTY_CONFIG.json."""

    def test_tier_under_50(self):
        # $30: 30 * 1.25 = 37.5 coins, R=0.95 -> cash = 30 * 1.25 * 0.95 * 0.72 = 25.65
        res = coin.bounty(30)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("bounty_usd"), 30.0)
        self.assertEqual(res.get("r_ratio"), 0.95)
        self.assertAlmostEqual(res.get("cash_value"), 25.65, places=2)

    def test_tier_50_to_200(self):
        # $100: 100 * 1.25 = 125 coins, R=0.92, contributor_coins = 115, cash = 82.80
        res = coin.bounty(100)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("bounty_usd"), 100.0)
        self.assertEqual(res.get("coins"), 125)
        self.assertEqual(res.get("r_ratio"), 0.92)
        self.assertEqual(res.get("contributor_coins"), 115)
        self.assertAlmostEqual(res.get("cash_value"), 82.80, places=2)

    def test_tier_200_to_500(self):
        # $350: R=0.90 -> cash = 350 * 1.25 * 0.90 * 0.72 = 283.50
        res = coin.bounty(350)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("r_ratio"), 0.90)
        self.assertAlmostEqual(res.get("cash_value"), 283.50, places=2)

    def test_tier_500_to_1000(self):
        # $750: R=0.87 -> cash = 750 * 1.25 * 0.87 * 0.72 = 587.25
        res = coin.bounty(750)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("r_ratio"), 0.87)
        self.assertAlmostEqual(res.get("cash_value"), 587.25, places=2)

    def test_tier_1000_plus(self):
        # $2000: R=0.85 -> cash = 2000 * 1.25 * 0.85 * 0.72 = 1530.00
        res = coin.bounty(2000)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("r_ratio"), 0.85)
        self.assertAlmostEqual(res.get("cash_value"), 1530.00, places=2)

    def test_string_formatting_tolerance(self):
        # "$100" and "1,000" strings should be parsed safely
        res1 = coin.bounty("$100")
        self.assertTrue(res1.get("ok"))
        self.assertEqual(res1.get("bounty_usd"), 100.0)

        res2 = coin.bounty("$1,000")
        self.assertTrue(res2.get("ok"))
        self.assertEqual(res2.get("bounty_usd"), 1000.0)

    def test_issue_1217_specific_payload(self):
        # Issue #1217: $250 reward, 312 coins
        res = coin.bounty(250)
        self.assertTrue(res.get("ok"))
        self.assertEqual(res.get("bounty_usd"), 250.0)
        self.assertEqual(res.get("coins"), 312)
        self.assertEqual(res.get("r_ratio"), 0.90)
        self.assertEqual(res.get("contributor_coins"), 281)
        self.assertAlmostEqual(res.get("cash_value"), 202.50, places=2)


class TestCoinSystemDefensiveGuards(unittest.TestCase):
    """Verify defensive safeguards in other coin operations."""

    def test_compute_hash_safe_with_none_and_row(self):
        # Should not raise AttributeError on None
        h1 = coin.compute_hash(None)
        self.assertIsInstance(h1, str)
        self.assertEqual(len(h1), 64)

        # Should work with empty dict
        h2 = coin.compute_hash({})
        self.assertIsInstance(h2, str)
        self.assertEqual(len(h2), 64)

    def test_get_balance_safe_with_invalid_username(self):
        conn = coin.get_db()
        try:
            self.assertEqual(coin.get_balance(conn, None), 0)
            self.assertEqual(coin.get_balance(conn, ""), 0)
            self.assertEqual(coin.get_balance(conn, 12345), 0)
        finally:
            conn.close()

    def test_ensure_account_safe_with_invalid_username(self):
        conn = coin.get_db()
        try:
            # Should not raise or insert corrupt rows
            coin.ensure_account(conn, None)
            coin.ensure_account(conn, "")
            coin.ensure_account(conn, 123)
        finally:
            conn.close()

    def test_transfer_negative_or_zero_amount_rejected(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            args_neg = SimpleNamespace(from_user="admin", to_user="testuser", amount=-10, reason="test")
            self.assertEqual(coin.cmd_transfer(args_neg), 1)

            args_zero = SimpleNamespace(from_user="admin", to_user="testuser", amount=0, reason="test")
            self.assertEqual(coin.cmd_transfer(args_zero), 1)

    def test_transfer_self_rejected(self):
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            args_self = SimpleNamespace(from_user="admin", to_user="admin", amount=10, reason="test")
            self.assertEqual(coin.cmd_transfer(args_self), 1)

    def test_cmd_pay_approved_request_safe_row_access(self):
        # Verify that cmd_pay does not crash with AttributeError: 'sqlite3.Row' object has no attribute 'get'
        conn = coin.get_db()
        try:
            coin.ensure_account(conn, "pay_test_user")
            cur = conn.execute(
                "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES (?,?,?,?,'approved')",
                ("pay_test_user", 10, 7.20, "0x1234567890abcdef")
            )
            req_id = cur.lastrowid
            conn.commit()
        finally:
            conn.close()

        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(buf):
            args_pay = SimpleNamespace(id=req_id, json=True)
            ret = coin.cmd_pay(args_pay)
        self.assertEqual(ret, 0)

        # Verify status became paid
        conn = coin.get_db()
        try:
            row = conn.execute("SELECT status FROM redeem_requests WHERE id = ?", (req_id,)).fetchone()
            self.assertEqual(row["status"], "paid")
        finally:
            conn.close()


class TestCliBountyCommand(unittest.TestCase):
    """Verify CLI interface for coin.py bounty subcommand."""

    def test_cli_bounty_json_output(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "coin.py"), "bounty", "100", "--json"],
            capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("bounty_usd"), 100.0)
        self.assertAlmostEqual(data.get("cash_value"), 82.80, places=2)

    def test_cli_bounty_text_output(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "coin.py"), "bounty", "100"],
            capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        self.assertIn("赏金换算结果", proc.stdout)
        self.assertIn("100.00", proc.stdout)
        self.assertIn("82.80", proc.stdout)

    def test_cli_bounty_flag_amount(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "coin.py"), "bounty", "--amount", "250", "--json"],
            capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 0)
        data = json.loads(proc.stdout)
        self.assertTrue(data.get("ok"))
        self.assertEqual(data.get("bounty_usd"), 250.0)
        self.assertEqual(data.get("r_ratio"), 0.90)

    def test_cli_bounty_invalid_input(self):
        proc = subprocess.run(
            [sys.executable, os.path.join(SCRIPTS_DIR, "coin.py"), "bounty", "invalid"],
            capture_output=True, text=True
        )
        self.assertEqual(proc.returncode, 1)
        self.assertIn("ERROR", proc.stdout)


if __name__ == "__main__":
    unittest.main()
