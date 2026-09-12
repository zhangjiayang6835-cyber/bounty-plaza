"""Verification script for Issue #1318: Bedrock block families after cleaning _temp."""

import sys
import tempfile
from pathlib import Path

from packages.bedrock_block_builder.verifier import run_all_verifications


def main() -> int:
    """Executes the verification suite and reports validation status."""
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        results = run_all_verifications(temp_path)

        print("=== Bedrock Block Family Verification Report (#1318) ===")
        all_passed = True
        for check_name, passed in results.items():
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {check_name}")
            if not passed:
                all_passed = False

        if all_passed:
            print("All verification checks passed successfully.")
            return 0

        print("One or more verification checks failed.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
