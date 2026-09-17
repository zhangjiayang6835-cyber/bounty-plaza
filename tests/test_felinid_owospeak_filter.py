"""Unit tests for Felinid OwO-speak Speech Modification Subsystem.
Resolves Issue #684: [Bounty] [$30] Apply an owospeak speech filter to the felinid species.
"""

import pytest
from scripts.felinid_owospeak_filter import (
    FelinidOwospeakFilter,
    OWO_SUFFIXES,
)


@pytest.fixture
def filter_seeded():
    return FelinidOwospeakFilter(rng_seed=42)


def test_phoneme_transformation_rules(filter_seeded):
    """Verifies that 'r', 'l', and other phonemes are properly converted to 'w' and nya equivalents."""
    input_text = "Hello world, look at the real red robot!"
    res = filter_seeded.transform_phonemes(input_text)
    assert "Hewwo wowwd" in res
    assert "wook" in res
    assert "wed wobot" in res
    assert "r" not in res.lower()
    assert "l" not in res.lower()


def test_owo_emoticon_injection(filter_seeded):
    """Verifies that :3 and owo-isms are appended to speech sentences."""
    input_text = "Please give me some milk."
    res = filter_seeded.filter_speech(input_text)
    assert any(suffix in res for suffix in OWO_SUFFIXES)
    assert "Pwease" in res


def test_empty_and_whitespace_handling(filter_seeded):
    """Verifies that empty string or whitespace messages return gracefully without error."""
    assert filter_seeded.filter_speech("") == ""
    assert filter_seeded.filter_speech("   ") == "   "


def test_dm_species_patch_syntax(filter_seeded):
    """Verifies DreamMaker species patch generation contains required signal handlers and replacements."""
    dm_patch = filter_seeded.generate_dm_species_patch()
    assert "/datum/species/felinid" in dm_patch
    assert "replacetext(message, \"r\", \"w\")" in dm_patch
    assert "replacetext(message, \"l\", \"w\")" in dm_patch
    assert "pick(emotes)" in dm_patch
    assert ":3" in dm_patch
