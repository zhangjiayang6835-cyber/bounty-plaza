"""Unified verification harness for Issue #1589 deliverables."""

import subprocess
import sys


def run_command(cmd: list[str], description: str) -> None:
    """Execute a verification command and abort on failure."""
    sys.stdout.write(f"\n--- Running: {description} ---\n")
    result = subprocess.run(cmd, capture_output=False, text=True, check=False)
    if result.returncode != 0:
        sys.stderr.write(
            f"Verification step failed: {description} (exit code: {result.returncode})\n"
        )
        sys.exit(result.returncode)


def main() -> None:
    """Run all quality, security, and runtime suites."""
    python_bin = sys.executable or "python3"

    run_command(
        [python_bin, "-m", "pytest", "tests/test_issue_1589.py", "-v"],
        "Pytest Suite for tt_distributed_norm",
    )

    run_command(
        [python_bin, "-m", "bandit", "-r", "packages/tt_distributed_norm"],
        "Bandit Static Security Audit",
    )

    run_command(
        [python_bin, "-m", "pylint", "packages/tt_distributed_norm"],
        "Pylint 10.00/10 Quality Audit",
    )

    run_command(
        [
            python_bin,
            "scripts/score.py",
            "--code",
            "packages/tt_distributed_norm/stride_engine.py",
            "--tests",
            "tests",
        ],
        "Bounty Plaza Official Scoring Harness",
    )

    sys.stdout.write("\n==================================================\n")
    sys.stdout.write("ALL ISSUE #1589 VERIFICATIONS PASSED SUCCESSFULLY!\n")
    sys.stdout.write("==================================================\n")


if __name__ == "__main__":
    main()
