"""Standalone verification script for Issue #1324.

Executes formal kinematic invariant verifier, Node.js test suite,
and Pytest suite to confirm continuous collision detection.
"""

import os
import subprocess
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from packages.kinematic_ccd.verifier import KinematicCcdVerifier


def main() -> int:
    """Runs complete end-to-end verification for Issue #1324."""
    print("=" * 60)
    print("Executing Kinematic CCD Formal Invariant Verifier...")
    print("=" * 60)
    report = KinematicCcdVerifier.run_all_checks()
    for detail in report.details:
        print(f"  [+] {detail}")

    if not report.all_passed:
        print("\n[-] Formal verification failed.")
        return 1

    print(f"\n[+] All {report.checks_run} formal invariant checks passed.")

    print("\n" + "=" * 60)
    print("Executing Node.js Swept AABB Test Suite...")
    print("=" * 60)
    node_res = subprocess.run(
        ["node", "--test", "test/swept_aabb.test.js"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    print(node_res.stdout)
    if node_res.returncode != 0:
        print(node_res.stderr)
        print("[-] Node.js test suite failed.")
        return 1

    print("=" * 60)
    print("Executing Pytest Verification Suite...")
    print("=" * 60)
    pytest_res = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_issue_1324.py", "-v"],
        cwd=_REPO_ROOT,
        capture_output=True,
        text=True,
    )
    print(pytest_res.stdout)
    if pytest_res.returncode != 0:
        print(pytest_res.stderr)
        print("[-] Pytest suite failed.")
        return 1

    print("=" * 60)
    print("VERIFICATION COMPLETE: Issue #1324 Fully Resolved (100% Invariants Verified)")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())
