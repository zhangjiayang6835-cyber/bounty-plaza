"""Unit tests for Tung Tung Tung Sahur Antagonist, Bat Weapon, and Paris Peace Accords Integration.
Resolves Issue #747: [BOUNTY][$67] Add the Tung Tung Tung Sahur antagonist.
"""

import numpy as np
import pytest
from scripts.tung_tung_sahur import (
    TungTungTungSahurAntagonist,
    TungSahurSpriteSet,
    SahurBat,
    PARIS_PEACE_ACCORDS_1947_QUOTES,
    SAHUR_CRIES,
    DM_TUNG_TUNG_SAHUR_SPEC,
)


@pytest.fixture
def sahur_antag():
    return TungTungTungSahurAntagonist()


def test_sprite_generation_and_four_squares_segmentation():
    """Verifies that the character sprite is 32x32 RGBA and partitioned into four distinct square regions."""
    sprites = TungSahurSpriteSet.generate()
    mob = sprites.mob_sprite
    bat = sprites.bat_sprite

    assert mob.shape == (32, 32, 4)
    assert bat.shape == (32, 32, 4)
    assert mob.dtype == np.uint8
    assert bat.dtype == np.uint8

    # Verify 4 distinct color quadrants exist and have non-zero alpha
    # Q1: top-left (r=5, c=5)
    assert mob[5, 5, 3] == 255
    # Q2: top-right (r=5, c=20)
    assert mob[5, 20, 3] == 255
    # Q3: bottom-left (r=20, c=5)
    assert mob[20, 5, 3] == 255
    # Q4: bottom-right (r=20, c=20)
    assert mob[20, 20, 3] == 255

    # Check color distinctness between quadrants
    assert not np.array_equal(mob[5, 5, :3], mob[5, 20, :3])
    assert not np.array_equal(mob[20, 5, :3], mob[20, 20, :3])

    # Verify bat has non-zero pixels
    assert np.sum(bat[:, :, 3] > 0) >= 20


def test_paris_peace_accords_quotes_random_speech(sahur_antag):
    """Verifies that dialogue includes authentic 1947 Paris Peace Accords articles and Sahur shouts."""
    spoken_samples = [sahur_antag.speak(rng_seed=i) for i in range(50)]

    # Must contain both Sahur cries and Paris Peace Accords quotes
    has_sahur_cry = any(any(cry in s for cry in ["Tung", "Sahur"]) for s in spoken_samples)
    has_peace_accord = any("Article" in s for s in spoken_samples)

    assert has_sahur_cry is True
    assert has_peace_accord is True

    # Validate specific historical treaty articles are present in quotes library
    assert any("Trieste" in q for q in PARIS_PEACE_ACCORDS_1947_QUOTES)
    assert any("Libya, Eritrea" in q for q in PARIS_PEACE_ACCORDS_1947_QUOTES)
    assert any("atomic weapons" in q for q in PARIS_PEACE_ACCORDS_1947_QUOTES)


def test_sahur_bat_combat_and_knockdown():
    """Verifies bat melee force, stamina drain, and knockdown delivery."""
    bat = SahurBat()
    res = bat.attack("Clown")

    assert res["target"] == "Clown"
    assert res["damage_dealt"] == 20.0
    assert res["stamina_damage"] == 35.0
    assert res["knockdown_applied"] == 2.0
    assert "tung_hit.ogg" in res["sound"]


def test_wake_up_call_and_theme_music(sahur_antag):
    """Verifies theme music playback and wake-up effect on sleeping targets."""
    sleepers = ["Chief Medical Officer", "Captain", "Janitor"]
    wake_result = sahur_antag.perform_sahur_wake_up_call(sleepers)

    assert wake_result["theme_music_playing"] == "sound/music/tung_tung_sahur.ogg"
    assert len(wake_result["targets_awakened"]) == 3
    for target_status in wake_result["targets_awakened"]:
        assert target_status["status"] == "awakened"
        assert target_status["caffeinated_buff"] is True


def test_dm_specification_export():
    """Verifies TGStation DM / BYOND definition integrity."""
    assert "/datum/antagonist/tung_tung_sahur" in DM_TUNG_TUNG_SAHUR_SPEC
    assert "/obj/item/melee/tung_bat" in DM_TUNG_TUNG_SAHUR_SPEC
    assert "tung_tung_sahur.ogg" in DM_TUNG_TUNG_SAHUR_SPEC
    assert "Paris Peace Accords" in DM_TUNG_TUNG_SAHUR_SPEC
