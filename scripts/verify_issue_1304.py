"""Standalone verification script for Issue #1304 ERC-4626 YieldVault."""

import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from packages.erc4626_vault.verifier import VaultFormalVerifier


def run_verification() -> int:
    """Executes formal verification and prints summary report.

    Returns:
        Status code 0 on success, non-zero on failure.
    """
    verifier = VaultFormalVerifier()
    report = verifier.execute_all()

    sys.stdout.write(f"Verification Report:\n{report.summary}\n")
    if report.all_passed:
        sys.stdout.write("All verification checks successfully passed.\n")
        return 0
    sys.stderr.write("Verification failed.\n")
    return 1


if __name__ == "__main__":
    sys.exit(run_verification())
