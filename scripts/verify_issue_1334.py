"""Standalone end-to-end verification runner for Issue #1334."""

from pathlib import Path
import subprocess
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.kinematic_ccd.verifier import KinematicCcdVerifier


def main() -> int:
    """Executes TypeScript build, Node test harness, and Python invariant verifier."""
    print("=== Step 1: Running TypeScript Compiler (tsc) ===")
    tsc_proc = subprocess.run(["npx", "tsc"], capture_output=True, text=True, check=False)
    if tsc_proc.returncode != 0:
        print(f"TypeScript compilation failed:\n{tsc_proc.stderr}")
        return 1
    print("[OK] TypeScript compilation succeeded.")

    print("\n=== Step 2: Running Node.js test/verify.js Harness ===")
    node_proc = subprocess.run(
        ["node", "test/verify.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    print(node_proc.stdout)
    if node_proc.returncode != 0:
        print(f"Node test/verify.js failed:\n{node_proc.stderr}")
        return 1

    print("=== Step 3: Running Node.js Unit Tests (test/swept_aabb.test.js) ===")
    unit_proc = subprocess.run(
        ["node", "--test", "test/swept_aabb.test.js"],
        capture_output=True,
        text=True,
        check=False,
    )
    if unit_proc.returncode != 0:
        print(f"Node unit tests failed:\n{unit_proc.stderr}")
        return 1
    print("[OK] All Node.js unit tests passed.")

    print("\n=== Step 4: Running Python Formal Invariant Verifier ===")
    report = KinematicCcdVerifier.run_all_checks()
    for detail in report.details:
        print(f"[*] {detail}")
    if not report.all_passed:
        print("Formal invariant verification failed.")
        return 1

    print(f"\nAll {report.checks_run} formal invariant checks passed.")
    print("\n[SUCCESS] All Issue #1334 verification targets PASSED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
