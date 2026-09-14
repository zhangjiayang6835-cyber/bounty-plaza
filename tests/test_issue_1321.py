"""
Test suite for validating Ruby Toolset generation and verification invariants (Issue #1321).
"""

from __future__ import annotations
import hashlib
from pathlib import Path
import pytest
from packages.ruby_texture_generator.generator import (
    RubyTextureGenerator,
    decode_png,
    encode_png,
    rgb_to_hsv,
    hsv_to_rgb,
    is_diamond_color,
    shift_pixel_to_ruby,
    generate_ruby_texture,
    ColorRgba,
    TOOLSET_ITEMS,
    CANONICAL_DIAMOND_BASE64,
)
from packages.ruby_texture_generator.verifier import (
    RubyToolsetVerifier,
    VerificationReport,
)


def test_hsv_rgb_conversions_roundtrip() -> None:
    """Validates RGB to HSV and back round-trip identity on key palette samples."""
    sample_rgbs = (
        (255, 0, 0),
        (0, 255, 0),
        (0, 0, 255),
        (164, 253, 240),
        (43, 199, 172),
        (14, 63, 54),
        (8, 37, 32),
        (104, 78, 30),
        (73, 54, 21),
    )
    for r_ch, g_ch, b_ch in sample_rgbs:
        hsv = rgb_to_hsv(r_ch, g_ch, b_ch)
        recon_r, recon_g, recon_b = hsv_to_rgb(hsv.hue, hsv.saturation, hsv.value)
        assert recon_r == r_ch
        assert recon_g == g_ch
        assert recon_b == b_ch


def test_is_diamond_color_classification() -> None:
    """Verifies color discriminator separates diamond pixels from handle and background."""
    glint = rgb_to_hsv(164, 253, 240)
    assert is_diamond_color(glint.hue, glint.saturation, glint.value) is True

    midtone = rgb_to_hsv(43, 199, 172)
    assert is_diamond_color(midtone.hue, midtone.saturation, midtone.value) is True

    outline = rgb_to_hsv(8, 37, 32)
    assert is_diamond_color(outline.hue, outline.saturation, outline.value) is True

    stick = rgb_to_hsv(104, 78, 30)
    assert is_diamond_color(stick.hue, stick.saturation, stick.value) is False


def test_shift_pixel_zero_alpha_bleed() -> None:
    """Verifies transparent pixels preserve zero alpha with cleaned RGB channels."""
    transparent = ColorRgba(164, 253, 240, 0)
    shifted = shift_pixel_to_ruby(transparent)
    assert shifted.alpha == 0
    assert shifted.red == 0
    assert shifted.green == 0
    assert shifted.blue == 0


def test_shift_pixel_stick_preservation() -> None:
    """Verifies wooden handle pixels remain unchanged."""
    handle_px = ColorRgba(104, 78, 30, 255)
    shifted = shift_pixel_to_ruby(handle_px)
    assert shifted.red == 104
    assert shifted.green == 78
    assert shifted.blue == 30
    assert shifted.alpha == 255


def test_shift_pixel_ruby_hue_and_v_preservation() -> None:
    """Verifies diamond pixels map to ruby spectrum while maintaining V gradation."""
    diamond_px = ColorRgba(43, 199, 172, 255)
    orig_hsv = rgb_to_hsv(diamond_px.red, diamond_px.green, diamond_px.blue)
    shifted = shift_pixel_to_ruby(diamond_px)
    new_hsv = rgb_to_hsv(shifted.red, shifted.green, shifted.blue)

    assert shifted.alpha == 255
    assert new_hsv.hue >= 340.0 or new_hsv.hue <= 10.0
    assert abs(new_hsv.value - orig_hsv.value) <= 0.05


def test_png_decode_encode_cycle() -> None:
    """Verifies PNG decode and encode consistency."""
    gen = RubyTextureGenerator()
    sword_bytes = gen.get_canonical_bytes("sword")
    width, height, rows = decode_png(sword_bytes)

    assert width == 16
    assert height == 16
    assert len(rows) == 16

    re_encoded = encode_png(width, height, rows)
    w_recon, h_recon, rows_recon = decode_png(re_encoded)

    assert w_recon == 16
    assert h_recon == 16
    assert len(rows_recon) == 16


def test_deterministic_output_hash() -> None:
    """Verifies repeated generation produces byte-for-byte identical output."""
    gen = RubyTextureGenerator()
    sword_bytes = gen.get_canonical_bytes("sword")

    pass_a = generate_ruby_texture(sword_bytes)
    pass_b = generate_ruby_texture(sword_bytes)

    hash_a = hashlib.sha256(pass_a).hexdigest()
    hash_b = hashlib.sha256(pass_b).hexdigest()
    assert hash_a == hash_b


def test_generate_toolset_all_items(tmp_path: Path) -> None:
    """Verifies batch generation produces all 5 toolset textures in target directory."""
    generator = RubyTextureGenerator()
    out_paths = generator.generate_toolset(output_dir=tmp_path)

    assert len(out_paths) == 5
    for item in TOOLSET_ITEMS:
        item_file = tmp_path / f"ruby_{item}.png"
        assert item_file.exists()
        assert item_file.stat().st_size > 0


def test_ruby_toolset_verifier_invariants(tmp_path: Path) -> None:
    """Verifies all six invariants on diamond and generated ruby assets."""
    generator = RubyTextureGenerator()
    for item in TOOLSET_ITEMS:
        d_bytes = generator.get_canonical_bytes(item)
        (tmp_path / f"diamond_{item}.png").write_bytes(d_bytes)

    generator.generate_toolset(input_dir=tmp_path, output_dir=tmp_path)

    verifier = RubyToolsetVerifier()
    report: VerificationReport = verifier.verify_toolset_directory(tmp_path)

    assert report.dimensions_valid is True
    assert report.zero_alpha_bleed_valid is True
    assert report.ruby_hue_valid is True
    assert report.shading_gradation_valid is True
    assert report.non_diamond_preserved is True
    assert report.deterministic_hash_valid is True
    assert report.is_all_passed is True


def test_verifier_detects_bad_dimensions(tmp_path: Path) -> None:
    """Verifies dimension checker fails on non-16x16 images."""
    dummy_pixels = [[ColorRgba(0, 0, 0, 0) for _ in range(8)] for _ in range(8)]
    bad_png = encode_png(8, 8, dummy_pixels)
    bad_path = tmp_path / "bad.png"
    bad_path.write_bytes(bad_png)

    assert RubyToolsetVerifier.verify_dimensions(bad_path) is False
