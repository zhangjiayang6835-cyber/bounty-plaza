"""Comprehensive standalone verification script for Issue #1303."""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: list[str], description: str) -> bool:
    """Executes an external command and validates exit code.

    Args:
        cmd: Command arguments to execute.
        description: Readable description of the command.

    Returns:
        True if command succeeded with exit code 0.
    """
    sys.stdout.write(f"==> Running: {description}\n")
    sys.stdout.flush()
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{REPO_ROOT}:{env.get('PYTHONPATH', '')}"
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )
    if result.returncode != 0:
        sys.stderr.write(f"FAILED: {description}\n{result.stderr}\n{result.stdout}\n")
        return False
    sys.stdout.write(f"PASSED: {description}\n")
    return True


def main() -> int:
    """Main verification orchestrator.

    Returns:
        0 if all test suites and verifications pass, 1 otherwise.
    """
    verifications = [
        (
            [sys.executable, "-m", "pytest", "tests/test_issue_1303.py", "-v"],
            "Pytest Test Suite",
        ),
        (["forge", "test"], "Foundry Test Suite"),
        (["npx", "hardhat", "test"], "Hardhat Test Suite"),
        (
            [
                sys.executable,
                "-c",
                (
                    "from packages.flash_loan_vault import FlashLoanFormalVerifier; "
                    "assert FlashLoanFormalVerifier.run_all_verifications()['all_passed']"
                ),
            ],
            "Mathematical Formal Verifier",
        ),
    ]

    for cmd, desc in verifications:
        if not run_command(cmd, desc):
            return 1

    sys.stdout.write("\nAll verifications for Issue #1303 passed successfully.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
