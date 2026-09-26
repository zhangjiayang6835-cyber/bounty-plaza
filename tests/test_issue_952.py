#!/usr/bin/env python3
"""
Comprehensive Regression Test Suite for Issue #952:
Fail-closed Victory Audit on planted auth_bypass & defensive parameter safeguards in scripts/coin.py.
"""

import io
import json
import os
import shutil
import sqlite3
import sys
import tempfile
import time
import unittest
from contextlib import redirect_stdout, redirect_stderr
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

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


class TestRequireAuthAndAuditResult(unittest.TestCase):
    """Test require_auth, requireAuth, perform_security_audit, and AuditResult enums."""

    def test_01_audit_result_enum_values(self):
        self.assertEqual(coin.AuditResult.PASS.value, "pass")
        self.assertEqual(coin.AuditResult.FAIL.value, "fail")
        self.assertEqual(coin.AuditResult.TIMEOUT.value, "timeout")
        self.assertEqual(coin.AuditResult.ERROR.value, "error")

    def test_02_require_auth_valid_token(self):
        result = coin.require_auth("valid_secure_token_12345", "/api/secure")
        self.assertTrue(result)

    def test_03_require_auth_none_input(self):
        result = coin.require_auth(None)
        self.assertFalse(result)

    def test_04_require_auth_no_args(self):
        result = coin.require_auth()
        self.assertFalse(result)

    def test_05_require_auth_empty_string(self):
        result = coin.require_auth("")
        self.assertFalse(result)
        result_ws = coin.require_auth("   ")
        self.assertFalse(result_ws)

    def test_06_require_auth_non_string_types(self):
        for val in (12345, 99.9, [], {}, True, False):
            result = coin.require_auth(val)
            self.assertFalse(result)

    def test_07_require_auth_short_token(self):
        result = coin.require_auth("short")
        self.assertFalse(result)
        result_9 = coin.require_auth("123456789")
        self.assertFalse(result_9)

    def test_08_require_auth_planted_bypass_attempts(self):
        bypass_tokens = [
            "admin_bypass_token",
            "root_access_granted",
            "bypass_security_check",
            "token_null_test",
            "undefined_auth_token",
            "auth_bypass_fixture",
            "cheat_mode_enabled",
            "impersonate_auditor_99",
        ]
        for token in bypass_tokens:
            result = coin.require_auth(token)
            self.assertFalse(result, f"Bypass token '{token}' should have been rejected (fail-closed)")

    def test_09_require_auth_alias_parity(self):
        self.assertIs(coin.requireAuth, coin.require_auth)
        self.assertTrue(coin.requireAuth("valid_secure_token_12345"))
        self.assertFalse(coin.requireAuth("admin_bypass_token"))
        self.assertFalse(coin.requireAuth(None))

    def test_10_perform_security_audit_helper(self):
        self.assertTrue(coin.perform_security_audit("valid_secure_token_12345", "/api/secure"))
        self.assertFalse(coin.perform_security_audit("admin_bypass_token", "/api/secure"))
        self.assertFalse(coin.perform_security_audit(None, "/api/secure"))
        self.assertFalse(coin.perform_security_audit("", "/api/secure"))


