"""Unit tests for Tung Tung Tung Sahur Antagonist Subsystem (Issue #747 - $67 USD)."""

import os
import pytest
from scripts.tung_tung_tung_sahur import (
    TungTungTungSahur,
    Sprite32x32,
    SahurBat,
    SahurThemeMusic,
    PARIS_PEACE_ACCORDS_1947,
)


def test_sprite_dimensions_and_quadrants():
    sprite = Sprite32x32()
    assert sprite.width == 32
    assert sprite.height == 32
    assert len(sprite.quadrants) == 4
    assert sprite.get_pixel(0, 0) == "#8B4513"       # Top-left quadrant
    assert sprite.get_pixel(31, 0) == "#D2691E"      # Top-right quadrant
    assert sprite.get_pixel(0, 31) == "#4B5320"      # Bottom-left quadrant
    assert sprite.get_pixel(31, 31) == "#1C1C1C"     # Bottom-right quadrant

    with pytest.raises(IndexError):
        sprite.get_pixel(32, 32)

    metadata = sprite.export_dmi_metadata()
    assert metadata["version"] == "4.0"
    assert "tung_sahur_strike" in metadata["states"]


def test_sahur_bat_attributes_and_strike():
    bat = SahurBat()
    assert bat.name == "Tung Sahur Bat"
    assert bat.force == 24
    assert bat.throwforce == 15
    assert bat.w_class == 3
    assert bat.sound_effect.endswith("tung_tung_tung.ogg")

    strike_res = bat.strike("Captain")
    assert strike_res["action"] == "STRIKE"
    assert strike_res["target"] == "Captain"
    assert strike_res["force_dealt"] == 24
    assert strike_res["chant"] == "TUNG! TUNG! TUNG! SAHUR!"


def test_sahur_theme_music_specification():
    music = SahurThemeMusic()
    assert music.bpm == 148
    assert music.loop is True
    assert music.audio_path.endswith("tung_tung_tung_sahur.ogg")

    cfg = music.get_playback_config()
    assert cfg["bpm"] == 148
    assert cfg["looping"] is True
    assert cfg["volume"] == 85


def test_paris_peace_accords_quotes_corpus():
    assert len(PARIS_PEACE_ACCORDS_1947) >= 9
    for entry in PARIS_PEACE_ACCORDS_1947:
        assert "treaty" in entry
        assert "article" in entry
        assert "text" in entry
        assert len(entry["text"]) > 20

    antagonist = TungTungTungSahur()
    # Test deterministic indexing
    q0 = antagonist.quote_paris_accords(index=0)
    assert "Treaty of Peace with Italy (1947)" in q0["treaty"]
    assert "Preamble" in q0["article"]
    assert "Tripartite Pact" in q0["quote"]

    q1 = antagonist.quote_paris_accords(index=1)
    assert "Article 15" in q1["article"]
    assert "human rights" in q1["quote"]


def test_trigger_wake_call_and_chant():
    antagonist = TungTungTungSahur()
    call = antagonist.trigger_wake_call()
    assert call["speaker"] == "Tung Tung Tung Sahur"
    assert "TUNG" in call["chant"] or "SAHUR" in call["chant"]
    assert "In accordance with" in call["accord_quote"]
    assert call["sound"].endswith("tung_tung_tung.ogg")
    assert "Percussion of Paris 1947" in call["music_playing"]


def test_byond_dm_export():
    antagonist = TungTungTungSahur()
    dm_code = antagonist.generate_byond_dm_code()
    assert "/mob/living/simple_animal/hostile/tung_sahur" in dm_code
    assert "/obj/item/weapon/sahur_bat" in dm_code
    assert "maxHealth = 250" in dm_code
    assert "tung_tung_tung.ogg" in dm_code
