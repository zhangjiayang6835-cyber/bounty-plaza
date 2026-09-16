"""Comprehensive verification runner for Issue #1561 Linux Emulator."""

import os
import subprocess
import sys


def main() -> int:
    """Run all test suites, security audits, and scoring validation."""
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    env = dict(os.environ)
    env["PYTHONPATH"] = f"{base_dir}:{env.get("PYTHONPATH", "")}"

    print("=== Running Python Test Suite ===")
    test_res = subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
        cwd=base_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    print(test_res.stderr or test_res.stdout)
    if test_res.returncode != 0:
        print("Python unit tests failed!")
        return 1

    print("=== Running Node.js Test Suite ===")
    node_res = subprocess.run(
        ["node", "test/linux_emulator.test.js"],
        cwd=base_dir,
        capture_output=True,
        text=True,
    )
    print(node_res.stdout or node_res.stderr)
    if node_res.returncode != 0:
        print("Node.js tests failed!")
        return 1

    print("=== Running Bandit Security Audit ===")
    bandit_res = subprocess.run(
        [sys.executable, "-m", "bandit", "-r", "packages/omni_linux"],
        cwd=base_dir,
        capture_output=True,
        text=True,
    )
    if bandit_res.returncode != 0:
        print("Bandit found issues!")
        print(bandit_res.stdout)
        return 1
    print("Bandit scan passed with 0 security findings.")

    print("=== Running Pylint Static Analysis ===")
    pylint_res = subprocess.run(
        [sys.executable, "-m", "pylint", "packages/omni_linux"],
        cwd=base_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    print(pylint_res.stdout)
    if pylint_res.returncode != 0:
        print("Pylint score below requirement!")
        return 1

    print("=== Running Automated Score System ===")
    score_res = subprocess.run(
        [sys.executable, "scripts/score.py", "--code", "packages/omni_linux/manager.py", "--tests", "tests"],
        cwd=base_dir,
        env=env,
        capture_output=True,
        text=True,
    )
    print(score_res.stdout)
    if score_res.returncode != 0:
        print("Scoring system failed!")
        return 1

    print("All verifications passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
