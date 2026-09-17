"""
Automated verification harness for Issue #1575 OmniUniverse implementation.
"""

import subprocess
import sys


def run_check(label: str, cmd: list[str]) -> bool:
    """Execute validation command and report exit status."""
    print(f"\n--- Running: {label} ---")
    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"FAILED: {label} (exit code: {result.returncode})")
        return False
    print(f"PASSED: {label}")
    return True


def main() -> int:
    """Orchestrate all verification checks."""
    py_bin = sys.executable or "python3"

    checks = [
        ("Python Test Suite", [py_bin, "-m", "pytest", "tests/test_issue_1575.py", "-v"]),
        ("Node.js Test Suite", ["node", "test/omni_universe.test.js"]),
        ("Bandit Security Scan", [py_bin, "-m", "bandit", "-r", "packages/omni_universe"]),
        ("Pylint Quality Analysis", [py_bin, "-m", "pylint", "packages/omni_universe"]),
        (
            "Evaluation Scoring Script",
            [py_bin, "scripts/score.py", "--code", "packages/omni_universe/universe_gateway.py", "--tests", "tests"],
        ),
    ]

    all_passed = True
    for label, cmd in checks:
        success = run_check(label, cmd)
        if not success:
            all_passed = False
            break

    if all_passed:
        print("\nAll verification checks completed successfully.")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
