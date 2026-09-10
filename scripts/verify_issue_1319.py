"""Standalone verification script for Issue #1319."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from packages.json_ui_text_slicing.verifier import BedrockJsonUiVerifier


def main() -> int:
    """Execute all verification checks for Issue #1319 and output summary report.

    Returns:
        Exit code 0 on complete verification success, 1 on failure.
    """
    print("=" * 60)
    print("BEDROCK JSON UI TEXT SLICING & PRESERVATION VERIFIER (ISSUE #1319)")
    print("=" * 60)

    panel_schema = BedrockJsonUiVerifier.create_sample_panel()
    report = BedrockJsonUiVerifier.run_all_checks(panel_schema)

    for detail in report.details:
        print(f"[*] {detail}")

    print("-" * 60)
    print(f"Results: {report.passed_checks}/{report.total_checks} Invariants Verified")

    if report.is_successful:
        print("VERIFICATION STATUS: SUCCESS (All Invariants Passed)")
        return 0

    print(f"VERIFICATION STATUS: FAILED ({report.failed_checks} Failures)")
    return 1


if __name__ == "__main__":
    sys.exit(main())
