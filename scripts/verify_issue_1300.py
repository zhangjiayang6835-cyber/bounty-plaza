"""Comprehensive standalone verification runner for Issue #1300."""

import os
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def run_command(cmd: list[str], description: str) -> bool:
    """Executes an external command and validates exit code.

    Args:
        cmd: Command arguments to execute.
        description: Human-readable description of the command.

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
            [sys.executable, "-m", "pytest", "tests/test_issue_1300.py", "-v"],
            "Pytest Integration Test Suite",
        ),
        (
            ["cargo", "test"],
            "Solana Anchor Rust Unit and Integration Test Suite",
        ),
        (
            [
                sys.executable,
                "-c",
                (
                    "from packages.staking_reward_engine import StakingRewardFormalVerifier; "
                    "results = StakingRewardFormalVerifier().verify_all(); "
                    "assert all(results.values()) and len(results) == 8"
                ),
            ],
            "Mathematical Formal Invariant Verifier",
        ),
        (
            [
                sys.executable,
                "scripts/score.py",
                "--code",
                "packages/staking_reward_engine/pool.py",
                "--tests",
                "tests/test_issue_1300.py",
            ],
            "Quality and Security Scoring Suite (Pool Engine)",
        ),
        (
            [
                sys.executable,
                "scripts/score.py",
                "--code",
                "packages/staking_reward_engine/verifier.py",
                "--tests",
                "tests/test_issue_1300.py",
            ],
            "Quality and Security Scoring Suite (Verifier Engine)",
        ),
    ]

    for cmd, desc in verifications:
        if not run_command(cmd, desc):
            return 1

    sys.stdout.write("\nAll verifications for Issue #1300 passed successfully.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
