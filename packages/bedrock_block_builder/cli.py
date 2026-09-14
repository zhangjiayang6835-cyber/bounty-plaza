"""Command-line interface for the Bedrock block family builder and compiler."""

import argparse
import json
import sys
from typing import Optional

from packages.bedrock_block_builder.builder import BlockFamilyBuilder
from packages.bedrock_block_builder.models import BuildOptions, FamilyValidationError
from packages.bedrock_block_builder.pipeline import BedrockBuildPipeline


def parse_arguments(args: Optional[list[str]] = None) -> argparse.Namespace:
    """Parses CLI arguments for the builder command line interface."""
    parser = argparse.ArgumentParser(
        description="Bedrock Block Family Compiler and Clean-Slate Pipeline"
    )
    parser.add_argument(
        "--source",
        default="packs/behavior_pack",
        help="Path to source pack directory",
    )
    parser.add_argument(
        "--staging-base",
        default="_temp",
        help="Base scratch directory for staging",
    )
    parser.add_argument(
        "--staging",
        default="_temp/behavior_pack",
        help="Staging directory for pack assets",
    )
    parser.add_argument(
        "--dest",
        default="dist/behavior_pack",
        help="Final distribution pack directory",
    )
    parser.add_argument(
        "--clean",
        action="store_true",
        default=True,
        help="Enforce scratch directory cleanup before build",
    )
    parser.add_argument(
        "--no-clean",
        action="store_false",
        dest="clean",
        help="Bypass scratch directory cleanup",
    )
    parser.add_argument(
        "--generate-catalog-only",
        action="store_true",
        help="Compile and export block_families.json only",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output structured JSON results",
    )
    return parser.parse_args(args)


def main(args: Optional[list[str]] = None) -> int:
    """CLI execution entrypoint for building block families."""
    parsed = parse_arguments(args)
    opts = BuildOptions(
        source_dir=parsed.source,
        staging_base=parsed.staging_base,
        staging_dir=parsed.staging,
        dest_dir=parsed.dest,
        clean=parsed.clean,
    )

    if parsed.generate_catalog_only:
        builder = BlockFamilyBuilder(options=opts)
        try:
            catalog = builder.build_catalog()
            builder.export_catalog(catalog)
            if parsed.json:
                print(json.dumps(catalog.to_dict(), indent=2, sort_keys=True))
            else:
                print(f"Catalog compiled with {catalog.statistics.total_families} families.")
            return 0
        except (OSError, FamilyValidationError, ValueError) as err:
            if parsed.json:
                print(json.dumps({"error": str(err)}, indent=2))
            else:
                sys.stderr.write(f"Error: {err}\n")
            return 1

    pipeline = BedrockBuildPipeline(options=opts)
    result = pipeline.run()

    if parsed.json:
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    else:
        status_text = "SUCCESS" if result.success else "FAILED"
        print(f"Build status: {status_text} - {result.message}")
        if result.catalog:
            print(f"Total families: {result.catalog.statistics.total_families}")
            print(f"Total blocks: {result.catalog.statistics.total_blocks}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
