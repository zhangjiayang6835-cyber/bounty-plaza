"""Verification script for Bedrock template compiler and build filter pipeline."""

import json
import os
import shutil
import tempfile
import time
from typing import Tuple

from packages.bedrock_template_compiler import (
    BedrockBuildPipeline,
    validate_deployment,
)


def prepare_fixtures(root_dir: str) -> Tuple[str, str]:
    """Populate test fixture directory with templates and audio samples.

    Args:
        root_dir: Temporary root folder.

    Returns:
        Tuple containing source directory and destination directory paths.
    """
    src = os.path.join(root_dir, "source")
    dest = os.path.join(root_dir, "dest")
    sounds = os.path.join(src, "sounds", "player")
    os.makedirs(sounds, exist_ok=True)

    parent_tpl = {
        "format_version": "1.20.0",
        "minecraft:item": {
            "description": {"category": "Equipment"},
            "components": {"minecraft:max_stack_size": 1},
        },
    }
    with open(os.path.join(src, "base.jsonte"), "w", encoding="utf-8") as handle:
        handle.write(json.dumps(parent_tpl))

    child_content = (
        '{\n'
        '  "$extend": "base.jsonte",\n'
        '  "$scope": {"material": "ruby"},\n'
        '  "minecraft:item": {\n'
        '    "description": {"identifier": "custom:{{material}}_sword"},\n'
        '    "components": {"minecraft:damage": 8}\n'
        '  }\n'
        '}'
    )
    with open(os.path.join(src, "sword.jsonte"), "w", encoding="utf-8") as handle:
        handle.write(child_content)

    with open(os.path.join(sounds, "hit.ogg"), "w", encoding="utf-8") as handle:
        handle.write("ogg_sample")

    return src, dest


def run_verification() -> bool:
    """Execute end-to-end verification of Bedrock build filters and templates.

    Returns:
        True if all pipeline validations pass cleanly.
    """
    temp_dir = tempfile.mkdtemp(prefix="verify_issue_1207_")
    try:
        src_dir, dest_dir = prepare_fixtures(temp_dir)
        pipeline = BedrockBuildPipeline()
        stats, results = pipeline.build_and_deploy(src_dir, dest_dir)
        report = validate_deployment(src_dir, dest_dir)

        dest_file = os.path.join(dest_dir, "sword.json")
        has_file = os.path.isfile(dest_file)
        item_id = ""
        if has_file:
            with open(dest_file, "r", encoding="utf-8") as handle:
                compiled = json.load(handle)
            desc = compiled.get("minecraft:item", {}).get("description", {})
            item_id = desc.get("identifier", "")

        return (
            stats.compiled_templates >= 1
            and stats.compiled_audio >= 1
            and all(res.success for res in results)
            and report.is_valid
            and has_file
            and item_id == "custom:ruby_sword"
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def main() -> None:
    """Main entry point for verification execution."""
    start = time.time()
    success = run_verification()
    elapsed = time.time() - start
    if success:
        print(f"VERIFICATION_SUCCESS in {elapsed:.3f}s")
    else:
        print(f"VERIFICATION_FAILED in {elapsed:.3f}s")


if __name__ == "__main__":
    main()
