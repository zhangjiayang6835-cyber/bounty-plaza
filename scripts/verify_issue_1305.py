"""Standalone verification entrypoint for Issue #1305."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from packages.hitbox_math.verifier import HitboxMathVerifier


def main() -> int:
    """Runs all formal invariant checks for Issue #1305."""
    print("=" * 60)
    print("Executing Hitbox Math Formal Invariant Verifier (Issue #1305)...")
    print("=" * 60)

    report = HitboxMathVerifier.run_all_checks()
    for detail in report.details:
        print(f"  [+] {detail}")

    if not report.all_passed:
        print("\n[-] Verification failed: One or more invariants violated.")
        return 1

    print(f"\n[+] All {report.checks_run} formal invariant checks passed successfully.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
