"""Unit tests for TempleOS Compatibility and HolyC Subsystem Driver.
Resolves Issue #669: [BOUNTY][$640][FIX] Fix the compatibility issues with the TempleOS operating system.
"""

import os
import pytest
from scripts.templeos_compatibility_driver import (
    TempleOSCompatibilityDriver,
    TEMPLEOS_WIDTH,
    TEMPLEOS_HEIGHT,
    TEMPLEOS_16_COLOR_PALETTE,
    SUMERIAN_WELCOME_CUNEIFORM,
)


@pytest.fixture
def driver():
    return TempleOSCompatibilityDriver()


def test_templeos_vga_specifications(driver):
    """Verifies standard 640x480 resolution and 16-color palette fidelity."""
    assert TEMPLEOS_WIDTH == 640
    assert TEMPLEOS_HEIGHT == 480
    assert len(driver.palette) == 16
    assert driver.palette[1] == (0, 0, 170)  # Standard TempleOS Blue


def test_ancient_sumerian_greeting_cuneiform(driver):
    """Verifies greeting contains valid Cuneiform Unicode characters (U+12000 to U+123FF)."""
    cuneiform, translit = driver.get_sumerian_greeting()
    assert len(cuneiform) > 0
    assert "Silim-ma" in translit or "Welcome" in translit

    for ch in cuneiform:
        cp = ord(ch)
        assert 0x12000 <= cp <= 0x123FF, f"Character {ch} ({hex(cp)}) outside Cuneiform block"


def test_generate_title_screen_artifact(driver, tmp_path):
    """Verifies title screen image rendering, byte output, and DMI header generation."""
    out_file = str(tmp_path / "templeos_title.png")
    artifact = driver.create_title_screen(output_path=out_file)

    assert artifact.width == 640
    assert artifact.height == 480
    assert artifact.color_depth_bits == 4
    assert artifact.sumerian_greeting == SUMERIAN_WELCOME_CUNEIFORM
    assert os.path.exists(out_file)
    assert os.path.getsize(out_file) > 1000
    assert len(artifact.image_bytes) > 1000


def test_dmi_header_specification_format(driver):
    """Verifies BYOND DreamMaker .dmi metadata header format."""
    header = driver.generate_dmi_header(state_name="templeos_splash", width=640, height=480)
    assert "# BEGIN DMI" in header
    assert "version = 4.0" in header
    assert "width = 640" in header
    assert "height = 480" in header
    assert "state = \"templeos_splash\"" in header
    assert "# END DMI" in header


def test_dm_subsystem_shim_declarations(driver):
    """Verifies generated DM code contains subsystem controller hooks."""
    dm_code = driver.generate_dm_subsystem_shim()
    assert "/datum/controller/subsystem/templeos" in dm_code
    assert "var/vga_resolution_w = 640" in dm_code
    assert "var/vga_resolution_h = 480" in dm_code
    assert "render_title_screen" in dm_code
