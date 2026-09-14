"""
Verification runner for validating Issue #1321 ruby toolset texture generation.
"""

from __future__ import annotations
import sys
from pathlib import Path

from packages.ruby_texture_generator.generator import (
    RubyTextureGenerator,
    TOOLSET_ITEMS,
)
from packages.ruby_texture_generator.verifier import (
    RubyToolsetVerifier,
    VerificationReport,
)


def _format_line(label: str, is_passed: bool) -> str:
    """
    Formats a single verification check line.

    :param label: Descriptive invariant label
    :param is_passed: Boolean outcome of the invariant check
    :return: Formatted string
    """
    outcome = "PASSED" if is_passed else "FAILED"
    return f"{label:<32} {outcome}\n"


def run_verification() -> int:
    """
    Executes end-to-end invariant validation on ruby toolset textures.

    :return: Exit status code (0 for success, 1 for failure)
    """
    textures_dir = Path("textures/items")
    generator = RubyTextureGenerator()
    generator.generate_toolset(input_dir=textures_dir, output_dir=textures_dir)

    verifier = RubyToolsetVerifier()
    report: VerificationReport = verifier.verify_toolset_directory(textures_dir)

    sys.stdout.write("==================================================\n")
    sys.stdout.write("Invariant Verification Report (Issue #1321)\n")
    sys.stdout.write("==================================================\n")
    sys.stdout.write(_format_line("1. Dimensions (16x16):", report.dimensions_valid))
    sys.stdout.write(_format_line("2. Zero Alpha Bleed:", report.zero_alpha_bleed_valid))
    sys.stdout.write(_format_line("3. Ruby Hue Authenticity:", report.ruby_hue_valid))
    sys.stdout.write(_format_line("4. Shading Gradation:", report.shading_gradation_valid))
    sys.stdout.write(_format_line("5. Non-Diamond Handle Intact:", report.non_diamond_preserved))
    sys.stdout.write(_format_line("6. Deterministic Output Hash:", report.deterministic_hash_valid))
    sys.stdout.write("--------------------------------------------------\n")

    for item in TOOLSET_ITEMS:
        item_path = textures_dir / f"ruby_{item}.png"
        size_bytes = item_path.stat().st_size if item_path.exists() else 0
        sys.stdout.write(f"- ruby_{item}.png: {size_bytes} bytes\n")

    sys.stdout.write("==================================================\n")

    if report.is_all_passed:
        sys.stdout.write("Result: All Invariants Satisfied (100% Passed)\n")
        return 0

    sys.stderr.write("Result: Verification Failed\n")
    return 1


if __name__ == "__main__":
    sys.exit(run_verification())
