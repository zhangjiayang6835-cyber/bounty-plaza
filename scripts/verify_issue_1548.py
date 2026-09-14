"""Verification script for Issue #1548: Enterprise Multi-Tenant SaaS Mode."""

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# pylint: disable=wrong-import-position
from packages.saas_mode.verifier import SaaSModeVerifier


def run_node_tests() -> bool:
    """Execute Node.js test suite for frontend / node runtime."""
    res = subprocess.run(
        ["node", "--test", "test/saas_mode.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and "pass 5" in res.stdout


def run_python_tests() -> bool:
    """Execute Pytest test suite for backend / python runtime."""
    res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_issue_1548.py", "-v"],
        capture_output=True,
        text=True,
        check=False,
    )
    return res.returncode == 0 and "17 passed" in res.stdout


def main() -> int:
    """Run all checks across runtimes and output invariant validation report."""
    print("=== SaaS Mode Verification Report (#1548) ===")

    node_ok = run_node_tests()
    print(f"[{'PASS' if node_ok else 'FAIL'}] Node.js runtime suite (test/saas_mode.test.js: 5/5 tests)")

    py_ok = run_python_tests()
    print(f"[{'PASS' if py_ok else 'FAIL'}] Pytest test suite (tests/test_issue_1548.py: 17/17 tests)")

    verifier = SaaSModeVerifier()
    results = verifier.verify_all_invariants()
    all_invariants_ok = results["all_passed"]
    print(f"[{'PASS' if all_invariants_ok else 'FAIL'}] Architectural invariants ({results['passed_checks']}/{results['total_checks']} verified)")

    for check_name, passed in results["details"].items():
        print(f"  - {check_name}: {'PASS' if passed else 'FAIL'}")

    all_passed = node_ok and py_ok and all_invariants_ok
    if all_passed:
        print("All verification checks passed successfully.")
        return 0

    print("One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
