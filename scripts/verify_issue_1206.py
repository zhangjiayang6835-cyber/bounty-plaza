"""Standalone verification and performance benchmarking script for Issue #1206."""

import json
import os
import sys
import time
from typing import Dict, Any

from packages.ruby_texture_generator.textures import generate_all_tools, image_to_png_bytes
from packages.ruby_texture_generator.recolor import recolor_image_bytes
from packages.ruby_texture_generator.validator import validate_ruby_texture


def run_benchmark(iterations: int = 50) -> Dict[str, Any]:
    """Benchmark the full generation, recoloring, and validation pipeline.

    :param iterations: Number of iterations across all five tools.
    :return: Dictionary containing benchmark statistics.
    """
    tools = generate_all_tools()
    encoded_tools = {name: image_to_png_bytes(img) for name, img in tools.items()}

    start_time = time.perf_counter()
    recolored_count = 0

    for _ in range(iterations):
        for name, dia_bytes in encoded_tools.items():
            ruby_bytes = recolor_image_bytes(dia_bytes)
            res = validate_ruby_texture(dia_bytes, ruby_bytes)
            if not res.valid:
                raise RuntimeError(f"Validation failure for {name}: {res.errors}")
            recolored_count += 1

    elapsed = time.perf_counter() - start_time
    ops_per_second = recolored_count / elapsed

    return {
        "iterations": iterations,
        "total_operations": recolored_count,
        "elapsed_seconds": elapsed,
        "ops_per_second": ops_per_second,
        "average_ms_per_image": (elapsed / recolored_count) * 1000.0,
    }


def verify_generated_assets(assets_dir: str) -> Dict[str, bool]:
    """Verify pre-generated disk assets for all five toolsets.

    :param assets_dir: Directory containing generated PNG assets.
    :return: Dictionary of status flags per tool.
    """
    tool_names = ["sword", "pickaxe", "axe", "shovel", "hoe"]
    results = {}

    for name in tool_names:
        dia_path = os.path.join(assets_dir, f"diamond_{name}.png")
        ruby_path = os.path.join(assets_dir, f"ruby_{name}.png")

        if not os.path.exists(dia_path) or not os.path.exists(ruby_path):
            results[name] = False
            continue

        with open(dia_path, "rb") as f_dia:
            dia_bytes = f_dia.read()
        with open(ruby_path, "rb") as f_ruby:
            ruby_bytes = f_ruby.read()

        validation = validate_ruby_texture(dia_bytes, ruby_bytes)
        results[name] = validation.valid

    return results


def main() -> int:
    """Execute complete verification and benchmark suite."""
    assets_directory = os.path.join(os.getcwd(), "assets", "textures", "items")
    asset_status = verify_generated_assets(assets_directory)

    all_assets_valid = len(asset_status) == 5 and all(asset_status.values())
    benchmark_data = run_benchmark(iterations=20)

    summary = {
        "status": "PASS" if all_assets_valid else "FAIL",
        "asset_verification": asset_status,
        "benchmark": benchmark_data,
    }

    sys.stdout.write(json.dumps(summary, indent=2) + "\n")
    return 0 if all_assets_valid else 1


if __name__ == "__main__":
    sys.exit(main())
