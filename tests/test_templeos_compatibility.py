"""Unit test suite for TempleOS Compatibility Engine and Ancient Sumerian Welcome Hook.
Tests Issue #746 requirements:
- 640x480 16-color VGA palette quantization and frame buffer operations.
- Ancient Sumerian cuneiform greeting & transliteration validation.
- TempleOS / HolyC client handshake detection and resolution lock.
- BYOND DM title screen and audio chime specification integrity.
"""

import pytest
from scripts.templeos_compatibility import (
    TempleOSColor,
    VGA_PALETTE,
    SUMERIAN_WELCOME_CUNEIFORM,
    SUMERIAN_TRANSLITERATION,
    SUMERIAN_ENGLISH,
    TempleOSDisplayBuffer,
    TempleOSCompatibilitySystem,
    DM_TEMPLEOS_COMPATIBILITY_SPEC,
)


def test_vga_palette_completeness():
    assert len(VGA_PALETTE) == 16
    for color in TempleOSColor:
        assert color in VGA_PALETTE
        r, g, b = VGA_PALETTE[color]
        assert 0 <= r <= 255 and 0 <= g <= 255 and 0 <= b <= 255


def test_nearest_templeos_color_quantization():
    # Pure red should map to TempleOS RED
    assert TempleOSCompatibilitySystem.nearest_templeos_color(255, 0, 0) == TempleOSColor.RED
    # Pure black should map to BLACK
    assert TempleOSCompatibilitySystem.nearest_templeos_color(0, 0, 0) == TempleOSColor.BLACK
    # Pure white should map to WHITE
    assert TempleOSCompatibilitySystem.nearest_templeos_color(255, 255, 255) == TempleOSColor.WHITE
    # Dark navy blue should map to BLUE
    assert TempleOSCompatibilitySystem.nearest_templeos_color(0, 0, 160) == TempleOSColor.BLUE


def test_templeos_framebuffer_primitives():
    buf = TempleOSDisplayBuffer(width=640, height=480)
    assert len(buf.buffer) == 480
    assert len(buf.buffer[0]) == 640

    # Draw pixel
    buf.plot_pixel(100, 100, TempleOSColor.YELLOW)
    assert buf.buffer[100][100] == int(TempleOSColor.YELLOW)

    # Draw rect
    buf.draw_rect(10, 10, 20, 20, TempleOSColor.RED)
    assert buf.buffer[15][15] == int(TempleOSColor.RED)
    assert buf.buffer[29][29] == int(TempleOSColor.RED)
    assert buf.buffer[30][30] != int(TempleOSColor.RED)


def test_ancient_sumerian_title_screen_payload():
    screen = TempleOSCompatibilitySystem.generate_sumerian_title_screen()
    assert screen["resolution"] == "640x480"
    assert screen["colors"] == 16
    assert "TempleOS" in screen["os_target"]
    assert "𒁲" in screen["cuneiform_banner"]
    assert "Silim-ma" in screen["transliteration"]
    assert "divine temple" in screen["translation"]
    assert len(screen["pc_speaker_chime_hz"]) == 4
    assert screen["status"] == "COMPATIBILITY_RESTORED_100_PERCENT"


def test_templeos_client_handshake_detection():
    handshake = TempleOSCompatibilitySystem.validate_client_handshake(
        user_agent="HolyC-GodOS/TempleOS-V5.03 (VGA; x86_64)",
        client_color_depth=4
    )
    assert handshake["is_templeos"] is True
    assert handshake["vga_16_color_enforced"] is True
    assert handshake["resolution_lock"] == (640, 480)
    assert handshake["redsea_fs_compatible"] is True
    assert handshake["allow_connection"] is True


def test_byond_dm_export_syntax():
    assert "/datum/templeos_manager" in DM_TEMPLEOS_COMPATIBILITY_SPEC
    assert "sumerian_greeting" in DM_TEMPLEOS_COMPATIBILITY_SPEC
    assert "640x480" in DM_TEMPLEOS_COMPATIBILITY_SPEC
    assert "/datum/title_screen/templeos_sumerian" in DM_TEMPLEOS_COMPATIBILITY_SPEC
