"""Standalone verification script for Issue #1210 acceptance criteria."""

import json
import sys
from pathlib import Path

try:
    from packages.bedrock_block_schema.validator import (
        BlockSchemaValidator,
        ResourcePackSoundResolver,
    )
except ModuleNotFoundError:
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    from packages.bedrock_block_schema.validator import (
        BlockSchemaValidator,
        ResourcePackSoundResolver,
    )

ROOT_DIR = Path(__file__).resolve().parent.parent


def verify_block_definition() -> bool:
    """Verify that BP/blocks/compressed_basalt.json strictly complies with format 1.26.30."""
    bp_path = ROOT_DIR / "BP" / "blocks" / "compressed_basalt.json"
    if not bp_path.exists():
        print("FAIL: BP/blocks/compressed_basalt.json does not exist")
        return False

    with open(bp_path, "r", encoding="utf-8") as handle:
        data = json.load(handle)

    validator = BlockSchemaValidator(target_format="1.26.30")
    report = validator.validate_dict(data)

    if not report.is_valid:
        print(f"FAIL: Schema validation failed with {len(report.issues)} issues:")
        for issue in report.issues:
            print(f"  - [{issue.severity}] {issue.path}: {issue.message}")
        return False

    desc = data.get("minecraft:block", {}).get("description", {})
    if "sound" in desc:
        print("FAIL: 'sound' property found inside description")
        return False

    print("PASS: BP/blocks/compressed_basalt.json complies with format 1.26.30")
    return True


def verify_resource_pack_sound() -> bool:
    """Verify that RP/blocks.json maps custom:compressed_basalt to stone sound profile."""
    rp_path = ROOT_DIR / "RP" / "blocks.json"
    if not rp_path.exists():
        print("FAIL: RP/blocks.json does not exist")
        return False

    resolver = ResourcePackSoundResolver(str(rp_path))
    report = resolver.verify_block_sound("custom:compressed_basalt", expected_sound="stone")

    if not report.is_valid:
        print(f"FAIL: Resource pack verification failed with {len(report.issues)} issues:")
        for issue in report.issues:
            print(f"  - [{issue.severity}] {issue.path}: {issue.message}")
        return False

    sound_val = resolver.resolve_sound("custom:compressed_basalt")
    print(f"PASS: RP/blocks.json correctly assigns sound '{sound_val}' to custom:compressed_basalt")
    return True


def main() -> int:
    """Run all verification checks for Issue #1210."""
    print("Executing Issue #1210 Acceptance Criteria Verification...")
    bp_ok = verify_block_definition()
    rp_ok = verify_resource_pack_sound()

    if bp_ok and rp_ok:
        print("All Issue #1210 checks PASSED.")
        return 0

    print("Issue #1210 verification FAILED.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
