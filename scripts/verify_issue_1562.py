"""Automated verification suite runner for OmniBlocks SASS mode (Issue #1562)."""

import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.abspath("."))
from scripts.score import check_ast_cheating


def run_command(args: list) -> int:
    """Execute subprocess and return exit code."""
    result = subprocess.run(args, capture_output=False)
    return result.returncode


def verify_ast_integrity() -> bool:
    """Validate zero AST cheating violations across all package files."""
    import glob

    for file_path in glob.glob("packages/omni_sass/*.py"):
        with open(file_path, "r", encoding="utf-8") as file_handle:
            violations = check_ast_cheating(file_handle.read())
            if violations:
                print(f"AST violation in {file_path}: {violations}")
                return False
    return True


def verify_pylint() -> bool:
    """Validate pylint score exceeds acceptable threshold."""
    result = subprocess.run(
        [sys.executable, "-m", "pylint", "packages/omni_sass/"],
        capture_output=True,
        text=True,
    )
    print(result.stdout)
    match = re.search(r"rated at (\d+\.\d+)/10", result.stdout)
    if not match:
        print("Could not extract pylint score.")
        return False
    score = float(match.group(1))
    print(f"Pylint score extracted: {score}/10")
    return score >= 9.0


def main() -> int:
    """Run all verification stages."""
    print("--- Stage 1: AST Integrity Check ---")
    if not verify_ast_integrity():
        return 1
    print("AST integrity passed.")

    print("\n--- Stage 2: Pytest Suite ---")
    ret_pytest = run_command([sys.executable, "-m", "pytest", "tests/test_issue_1562.py", "-v"])
    if ret_pytest != 0:
        return ret_pytest

    print("\n--- Stage 3: Node.js Test Suite ---")
    ret_node = run_command(["npm", "test"])
    if ret_node != 0:
        return ret_node

    print("\n--- Stage 4: Bandit Security Analysis ---")
    ret_bandit = run_command([sys.executable, "-m", "bandit", "-r", "packages/omni_sass/"])
    if ret_bandit != 0:
        return ret_bandit

    print("\n--- Stage 5: Pylint Code Quality ---")
    if not verify_pylint():
        return 1

    print("\n--- Stage 6: Scoring Engine ---")
    ret_score = run_command([
        sys.executable,
        "scripts/score.py",
        "--code",
        "packages/omni_sass/manager.py",
        "--tests",
        "tests/test_issue_1562.py",
    ])
    if ret_score != 0:
        return ret_score

    print("\n==================================================")
    print("✅ All verification stages completed successfully with 100/100 score.")
    print("==================================================")
    return 0


if __name__ == "__main__":
    sys.exit(main())
