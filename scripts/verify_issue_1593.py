"""Unified verification harness for Issue #1593 deliverables."""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> None:
    """Execute a verification command and abort on failure."""
    sys.stdout.write(f"\n--- Running: {description} ---\n")
    result = subprocess.run(cmd, capture_output=False, text=True)
    if result.returncode != 0:
        sys.stderr.write(f"Verification step failed: {description} (exit code: {result.returncode})\n")
        sys.exit(result.returncode)


def main() -> None:
    """Run all quality, security, and runtime suites."""
    python_bin = sys.executable or "python3"

    run_command(
        [python_bin, "-m", "pytest", "tests/test_issue_1593.py", "-v"],
        "Pytest Suite for omni_backflip",
    )

    run_command(
        ["node", "test/omni_backflip.test.js"],
        "Node.js Parity Suite for omni_backflip.js",
    )

    run_command(
        [python_bin, "-m", "bandit", "-r", "packages/omni_backflip"],
        "Bandit Static Security Audit",
    )

    run_command(
        [python_bin, "-m", "pylint", "packages/omni_backflip"],
        "Pylint 10.00/10 Quality Audit",
    )

    run_command(
        [
            python_bin,
            "scripts/score.py",
            "--code",
            "packages/omni_backflip/backflip_gateway.py",
            "--tests",
            "tests",
        ],
        "Bounty Plaza Official Scoring Harness",
    )

    sys.stdout.write("\n==================================================\n")
    sys.stdout.write("ALL ISSUE #1593 VERIFICATIONS PASSED SUCCESSFULLY!\n")
    sys.stdout.write("==================================================\n")


if __name__ == "__main__":
    main()
