#!/usr/bin/env python3
"""Automated verification script for Issue #1584 submission."""

import subprocess
import sys


def run_step(description: str, cmd: list[str]) -> None:
    """Execute validation step and abort on failure."""
    sys.stdout.write(f"==> {description}...\n")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.stderr.write(f"FAILED: {description}\n")
        sys.stderr.write(proc.stdout + "\n" + proc.stderr + "\n")
        sys.exit(proc.returncode)
    sys.stdout.write(proc.stdout)
    sys.stdout.write(f"OK: {description}\n\n")


def main() -> None:
    """Run all quality, security, correctness, and scoring verifications."""
    python_bin = sys.executable or "python3"
    run_step("Django System Check", [python_bin, "manage.py", "check"])
    run_step("Pytest Test Suite", [python_bin, "-m", "pytest", "tests/", "-v"])
    run_step("Bandit Security Scan", ["bandit", "-r", "packages/", "django_hello_world.py"])
    run_step("Pylint Quality Gate", ["pylint", "packages/", "django_hello_world.py", "tests/"])
    run_step("Bounty Score Engine", [python_bin, "scripts/score.py", "--code", "django_hello_world.py", "--tests", "tests/"])
    sys.stdout.write("ALL VERIFICATIONS PASSED WITH ZERO VIOLATIONS.\n")


if __name__ == "__main__":
    main()
