"""Comprehensive verification script for Issue #1233 solution package."""

import subprocess
import sys


def run_node_tests() -> bool:
    """Run Node.js kinematics test suite."""
    print("Running Node.js Kinematics Test Suite...")
    result = subprocess.run(
        ["node", "--test", "tests/kinematics.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False
    return True


def run_python_scoring() -> bool:
    """Run Bounty Plaza score evaluation harness."""
    print("Running Python Scoring Harness (scripts/score.py)...")
    cmd = [
        sys.executable,
        "scripts/score.py",
        "--code",
        "packages/kinematics_solver/rk4_integrator.py",
        "--tests",
        "tests/test_issue_1233.py",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    print(result.stdout)
    if result.returncode != 0:
        print(result.stderr, file=sys.stderr)
        return False
    return "总分: 100/100" in result.stdout


def main() -> int:
    """Execute complete validation suite across Node.js and Python implementations."""
    node_ok = run_node_tests()
    python_ok = run_python_scoring()

    if node_ok and python_ok:
        print("Issue #1233 Verification: ALL SUITES PASSED (100/100)")
        return 0

    print("Issue #1233 Verification: FAILED", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