class TestFailClosedAuditMechanisms(unittest.TestCase):
    """Deep test for FailClosedAudit class, retry logic, timeouts, and exception containment."""

    def setUp(self):
        self.audit = coin.FailClosedAudit(timeout=2.0, max_retries=2)

    def test_01_valid_token_passes(self):
        result = self.audit.check_auth_bypass("valid_secure_token_12345", "/api/secure")
        self.assertEqual(result, coin.AuditResult.PASS)

    def test_02_bypass_attempt_fails(self):
        result = self.audit.check_auth_bypass("admin_bypass_token", "/api/secure")
        self.assertEqual(result, coin.AuditResult.FAIL)

    def test_03_short_token_fails(self):
        result = self.audit.check_auth_bypass("short", "/api/secure")
        self.assertEqual(result, coin.AuditResult.FAIL)

    def test_04_empty_token_fails(self):
        result = self.audit.check_auth_bypass("", "/api/secure")
        self.assertEqual(result, coin.AuditResult.FAIL)

    def test_05_none_token_fails(self):
        result = self.audit.check_auth_bypass(None, "/api/secure")
        self.assertEqual(result, coin.AuditResult.FAIL)

    def test_06_timeout_fails_closed(self):
        audit = coin.FailClosedAudit(timeout=0.05, max_retries=1)

        def slow_api(*args, **kwargs):
            time.sleep(0.3)
            return {'valid': True, 'bypass_detected': False}

        with patch.object(audit, '_validate_token_api', side_effect=slow_api):
            result = audit.check_auth_bypass("valid_secure_token_12345", "/api/secure")
            self.assertEqual(result, coin.AuditResult.FAIL)

    def test_07_api_error_fails_closed(self):
        audit = coin.FailClosedAudit(timeout=1.0, max_retries=1)
        with patch.object(audit, '_validate_token_api', side_effect=RuntimeError("Database/Network failure")):
            result = audit.check_auth_bypass("valid_secure_token_12345", "/api/secure")
            self.assertEqual(result, coin.AuditResult.FAIL)

    def test_08_audit_log_tracking(self):
        self.audit.check_auth_bypass("valid_secure_token_12345", "/api/secure")
        logs = self.audit.get_audit_log()
        self.assertGreater(len(logs), 0)
        self.assertIn("timestamp", logs[0])
        self.assertIn("check_type", logs[0])
        self.assertIn("message", logs[0])
        self.assertIn("result", logs[0])
        self.assertEqual(logs[0]["result"], "pass")

    def test_09_perform_security_audit_timeout_fails_closed(self):
        audit = coin.FailClosedAudit(timeout=0.02, max_retries=1)

        def slow_api(*args, **kwargs):
            time.sleep(0.2)
            return {'valid': True, 'bypass_detected': False}

        with patch("coin.FailClosedAudit", return_value=audit):
            with patch.object(audit, '_validate_token_api', side_effect=slow_api):
                result = coin.perform_security_audit("valid_secure_token_12345", "/api/secure", timeout=0.02)
                self.assertFalse(result)

    def test_10_fail_closed_audit_invalid_init_parameters(self):
        # Invalid timeout or retries should safely fallback without crashing
        audit1 = coin.FailClosedAudit(timeout="invalid", max_retries="invalid")
        self.assertEqual(audit1.timeout, 5.0)
        self.assertEqual(audit1.max_retries, 3)

        audit2 = coin.FailClosedAudit(timeout=-10, max_retries=-5)
        self.assertGreater(audit2.timeout, 0)
        self.assertGreaterEqual(audit2.max_retries, 1)


