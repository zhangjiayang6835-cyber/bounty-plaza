"""Formal verification entrypoint for Issue #1308 Bedrock physics math."""

from __future__ import annotations

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.bedrock_physics_effects.verifier import BedrockPhysicsVerifier


def run_typescript_build() -> bool:
    """Execute TypeScript compiler to build distribution JavaScript."""
    proc = subprocess.run(
        ["npx", "tsc"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        print(f"TypeScript compilation failed:\n{proc.stderr}")
        return False
    print("[OK] TypeScript compilation succeeded.")
    return True


def run_node_tests() -> bool:
    """Execute Node.js unit tests and verification harness."""
    unit_proc = subprocess.run(
        ["node", "--test", "test/bedrock_physics.test.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if unit_proc.returncode != 0:
        print(f"Node unit tests failed:\n{unit_proc.stderr}")
        return False
    print("[OK] Node.js unit tests passed.")

    harness_proc = subprocess.run(
        ["node", "test/verify.js"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    print(harness_proc.stdout)
    if harness_proc.returncode != 0:
        print(f"Node harness failed:\n{harness_proc.stderr}")
        return False
    return True


def run_verification() -> int:
    """Execute all verification layers and return appropriate exit code."""
    print("=== Step 1: TypeScript Compilation ===")
    if not run_typescript_build():
        return 1

    print("\n=== Step 2: Node.js Test Suites ===")
    if not run_node_tests():
        return 1

    print("=== Step 3: Python Formal Invariant Verifications ===")
    report = BedrockPhysicsVerifier.run_all_checks()

    for detail in report.details:
        print(detail)

    print(f"\nSummary: {report.checks_passed}/{report.checks_run} invariant checks passed.")
    if report.all_passed:
        print("PASS: Bedrock physics 1-tick potion effect invariants verified.")
        return 0

    print("FAIL: One or more invariant checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(run_verification())
