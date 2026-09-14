"""Command-line interface for testing and querying Minecraft Bedrock pack paths."""

import argparse
import json
import sys
from typing import List, Optional

from packages.bedrock_pack_resolver.models import (
    BedrockPathNotFoundError,
    BedrockResolverOptions,
    PackType,
)
from packages.bedrock_pack_resolver.resolver import (
    get_development_packs_path,
    list_candidate_mojang_paths,
)


def build_parser() -> argparse.ArgumentParser:
    """Construct command-line argument parser for bedrock pack resolver.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="Minecraft Bedrock Development Packs Path Resolver",
    )
    parser.add_argument(
        "--type",
        choices=["behavior", "resource", "skin"],
        default="behavior",
        help="Pack directory type to resolve",
    )
    parser.add_argument(
        "--localappdata",
        default=None,
        help="Override LocalAppData directory path",
    )
    parser.add_argument(
        "--list-candidates",
        action="store_true",
        help="List all evaluated candidate paths",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit result in JSON format",
    )
    return parser


def main(argv: Optional[List[str]] = None) -> int:
    """Execute command-line entrypoint.

    Args:
        argv: Optional arguments vector.

    Returns:
        Exit code (0 for success, 1 for error).
    """
    parser = build_parser()
    args = parser.parse_args(argv)

    options = BedrockResolverOptions(
        pack_type=PackType(args.type),
        local_app_data=args.localappdata,
    )

    if args.list_candidates:
        candidates = list_candidate_mojang_paths(options)
        if args.json:
            print(json.dumps({"candidates": candidates}, indent=2))
        else:
            print(f"Evaluated {len(candidates)} candidate paths:")
            for candidate in candidates:
                print(f"  - {candidate}")
        return 0

    try:
        resolved = get_development_packs_path(options)
        if args.json:
            print(json.dumps({"resolved_path": resolved, "status": "success"}, indent=2))
        else:
            print(resolved)
        return 0
    except (BedrockPathNotFoundError, FileNotFoundError) as err:
        if args.json:
            print(json.dumps({"error": str(err), "status": "failed"}, indent=2))
        else:
            sys.stderr.write(f"Error: {err}\n")
        return 1


if __name__ == "__main__":
    sys.exit(main())
