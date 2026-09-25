"""CLI entrypoint for managing platform status meters."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from src.status_meter import (
    START_TAG,
    load_metrics_from_config,
    update_readme,
)


def run_check(target_file: Path) -> bool:
    """Verify that target document contains valid status meter markers.

    Args:
        target_file: Path to Markdown file to verify.

    Returns:
        True if markers are found and file exists, False otherwise.
    """
    if not target_file.exists():
        return False
    content = target_file.read_text(encoding="utf-8")
    status = START_TAG in content
    return status


def update_target_file(file_path: Path, locale: str) -> bool:
    """Update status meter section in the specified file.

    Args:
        file_path: File path to update.
        locale: Language identifier for rendered table.

    Returns:
        True if update succeeded, False otherwise.
    """
    metrics = load_metrics_from_config()
    success = update_readme(file_path, metrics=metrics, locale=locale)
    return success


def parse_arguments() -> argparse.Namespace:
    """Configure command line arguments.

    Returns:
        Parsed arguments namespace.
    """
    parser = argparse.ArgumentParser(
        description="Bounty Plaza README status meter generator and validator."
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update status meters across README files.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate presence of status meter markers.",
    )
    parser.add_argument(
        "--file",
        type=str,
        default=None,
        help="Optional path to a single target Markdown file.",
    )
    parser.add_argument(
        "--locale",
        type=str,
        choices=["en", "zh"],
        default="en",
        help="Locale for rendered output table.",
    )
    args = parser.parse_args()
    return args


def main() -> int:
    """Execute status meter command line workflow.

    Returns:
        Exit code (0 for success, 1 for failure).
    """
    args = parse_arguments()

    if args.check:
        files = [Path("README.md"), Path("README.en.md")]
        if args.file:
            files = [Path(args.file)]
        all_passed = True
        for doc in files:
            present = run_check(doc)
            state_label = "VALID" if present else "MISSING"
            print(f"[{state_label}] {doc}")
            if not present:
                all_passed = False
        return 0 if all_passed else 1

    if args.update or not args.check:
        if args.file:
            target = Path(args.file)
            loc = args.locale
            ok = update_target_file(target, loc)
            return 0 if ok else 1

        res_zh = update_target_file(Path("README.md"), "zh")
        res_en = update_target_file(Path("README.en.md"), "en")
        if res_zh and res_en:
            print("Successfully updated README.md and README.en.md status meters.")
            return 0
        print("Failed to update status meters.")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
