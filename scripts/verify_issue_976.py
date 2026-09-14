"""Verification script for Issue #976 solution."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_command(command: list[str], description: str) -> bool:
    """Execute a command and report status.

    Parameters:
        command: List of command arguments.
        description: Description of the verification step.

    Returns:
        True if the command succeeded, False otherwise.
    """
    print(f"--> Running: {description}")
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    if result.returncode == 0:
        print(f"    [PASS] {description}")
        return True
    print(f"    [FAIL] {description}")
    print(f"STDOUT:\n{result.stdout}")
    print(f"STDERR:\n{result.stderr}")
    return False


def main() -> int:
    """Run all verification checks for issue 976.

    Returns:
        0 if all checks pass, 1 otherwise.
    """
    root = Path(__file__).resolve().parent.parent

    steps = [
        (
            [sys.executable, "-m", "pytest", str(root / "tests"), "-v"],
            "Pytest Suite Execution",
        ),
        (
            [sys.executable, "-m", "pylint", str(root / "src" / "math_utils.py")],
            "Pylint Static Analysis on src/math_utils.py",
        ),
        (
            [
                sys.executable,
                "-m",
                "bandit",
                "-q",
                "-f",
                "json",
                str(root / "src" / "math_utils.py"),
            ],
            "Bandit Security Scan on src/math_utils.py",
        ),
        (
            [
                sys.executable,
                str(root / "scripts" / "score.py"),
                "--code",
                str(root / "src" / "math_utils.py"),
                "--tests",
                str(root / "tests"),
            ],
            "Bounty Plaza Official Scoring System",
        ),
    ]

    all_passed = True
    for cmd, desc in steps:
        if not run_command(cmd, desc):
            all_passed = False

    if all_passed:
        print("\nAll verification steps completed successfully.")
        return 0

    print("\nOne or more verification steps failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