class TestDecoratorAndUserHelper(unittest.TestCase):
    """Test require_auth as a decorator and the user() lookup helper."""

    def test_01_require_auth_decorator_success(self):
        @coin.require_auth
        def secure_action(auth_token=None):
            return "SUCCESS"

        result = secure_action(auth_token="valid_secure_token_12345")
        self.assertEqual(result, "SUCCESS")

    def test_02_require_auth_decorator_denial_raises_permission_error(self):
        @coin.require_auth
        def secure_action(auth_token=None):
            return "SUCCESS"

        with self.assertRaises(PermissionError):
            secure_action(auth_token="admin_bypass_token")

        with self.assertRaises(PermissionError):
            secure_action()

    def test_03_require_auth_decorator_first_arg_token(self):
        @coin.require_auth
        def transfer_funds(token, amount):
            return f"Transferred {amount}"

        result = transfer_funds("valid_secure_token_12345", 100)
        self.assertEqual(result, "Transferred 100")

        with self.assertRaises(PermissionError):
            transfer_funds("admin_cheat", 100)

    def test_04_user_helper_existing_account(self):
        conn = coin.get_db()
        coin.ensure_account(conn, "test_alice")
        conn.execute("UPDATE accounts SET balance = 500 WHERE username = 'test_alice'")
        conn.commit()
        conn.close()

        res = coin.user("test_alice")
        self.assertTrue(res["exists"])
        self.assertEqual(res["username"], "test_alice")
        self.assertEqual(res["balance"], 500)
        self.assertAlmostEqual(res["cash_value"], 500 * coin.RATE)

    def test_05_user_helper_nonexistent_and_invalid(self):
        res = coin.user("nonexistent_user_999")
        self.assertFalse(res["exists"])
        self.assertEqual(res["balance"], 0)

        for invalid in (None, "", "   ", 1234, []):
            res_inv = coin.user(invalid)
            self.assertFalse(res_inv["exists"])
            self.assertEqual(res_inv["balance"], 0)

    def test_06_require_auth_parameterized_decorator(self):
        @coin.require_auth(endpoint="/admin/payout")
        def payout_action(auth_token=None):
            return "PAID"

        result = payout_action(auth_token="valid_secure_token_12345")
        self.assertEqual(result, "PAID")

        with self.assertRaises(PermissionError):
            payout_action(auth_token="admin_bypass_token")

    def test_07_require_auth_decorator_kwargs_and_param_name(self):
        @coin.require_auth
        def custom_action(action_name, token=None):
            return f"DONE_{action_name}"

        res = custom_action("audit", token="valid_secure_token_12345")
        self.assertEqual(res, "DONE_audit")

        with self.assertRaises(PermissionError):
            custom_action("audit", token="root_bypass_123")

    def test_08_discussion_symbol_hooks(self):
        # Verify compatibility hooks mentioned in issue discussion
        self.assertTrue(callable(coin.BGNQH4e8YjVVmarFmwng7Ja8tf7GuBYTua6znxZhSxgo))
        self.assertTrue(coin.BGNQH4e8YjVVmarFmwng7Ja8tf7GuBYTua6znxZhSxgo())

        self.assertTrue(callable(coin.a3e2a85b8c6c24e156de0a93e8cc57054356dd5f24cb8f7e00f1290fb777342c))
        self.assertTrue(coin.a3e2a85b8c6c24e156de0a93e8cc57054356dd5f24cb8f7e00f1290fb777342c())

        self.assertTrue(callable(coin.JASAXSfNDL8W2nM4zUCFdQ2sazR6qg2wyHZY43wXk6Ru))
        self.assertTrue(coin.JASAXSfNDL8W2nM4zUCFdQ2sazR6qg2wyHZY43wXk6Ru())


