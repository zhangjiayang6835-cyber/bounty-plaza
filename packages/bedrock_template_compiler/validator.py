"""Integrity validator for compiled Bedrock behavior and resource packs."""

import json
import os
from typing import Dict, List, Optional

from packages.bedrock_template_compiler.models import ValidationReport
from packages.bedrock_template_compiler.pipeline import snapshot_directory_hashes

BANNED_DIRECTIVE_KEYS = {
    "$extend",
    "$template",
    "$copy",
    "$delete",
    "$scope",
    "$variables",
    "$comment",
}


def validate_deployment(
    src_dir: str,
    dest_dir: str,
    pre_build_hashes: Optional[Dict[str, str]] = None,
) -> ValidationReport:
    """Audit compiled Bedrock pack output against acceptance criteria.

    Args:
        src_dir: Source files directory.
        dest_dir: Destination deployment directory.
        pre_build_hashes: Optional pre-build file snapshot of src_dir.

    Returns:
        ValidationReport summarizing integrity findings.
    """
    errors: List[str] = []
    checked_files = 0
    source_unmodified = True
    json_valid = True
    directives_cleared = True

    if pre_build_hashes is not None:
        post_hashes = snapshot_directory_hashes(src_dir)
        if pre_build_hashes != post_hashes:
            source_unmodified = False
            errors.append("Source directory modified: file contents or timestamps mutated during build.")

    if not os.path.isdir(dest_dir):
        return ValidationReport(
            is_valid=False,
            checked_files=0,
            source_unmodified=source_unmodified,
            json_valid=False,
            directives_cleared=False,
            errors=["Destination directory does not exist: " + dest_dir],
        )

    for root, _, files in os.walk(dest_dir):
        for filename in files:
            checked_files += 1
            full_path = os.path.join(root, filename)
            rel_path = os.path.relpath(full_path, dest_dir)

            if filename.endswith(".jsonte"):
                directives_cleared = False
                errors.append(f"Uncompiled .jsonte file discovered in destination: {rel_path}")

            if filename.endswith(".json"):
                try:
                    with open(full_path, "r", encoding="utf-8") as handle:
                        raw_content = handle.read()
                    parsed = json.loads(raw_content)
                except Exception as exc:
                    json_valid = False
                    errors.append(f"Invalid JSON syntax in {rel_path}: {exc}")
                    continue

                if "{{" in raw_content or "}}" in raw_content:
                    directives_cleared = False
                    errors.append(f"Unexpanded mustache expression found in {rel_path}")

                def scan_node(node: object, path_prefix: str) -> None:
                    nonlocal directives_cleared
                    if isinstance(node, dict):
                        for k, v in node.items():
                            if k in BANNED_DIRECTIVE_KEYS or k.startswith("$") or k.startswith("//"):
                                directives_cleared = False
                                errors.append(f"Illegal directive key '{k}' found at {path_prefix} in {rel_path}")
                            scan_node(v, f"{path_prefix}.{k}")
                    elif isinstance(node, list):
                        for idx, item in enumerate(node):
                            scan_node(item, f"{path_prefix}[{idx}]")

                scan_node(parsed, "root")

    is_valid = source_unmodified and json_valid and directives_cleared and (len(errors) == 0)
    return ValidationReport(
        is_valid=is_valid,
        checked_files=checked_files,
        source_unmodified=source_unmodified,
        json_valid=json_valid,
        directives_cleared=directives_cleared,
        errors=errors,
    )
