"""Unit tests for Tung Tung Tung Sahur Antagonist Engine.
Resolves Issue #657: [BOUNTY][$67] Add the Tung Tung Tung Sahur antagonist.
Upstream Reference: Iamgoofball/-tg-station#213.
"""

import pytest
from scripts.tung_tung_tung_sahur import (
    TungTungTungSahur,
    Sprite32x32,
    PARIS_PEACE_ACCORDS_1947_ARTICLES,
    TUNG_SAHUR_CHANTS,
)


@pytest.fixture
def sahur_antag():
    return TungTungTungSahur(ckey="TungPlayer1")


def test_sprite_dimensions_and_quadrants():
    sprite = Sprite32x32()
    assert sprite.width == 32
    assert sprite.height == 32
    assert len(sprite.quadrants) == 4
    assert "top_left" in sprite.quadrants
    assert "top_right" in sprite.quadrants
    assert "bottom_left" in sprite.quadrants
    assert "bottom_right" in sprite.quadrants

    ascii_grid = sprite.render_ascii()
    lines = ascii_grid.splitlines()
    assert len(lines) == 32
    for line in lines:
        assert len(line) == 32
        # Contains quadrants 1, 2, 3, or 4
        assert set(line).issubset({"1", "2", "3", "4"})


def test_paris_peace_accords_citation(sahur_antag):
    # Deterministic quote check
    quote_0 = sahur_antag.quote_paris_peace_accord(fixed_article_index=0)
    assert "Paris Peace Accords of 1947" in quote_0
    assert "Article 15" in quote_0

    quote_1 = sahur_antag.quote_paris_peace_accord(fixed_article_index=1)
    assert "Free Territory of Trieste" in quote_1
    assert "Article 21" in quote_1

    # Random quote check
    quote_rnd = sahur_antag.quote_paris_peace_accord()
    assert any(art[:15] in quote_rnd for art in PARIS_PEACE_ACCORDS_1947_ARTICLES)
    assert len(sahur_antag.speech_history) >= 3


def test_sahur_lore_chant(sahur_antag):
    chant = sahur_antag.chant_sahur_lore(fixed_chant_index=0)
    assert "TUNG TUNG TUNG SAHUR!" in chant
    assert chant in sahur_antag.speech_history


def test_theme_music_playback(sahur_antag):
    assert sahur_antag.music_playing is False

    play_res = sahur_antag.start_theme_music(volume=85)
    assert play_res["status"] == "PLAYING"
    assert play_res["volume"] == 85
    assert "tung_tung_sahur_theme.ogg" in play_res["track"]
    assert sahur_antag.music_playing is True

    stop_res = sahur_antag.stop_theme_music()
    assert stop_res["status"] == "STOPPED"
    assert sahur_antag.music_playing is False


def test_strike_with_bat_combat(sahur_antag):
    strike_res = sahur_antag.strike_with_bat("Sleeping Assistant", quote_index=2)
    assert strike_res["status"] == "BAT_STRIKE_LANDED"
    assert strike_res["target"] == "Sleeping Assistant"
    assert strike_res["damage"] == 30.0
    assert strike_res["sound_effect"] == "*TUNG! BONK!*"
    assert "Article 47" in strike_res["treaty_quote"]
    assert "TUNG TUNG TUNG SAHUR!" in strike_res["lore_chant"]


def test_dreammaker_export_syntax(sahur_antag):
    dm_code = sahur_antag.export_dreammaker_code()
    assert "/mob/living/carbon/human/tung_sahur" in dm_code
    assert "/obj/item/melee/tung_bat" in dm_code
    assert "tung_tung_sahur_theme.ogg" in dm_code
    assert "hitsound = 'sound/weapons/tung_bonk.ogg'" in dm_code
