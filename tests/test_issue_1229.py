"""Pytest suite for Issue #1229 Ruby texture generator."""

import pytest
from PIL import Image

from packages.ruby_texture_generator.palette import (
    interpolate_ruby_ramp,
    recolor_pixel,
)
from packages.ruby_texture_generator.recolor import (
    recolor_rgba_buffer,
    recolor_image,
    recolor_image_bytes,
)
from packages.ruby_texture_generator.textures import (
    generate_diamond_tool,
    generate_all_tools,
    image_to_png_bytes,
    TOOL_NAMES,
)
from packages.ruby_texture_generator.validator import (
    validate_ruby_texture,
)


def test_diamond_specular_highlight_recoloring():
    """Verify that primary diamond specular highlight transforms into peach-pink gleam."""
    r, g, b, a = recolor_pixel(188, 252, 252, 255)
    assert (r, g, b, a) == (255, 205, 218, 255)


def test_diamond_secondary_highlight_recoloring():
    """Verify secondary diamond highlight recolors to radiant light rose."""
    r, g, b, a = recolor_pixel(155, 244, 242, 255)
    assert (r, g, b, a) == (255, 185, 195, 255)


def test_diamond_midtone_recoloring():
    """Verify diamond midtone facet recolors to saturated crimson."""
    r, g, b, a = recolor_pixel(45, 194, 191, 255)
    assert (r, g, b, a) == (196, 35, 60, 255)


def test_diamond_dark_facet_recoloring():
    """Verify diamond shadow facet recolors to deep wine burgundy."""
    r, g, b, a = recolor_pixel(32, 139, 139, 255)
    assert (r, g, b, a) == (140, 19, 40, 255)


def test_diamond_outline_recoloring():
    """Verify diamond silhouette outline recolors to deep maroon."""
    r, g, b, a = recolor_pixel(25, 95, 95, 255)
    assert (r, g, b, a) == (84, 9, 23, 255)


def test_wood_handle_preservation():
    """Verify wood stick handle pixels remain byte-for-byte identical."""
    stick_tones = [
        (143, 103, 60, 255),
        (110, 77, 37, 255),
        (75, 49, 20, 255),
        (46, 29, 12, 255),
    ]
    for tone in stick_tones:
        result = recolor_pixel(*tone)
        assert result == tone


def test_full_transparency_preservation():
    """Verify fully transparent pixels retain zero alpha and do not bleed color."""
    transparent_pixels = [
        (0, 0, 0, 0),
        (10, 20, 30, 0),
        (188, 252, 252, 0),
    ]
    for pixel in transparent_pixels:
        result = recolor_pixel(*pixel)
        assert result[3] == 0


def test_partial_alpha_preservation():
    """Verify partial alpha transparency for anti-aliasing is conserved."""
    result = recolor_pixel(45, 194, 191, 140)
    assert result == (196, 35, 60, 140)


def test_recolor_rgba_buffer_size_validation():
    """Verify recolor_rgba_buffer raises ValueError on invalid buffer dimensions."""
    with pytest.raises(ValueError):
        recolor_rgba_buffer(b"too_short", 16, 16)


def test_recolor_rgba_buffer_processing():
    """Verify uncompressed 1024-byte RGBA buffer recoloring."""
    raw = bytearray(16 * 16 * 4)
    for i in range(16 * 16):
        raw[i * 4] = 45
        raw[i * 4 + 1] = 194
        raw[i * 4 + 2] = 191
        raw[i * 4 + 3] = 255

    recolored = recolor_rgba_buffer(bytes(raw), 16, 16)
    assert len(recolored) == 1024
    assert recolored[0] == 196
    assert recolored[1] == 35
    assert recolored[2] == 60
    assert recolored[3] == 255


def test_recolor_image_returns_rgba_pil():
    """Verify recolor_image accepts a PIL Image and returns an RGBA Image of matching size."""
    img = Image.new("RGBA", (16, 16), (45, 194, 191, 255))
    result = recolor_image(img)
    assert result.size == (16, 16)
    assert result.mode == "RGBA"
    pixel = result.getpixel((0, 0))
    assert pixel == (196, 35, 60, 255)


def test_recolor_image_bytes_png_roundtrip():
    """Verify end-to-end PNG encoding and decoding cycle."""
    sword_img = generate_diamond_tool("sword")
    png_bytes = image_to_png_bytes(sword_img)
    ruby_png_bytes = recolor_image_bytes(png_bytes)
    assert len(ruby_png_bytes) > 0
    validation = validate_ruby_texture(png_bytes, ruby_png_bytes)
    assert validation.valid is True


def test_generate_diamond_tools_coverage():
    """Verify all five tools can be generated as 16x16 RGBA images."""
    for tool_name in TOOL_NAMES:
        img = generate_diamond_tool(tool_name)
        assert img.size == (16, 16)
        assert img.mode == "RGBA"


def test_unknown_diamond_tool_raises_value_error():
    """Verify error handling on invalid tool names."""
    with pytest.raises(ValueError):
        generate_diamond_tool("invalid_weapon")


def test_validate_ruby_texture_passes_on_all_toolsets():
    """Verify validator approves all five generated and recolored toolsets."""
    all_tools = generate_all_tools()
    for name, dia_img in all_tools.items():
        ruby_img = recolor_image(dia_img)
        res = validate_ruby_texture(dia_img, ruby_img)
        assert res.valid is True, f"Validation failed for {name}: {res.errors}"


def test_validate_ruby_texture_fails_on_corrupted_handle():
    """Verify validator detects handle modifications."""
    dia_img = generate_diamond_tool("sword")
    corrupted_ruby = recolor_image(dia_img)
    corrupted_ruby.putpixel((3, 12), (255, 0, 0, 255))
    res = validate_ruby_texture(dia_img, corrupted_ruby)
    assert res.valid is False
    assert res.handle_preserved is False


def test_contrast_monotonicity_ruby_ramp():
    """Verify that the continuous ruby ramp maintains strict luminance monotonicity."""
    lightness_values = [0.05, 0.15, 0.30, 0.50, 0.70, 0.95]
    prev_luminance = -1.0
    for lightness in lightness_values:
        r, g, b = interpolate_ruby_ramp(lightness)
        lum = 0.2126 * r + 0.7152 * g + 0.0722 * b
        assert lum > prev_luminance
        prev_luminance = lum


def test_hue_shift_ratio_differentiation():
    """Verify hue shifting by checking green-to-red ratios across luminance tiers."""
    highlight = recolor_pixel(188, 252, 252, 255)
    midtone = recolor_pixel(45, 194, 191, 255)
    shadow = recolor_pixel(32, 139, 139, 255)

    assert (highlight[1] / highlight[0]) > 0.70
    assert (midtone[1] / midtone[0]) < 0.30
    assert (shadow[1] / shadow[0]) < 0.25
