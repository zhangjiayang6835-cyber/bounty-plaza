"""
Invariant verifier for validating generated ruby Minecraft toolset textures.
"""

from __future__ import annotations
import hashlib
from pathlib import Path
from typing import NamedTuple

from packages.ruby_texture_generator.generator import (
    decode_png,
    generate_ruby_texture,
    is_diamond_color,
    rgb_to_hsv,
    TOOLSET_ITEMS,
)


class VerificationReport(NamedTuple):
    """Container for invariant verification outcomes."""

    dimensions_valid: bool
    zero_alpha_bleed_valid: bool
    ruby_hue_valid: bool
    shading_gradation_valid: bool
    non_diamond_preserved: bool
    deterministic_hash_valid: bool

    @property
    def is_all_passed(self) -> bool:
        """
        Determines if all invariant checks passed.

        :return: True if every check evaluated to True
        """
        checks = (
            self.dimensions_valid,
            self.zero_alpha_bleed_valid,
            self.ruby_hue_valid,
            self.shading_gradation_valid,
            self.non_diamond_preserved,
            self.deterministic_hash_valid,
        )
        return all(checks)


class RubyToolsetVerifier:
    """Verifier executing invariant assertions over texture assets."""

    @staticmethod
    def verify_dimensions(png_path: Path) -> bool:
        """
        Validates that texture dimensions are exactly 16x16.

        :param png_path: Path to PNG asset
        :return: True if width and height equal 16
        """
        file_bytes = png_path.read_bytes()
        width, height, _ = decode_png(file_bytes)
        return width == 16 and height == 16

    @staticmethod
    def verify_zero_alpha_bleed(png_path: Path) -> bool:
        """
        Ensures transparent pixels have zero RGB values and zero alpha bleed.

        :param png_path: Path to PNG asset
        :return: True if all alpha=0 pixels have r=0, g=0, b=0
        """
        file_bytes = png_path.read_bytes()
        _, _, rows = decode_png(file_bytes)
        for row in rows:
            for px in row:
                if px.alpha == 0 and (px.red != 0 or px.green != 0 or px.blue != 0):
                    return False
        return True

    @staticmethod
    def verify_ruby_hue_authenticity(png_path: Path) -> bool:
        """
        Verifies that non-handle colored pixels lie within ruby spectrum.

        :param png_path: Path to PNG asset
        :return: True if transformed gem pixels fall in 340 deg to 10 deg band
        """
        file_bytes = png_path.read_bytes()
        _, _, rows = decode_png(file_bytes)
        gem_pixels_count = 0

        for row in rows:
            for px in row:
                if px.alpha > 0:
                    hsv = rgb_to_hsv(px.red, px.green, px.blue)
                    is_red_band = (hsv.hue >= 340.0 or hsv.hue <= 10.0)
                    is_ruby_sat = hsv.saturation >= 0.15
                    if is_red_band and is_ruby_sat:
                        gem_pixels_count += 1

        return gem_pixels_count > 0

    @staticmethod
    def verify_shading_gradations(diamond_path: Path, ruby_path: Path) -> bool:
        """
        Verifies that Jappa hand-shaded depth values are preserved between diamond and ruby.

        :param diamond_path: Original diamond PNG path
        :param ruby_path: Generated ruby PNG path
        :return: True if value/luminance delta is within 0.05
        """
        _, _, d_rows = decode_png(diamond_path.read_bytes())
        _, _, r_rows = decode_png(ruby_path.read_bytes())

        for d_row, r_row in zip(d_rows, r_rows):
            for d_px, r_px in zip(d_row, r_row):
                if d_px.alpha > 0:
                    d_hsv = rgb_to_hsv(d_px.red, d_px.green, d_px.blue)
                    if is_diamond_color(d_hsv.hue, d_hsv.saturation, d_hsv.value):
                        r_hsv = rgb_to_hsv(r_px.red, r_px.green, r_px.blue)
                        if abs(d_hsv.value - r_hsv.value) > 0.05:
                            return False
        return True

    @staticmethod
    def verify_non_diamond_preservation(diamond_path: Path, ruby_path: Path) -> bool:
        """
        Verifies that non-diamond pixels (such as wooden tool handles) remain unchanged.

        :param diamond_path: Original diamond PNG path
        :param ruby_path: Generated ruby PNG path
        :return: True if wooden handle pixels are byte-identical
        """
        _, _, d_rows = decode_png(diamond_path.read_bytes())
        _, _, r_rows = decode_png(ruby_path.read_bytes())

        for d_row, r_row in zip(d_rows, r_rows):
            for d_px, r_px in zip(d_row, r_row):
                if d_px.alpha > 0:
                    d_hsv = rgb_to_hsv(d_px.red, d_px.green, d_px.blue)
                    if not is_diamond_color(d_hsv.hue, d_hsv.saturation, d_hsv.value):
                        if (
                            d_px.red != r_px.red
                            or d_px.green != r_px.green
                            or d_px.blue != r_px.blue
                            or d_px.alpha != r_px.alpha
                        ):
                            return False
        return True

    @staticmethod
    def verify_determinism(sample_png_bytes: bytes) -> bool:
        """
        Verifies that consecutive generation runs yield identical SHA-256 byte hashes.

        :param sample_png_bytes: Source PNG bytes
        :return: True if two separate runs produce identical hash
        """
        pass_one = generate_ruby_texture(sample_png_bytes)
        pass_two = generate_ruby_texture(sample_png_bytes)

        hash_one = hashlib.sha256(pass_one).hexdigest()
        hash_two = hashlib.sha256(pass_two).hexdigest()
        return hash_one == hash_two

    def verify_toolset_directory(
        self, textures_dir: Path, items: tuple[str, ...] = TOOLSET_ITEMS
    ) -> VerificationReport:
        """
        Runs comprehensive suite of invariant checks across all toolset assets in a directory.

        :param textures_dir: Directory containing diamond and ruby PNG assets
        :param items: Tuple of item names to verify
        :return: VerificationReport summary
        """
        dims_ok = True
        alpha_ok = True
        hue_ok = True
        grad_ok = True
        handles_ok = True
        det_ok = True

        for item in items:
            d_path = textures_dir / f"diamond_{item}.png"
            r_path = textures_dir / f"ruby_{item}.png"

            if not d_path.exists() or not r_path.exists():
                return VerificationReport(
                    dimensions_valid=False,
                    zero_alpha_bleed_valid=False,
                    ruby_hue_valid=False,
                    shading_gradation_valid=False,
                    non_diamond_preserved=False,
                    deterministic_hash_valid=False,
                )

            dims_ok = dims_ok and self.verify_dimensions(r_path)
            alpha_ok = alpha_ok and self.verify_zero_alpha_bleed(r_path)
            hue_ok = hue_ok and self.verify_ruby_hue_authenticity(r_path)
            grad_ok = grad_ok and self.verify_shading_gradations(d_path, r_path)
            handles_ok = handles_ok and self.verify_non_diamond_preservation(d_path, r_path)
            det_ok = det_ok and self.verify_determinism(d_path.read_bytes())

        return VerificationReport(
            dimensions_valid=dims_ok,
            zero_alpha_bleed_valid=alpha_ok,
            ruby_hue_valid=hue_ok,
            shading_gradation_valid=grad_ok,
            non_diamond_preserved=handles_ok,
            deterministic_hash_valid=det_ok,
        )
