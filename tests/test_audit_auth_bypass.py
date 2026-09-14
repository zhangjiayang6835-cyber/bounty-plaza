#!/usr/bin/env python3
"""
Fail-closed Victory Audit — planted auth_bypass (bounty-plaza #952).

Verifies the audit gate on a planted `auth_bypass` cheat (Pillar 2: auth):
  - planted cheat (commented-out require_auth / hard-coded bypass switch)
    -> auditor REQUEST_CHANGES, audit_status=FAIL, merge stays blocked
  - after the bypass is removed (fix commit) -> auditor APPROVE,
    audit_status=PASS only then

Runs under `python -m unittest` (stdlib) and `pytest`.
"""

import os
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(
    0,
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"),
)

import score

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


def read_fixture(name):
    with open(os.path.join(FIXTURES, name), encoding="utf-8") as f:
        return f.read()


class CheckAuthBypassTest(unittest.TestCase):
    def test_commented_out_require_auth_is_flagged(self):
        code = """
def handler(request):
    # require_auth(request)
    return "ok"
"""
        violations = score.check_auth_bypass(code)
        self.assertTrue(violations)
        self.assertIn("require_auth", violations[0])

    def test_whitespace_comment_variant_is_flagged(self):
        code = "def h(r):\n    #    require_auth (r)\n    return 1\n"
        violations = score.check_auth_bypass(code)
        self.assertTrue(violations)

    def test_auth_bypass_assignment_is_flagged(self):
        for code in ("auth_bypass = True\n", "auth_bypass=1\n", "bypass_auth = True\n", "skip_auth = 'true'\n"):
            violations = score.check_auth_bypass(code)
            self.assertTrue(violations, f"expected flag for: {code!r}")

    def test_falsy_bypass_assignment_not_flagged(self):
        self.assertEqual(score.check_auth_bypass("auth_bypass = False\n"), [])

    def test_active_require_auth_not_flagged(self):
        code = """
def handler(request):
    require_auth(request)
    return "ok"
"""
        self.assertEqual(score.check_auth_bypass(code), [])

    def test_clean_module_not_flagged(self):
        self.assertEqual(score.check_auth_bypass(read_fixture("victim_clean.py")), [])

    def test_planted_module_is_flagged(self):
        violations = score.check_auth_bypass(read_fixture("victim_planted.py"))
        self.assertGreaterEqual(len(violations), 2)


class AuditAuthBypassTest(unittest.TestCase):
    def test_fails_closed_on_planted_bypass(self):
        result = score.audit_auth_bypass(read_fixture("victim_planted.py"))
        self.assertEqual(result["audit_status"], "FAIL")
        self.assertTrue(result["cheating_detected"])
        self.assertTrue(result["violations"])

    def test_passes_after_bypass_removed(self):
        result = score.audit_auth_bypass(read_fixture("victim_clean.py"))
        self.assertEqual(result["audit_status"], "PASS")
        self.assertFalse(result["cheating_detected"])
        self.assertEqual(result["violations"], [])

    def test_direct_assignment_fails_closed(self):
        self.assertEqual(score.audit_auth_bypass("auth_bypass = True\n")["audit_status"], "FAIL")
        self.assertEqual(score.audit_auth_bypass("auth_bypass = False\n")["audit_status"], "PASS")


class EvaluateIntegrationTest(unittest.TestCase):
    """Full evaluate() path: planted cheat -> veto (score 0); fix -> PASS."""

    def _evaluate_fixture(self, name):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = os.path.join(tmpdir, "victim.py")
            with open(target, "w", encoding="utf-8") as f:
                f.write(read_fixture(name))
            with mock.patch("score.check_bandit", return_value=[]):
                return score.evaluate(target)

    def test_evaluate_fails_closed_on_planted_bypass(self):
        result = self._evaluate_fixture("victim_planted.py")
        self.assertTrue(result["cheating_detected"])
        self.assertEqual(result["score"], 0)
        self.assertFalse(result["passed"])
        self.assertTrue(
            any("auth_bypass" in v or "require_auth" in v for v in result["violations"])
        )

    def test_evaluate_passes_after_bypass_removed(self):
        with mock.patch("score.score_correctness", return_value=(40, "4/4 通过")), \
             mock.patch("score.score_quality", return_value=(15, "pylint: 10/10")), \
             mock.patch("score.score_performance", return_value=(10, "执行时间 0.01s")):
            result = self._evaluate_fixture("victim_clean.py")
        self.assertFalse(result["cheating_detected"])
        self.assertEqual(result["violations"], [])
        self.assertTrue(result["passed"])
        self.assertGreaterEqual(result["score"], score.PASS_THRESHOLD)


if __name__ == "__main__":
    unittest.main()