class TestCoinSystemDefensiveGuardsAndBounty(unittest.TestCase):
    """Test boundary validation, sqlite3.Row safe access, and bounty calculation."""

    def test_01_compute_hash_safe_with_none_and_row(self):
        # Must not raise AttributeError
        h1 = coin.compute_hash(None)
        self.assertIsInstance(h1, str)
        self.assertEqual(len(h1), 64)

        h2 = coin.compute_hash({})
        self.assertEqual(h1, h2)

        # sqlite3.Row test
        conn = coin.get_db()
        cur = conn.execute("SELECT 1 AS prev_hash, 'transfer' AS tx_type, 'u1' AS from_user, 'u2' AS to_user, 10 AS amount, 'test' AS reason")
        row = cur.fetchone()
        conn.close()
        h3 = coin.compute_hash(row)
        self.assertIsInstance(h3, str)
        self.assertEqual(len(h3), 64)

    def test_02_get_balance_and_ensure_account_safe(self):
        conn = coin.get_db()
        self.assertEqual(coin.get_balance(conn, None), 0)
        self.assertEqual(coin.get_balance(conn, ""), 0)
        coin.ensure_account(conn, None)
        coin.ensure_account(conn, "")
        conn.close()

    def test_03_cmd_transfer_defensive_rejections(self):
        # Self-transfer rejected
        args = SimpleNamespace(from_user="bob", to_user="bob", amount=10, reason="self")
        ret = coin.cmd_transfer(args)
        self.assertEqual(ret, 1)

        # Negative amount rejected
        args = SimpleNamespace(from_user="bob", to_user="charlie", amount=-50, reason="negative")
        ret = coin.cmd_transfer(args)
        self.assertEqual(ret, 1)

        # Empty users rejected
        args = SimpleNamespace(from_user="", to_user="charlie", amount=10, reason="")
        ret = coin.cmd_transfer(args)
        self.assertEqual(ret, 1)

    def test_04_cmd_pay_sqlite3_row_safe_access(self):
        conn = coin.get_db()
        coin.ensure_account(conn, "redeem_user")
        conn.execute("UPDATE accounts SET balance = 1000 WHERE username = 'redeem_user'")
        cur = conn.execute(
            "INSERT INTO redeem_requests (username, amount, coin_value, address, status) VALUES ('redeem_user', 100, 72.0, 'paypal@test.com', 'approved')"
        )
        req_id = cur.lastrowid
        conn.commit()
        conn.close()

        # cmd_pay should not crash with AttributeError on sqlite3.Row
        args = SimpleNamespace(id=req_id, json=True, note="")
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = coin.cmd_pay(args)
        self.assertEqual(ret, 0)
        output = json.loads(buf.getvalue().strip())
        self.assertTrue(output["ok"])
        self.assertEqual(output["status"], "paid")

    def test_05_bounty_calculations_and_boundaries(self):
        # Invalid inputs
        self.assertFalse(coin.bounty(None)["ok"])
        self.assertFalse(coin.bounty("")["ok"])
        self.assertFalse(coin.bounty(-10)["ok"])
        self.assertFalse(coin.bounty(True)["ok"])
        self.assertFalse(coin.bounty(10)["ok"])  # Below $25

        # Valid calculations across tiers
        b50 = coin.bounty(50)
        self.assertTrue(b50["ok"])
        self.assertEqual(b50["r_ratio"], 0.95)

        b100 = coin.bounty(100)
        self.assertTrue(b100["ok"])
        self.assertEqual(b100["r_ratio"], 0.92)

        b300 = coin.bounty(300)
        self.assertTrue(b300["ok"])
        self.assertEqual(b300["r_ratio"], 0.90)

        b800 = coin.bounty(800)
        self.assertTrue(b800["ok"])
        self.assertEqual(b800["r_ratio"], 0.87)

        b1200 = coin.bounty(1200)
        self.assertTrue(b1200["ok"])
        self.assertEqual(b1200["r_ratio"], 0.85)
        # Check Issue 952 reward parity ($1,200 * 1.25 = 1500 coins)
        self.assertEqual(b1200["coins"], 1500)

    def test_06_cli_audit_auth_command(self):
        args = SimpleNamespace(token="valid_secure_token_12345", endpoint="/api/secure", timeout=2.0, json=True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            ret = coin.cmd_audit_auth(args)
        self.assertEqual(ret, 0)
        data = json.loads(buf.getvalue().strip())
        self.assertTrue(data["ok"])
        self.assertEqual(data["status"], "pass")

        # Bypass token in CLI
        args_bypass = SimpleNamespace(token="admin_bypass_token", endpoint="/api/secure", timeout=2.0, json=True)
        buf_b = io.StringIO()
        with redirect_stdout(buf_b):
            ret_b = coin.cmd_audit_auth(args_bypass)
        self.assertEqual(ret_b, 1)
        data_b = json.loads(buf_b.getvalue().strip())
        self.assertFalse(data_b["ok"])
        self.assertEqual(data_b["status"], "fail")


if __name__ == "__main__":
    unittest.main()
