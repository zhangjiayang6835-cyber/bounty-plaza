"""Verification script for Bedrock block schema validation (Issue #1306)."""

import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from packages.bedrock_block_schema.verifier import (
    BedrockBlockVerifier,
)


def main() -> int:
    """Run comprehensive verification on block definition and pack assets.

    Returns:
        Exit code 0 if all invariants pass, 1 otherwise.
    """
    bp_path = Path("packs/BP/blocks/void_crystal_ore.json")
    geo_path = Path("packs/RP/models/blocks/void_crystal_ore.geo.json")
    terrain_path = Path("packs/RP/textures/terrain_texture.json")

    for path in (bp_path, geo_path, terrain_path):
        if not path.exists():
            print(f"Error: Missing required pack asset: {path}")
            return 1

    with open(bp_path, encoding="utf-8") as f:
        block_def = json.load(f)
    with open(geo_path, encoding="utf-8") as f:
        geo_data = json.load(f)
    with open(terrain_path, encoding="utf-8") as f:
        terrain_data = json.load(f)

    report = BedrockBlockVerifier.verify_all_invariants(block_def, geo_data, terrain_data)

    print("=" * 60)
    print("Bedrock Block Schema Verification Report (Issue #1306)")
    print("=" * 60)
    print(f"Status: {'PASSED' if report.is_successful else 'FAILED'}")
    print(f"Invariants Passed: {report.passed_invariants}/{len(BedrockBlockVerifier.INVARIANTS)}")

    print("\nVerified Invariants:")
    for inv in report.invariants_verified:
        print(f"  [OK] {inv}")

    if report.failure_reasons:
        print("\nFailures:")
        for fail in report.failure_reasons:
            print(f"  [FAIL] {fail}")

    print("=" * 60)
    return 0 if report.is_successful else 1


if __name__ == "__main__":
    sys.exit(main())
