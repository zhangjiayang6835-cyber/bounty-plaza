"""Verification runner script for Issue #1310."""

from pathlib import Path
import sys

from packages.bedrock_json_ui.verifier import BedrockJsonUiVerifier


def main() -> int:
    """Executes formal verification checks for Issue #1310.

    Returns:
        Exit code 0 on success, 1 on failure.
    """
    repo_root = Path(__file__).resolve().parent.parent
    verifier = BedrockJsonUiVerifier()
    report = verifier.execute_all(repo_root)

    print("==================================================")
    print("Bedrock JSON UI Issue #1310 Formal Verification")
    print("==================================================")
    print(report.summary)
    print("==================================================")

    if report.all_passed:
        print("[SUCCESS] All Issue #1310 criteria verified.")
        return 0

    print("[FAILURE] One or more verification checks failed.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
