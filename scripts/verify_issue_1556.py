#!/usr/bin/env python3
"""Automated verifier for Issue #1556: EvilGuard autonomous agent defense."""

import os
import subprocess
import sys
from pathlib import Path


def run_cmd(cmd: list[str], description: str) -> bool:
    """Execute process and report status."""
    print(f"\n[RUNNING] {description}...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"[PASS] {description}")
        return True
    print(f"[FAIL] {description}")
    print(result.stdout)
    print(result.stderr)
    return False


def main() -> int:
    """Execute complete end-to-end verification pipeline."""
    repo_root = Path(__file__).resolve().parent.parent
    os.chdir(repo_root)

    print("==================================================")
    print("Verification Pipeline: Issue #1556 (EvilGuard)")
    print("==================================================")

    steps = [
        ([sys.executable, "-m", "pytest", "tests/test_issue_1556.py", "-v"], "Python Pytest Suite"),
        (["node", "--test", "test/evil_guard.test.js"], "Node.js Unit Suite"),
        ([sys.executable, "-m", "pylint", "packages/evil_guard/"], "Pylint Static Analysis (10.0/10)"),
        ([sys.executable, "-m", "bandit", "-r", "packages/evil_guard/"], "Bandit Security Vulnerability Scanner"),
        ([sys.executable, "scripts/score.py", "--code", "packages/evil_guard/manager.py", "--tests", "tests"], "Official Score Harness (scripts/score.py)"),
    ]

    all_passed = True
    for cmd, desc in steps:
        if not run_cmd(cmd, desc):
            all_passed = False

    print("\n==================================================")
    if all_passed:
        print("ALL VERIFICATION CHECKS PASSED: 100/100 READY")
        print("==================================================")
        return 0

    print("VERIFICATION FAILED")
    print("==================================================")
    return 1


if __name__ == "__main__":
    sys.exit(main())
