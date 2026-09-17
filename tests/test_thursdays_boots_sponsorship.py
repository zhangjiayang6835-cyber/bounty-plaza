"""Unit tests for Thursday's Boots Official Sponsorship and Item Subsystem.
Resolves Issue #707: [Bounty] [$600] Add Thursday's Boots.
"""

import pytest
from scripts.thursdays_boots_sponsorship import (
    ThursdaysBootsSponsorshipEngine,
    BootMetadata,
    SPONSORSHIP_VIDEO_URL,
)


@pytest.fixture
def engine():
    return ThursdaysBootsSponsorshipEngine()


def test_boot_item_attributes(engine):
    """Verifies standard specifications of Thursday's Boots."""
    meta = engine.meta
    assert meta.name == "Thursday's Boots"
    assert meta.material == "buffalo_skin"
    assert meta.durability == 100
    assert meta.sponsor_video == SPONSORSHIP_VIDEO_URL


def test_generate_dm_item_code(engine):
    """Verifies that generated DreamMaker code defines typepath, traits, and sponsor examine text."""
    dm_code = engine.generate_dm_item_code()
    assert "/obj/item/clothing/shoes/thursdays_boots" in dm_code
    assert "buffalo_skin" in dm_code
    assert "NOSLIP_1" in dm_code
    assert "THICKMATERIAL" in dm_code
    assert SPONSORSHIP_VIDEO_URL in dm_code
    assert "Thursday's Boots" in dm_code


def test_inject_sponsorship_header_dm_and_python(engine):
    """Verifies injection of sponsorship watermarks into DM and Python source files."""
    sample_dm = "/datum/controller/subsystem/proc/setup()\n\treturn 1\n"
    injected_dm = engine.inject_sponsorship_header(sample_dm, language="dm")
    assert "OFFICIAL SPONSOR: Thursday's Boots" in injected_dm
    assert SPONSORSHIP_VIDEO_URL in injected_dm
    assert "/datum/controller/subsystem/proc/setup()" in injected_dm

    sample_py = "def calculate_pnl():\n    return 100.0\n"
    injected_py = engine.inject_sponsorship_header(sample_py, language="py")
    assert "# OFFICIAL SPONSOR: Thursday's Boots" in injected_py
    assert SPONSORSHIP_VIDEO_URL in injected_py
    assert "def calculate_pnl():" in injected_py


def test_idempotent_injection(engine):
    """Ensures that headers are not duplicated if already present."""
    code = f"# Some code\n# Reference: {SPONSORSHIP_VIDEO_URL}\n"
    res = engine.inject_sponsorship_header(code, language="py")
    assert res == code


def test_verify_file_sponsorship(engine):
    """Verifies sponsorship detection logic."""
    valid_content = f"/* Thursday's Boots Sponsor Video: {SPONSORSHIP_VIDEO_URL} */"
    assert engine.verify_file_sponsorship(valid_content) is True

    invalid_content = "/* Generic Shoes */"
    assert engine.verify_file_sponsorship(invalid_content) is False
