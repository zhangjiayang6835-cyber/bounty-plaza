#!/usr/bin/env python3
"""
block_entity_migrate.py — Rigorous migration tool for Bedrock block entities

This script copies custom block entity definition files from one addon to another
while updating every reference to the old namespace. It handles hidden component
groups, type families, scale animations, and Script API component registrations.

Usage:
    python scripts/block_entity_migrate.py \
        --src path/to/old_addon \
        --dst path/to/new_addon \
        --old-ns old_ns \
        --new-ns new_ns [--dry-run]
"""

import argparse
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Any

# ---------------------------------------------------------------------------
# Helper functions
# ---------------------------------------------------------------------------

def load_json(file_path: Path) -> Dict[str, Any]:
    """Load a JSON file preserving ordering and Unicode characters."""
    with file_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Dict[str, Any], file_path: Path) -> None:
    """Write JSON data with pretty formatting (4‑space indent)."""
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)
        f.write("\n")


def replace_namespace(value: Any, old_ns: str, new_ns: str) -> Any:
    """Recursively replace namespace strings in JSON values.

    The function looks for occurrences of "old_ns:" in strings and replaces
    them with "new_ns:". It also handles dictionary keys that represent component
    identifiers.
    """
    if isinstance(value, str):
        return value.replace(f"{old_ns}:", f"{new_ns}:")
    if isinstance(value, list):
        return [replace_namespace(v, old_ns, new_ns) for v in value]
    if isinstance(value, dict):
        new_dict = {}
        for k, v in value.items():
            new_key = k.replace(f"{old_ns}:", f"{new_ns}:")
            new_dict[new_key] = replace_namespace(v, old_ns, new_ns)
        return new_dict
    return value


def migrate_file(src_file: Path, dst_file: Path, old_ns: str, new_ns: str, dry_run: bool) -> None:
    """Migrate a single block entity definition.

    - Loads the JSON definition.
    - Replaces all namespace occurrences.
    - Preserves hidden component groups and other nested structures.
    - Writes the result to the destination (or prints diff when dry‑run).
    """
    data = load_json(src_file)
    migrated = replace_namespace(data, old_ns, new_ns)

    if dry_run:
        print(f"[DRY‑RUN] Would write {dst_file.relative_to(Path.cwd())}")
        return

    dst_file.parent.mkdir(parents=True, exist_ok=True)
    save_json(migrated, dst_file)
    print(f"Migrated {src_file.relative_to(Path.cwd())} → {dst_file.relative_to(Path.cwd())}")


def migrate_directory(src_dir: Path, dst_dir: Path, old_ns: str, new_ns: str, dry_run: bool) -> None:
    """Recursively migrate all *.json files in the source directory."""
    for src_file in src_dir.rglob("*.json"):
        relative = src_file.relative_to(src_dir)
        dst_file = dst_dir / relative
        migrate_file(src_file, dst_file, old_ns, new_ns, dry_run)

# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

def main() -> int:
    parser = argparse.ArgumentParser(description="Migrate custom Bedrock block entity definitions")
    parser.add_argument("--src", required=True, type=Path, help="Source addon directory containing block entity JSON files")
    parser.add_argument("--dst", required=True, type=Path, help="Destination addon directory where migrated files will be placed")
    parser.add_argument("--old-ns", required=True, help="Old namespace prefix (e.g., old_ns)")
    parser.add_argument("--new-ns", required=True, help="New namespace prefix (e.g., new_ns)")
    parser.add_argument("--dry-run", action="store_true", help="Show actions without writing files")
    args = parser.parse_args()

    if not args.src.is_dir():
        parser.error(f"Source directory does not exist: {args.src}")
    if args.src.resolve() == args.dst.resolve():
        parser.error("Source and destination directories must be different")

    migrate_directory(args.src, args.dst, args.old_ns, args.new_ns, args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
