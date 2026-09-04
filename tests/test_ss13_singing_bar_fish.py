"""Unit tests for SS13 Animatronic Singing Bar Fish and Mr. Deempisi (Issue #587)."""

import pytest
from scripts.ss13_singing_bar_fish import (
    AnimatronicBarFish,
    FishMotionState,
    MrDeempisiBarflyMob,
    SONG_TAKE_ME_TO_THE_RIVER_LYRICS,
    StationBarSubsystem,
)


def test_singing_fish_activation_and_song_progression():
    fish = AnimatronicBarFish()
    assert fish.is_singing is False
    assert fish.motion_state == FishMotionState.IDLE
    assert fish.current_verse_index == 0

    # First button press: starts "Take me to the river..."
    res1 = fish.press_activation_button()
    assert res1["status"] == "SINGING_AND_DANCING"
    assert res1["lyric"] == SONG_TAKE_ME_TO_THE_RIVER_LYRICS[0]
    assert res1["motion"] == "full_dance"
    assert res1["audio_file"] == "take_me_to_the_river_sopranos.ogg"
    assert fish.current_verse_index == 1

    # Second button press: progresses to next verse
    res2 = fish.press_activation_button()
    assert res2["lyric"] == SONG_TAKE_ME_TO_THE_RIVER_LYRICS[1]
    assert fish.current_verse_index == 2

    # Verify battery consumption
    assert fish.battery_charge_pct < 100.0


def test_motion_sensor_trigger():
    fish = AnimatronicBarFish(wall_coord=(100, 100, 1))

    # Passerby 2 tiles away triggers motion sensor
    trigger_res = fish.detect_motion("ckey_bartender", (101, 101, 1))
    assert trigger_res is not None
    assert trigger_res["status"] == "SINGING_AND_DANCING"

    # Reset fish
    fish.stop_performance()

    # Passerby 10 tiles away does not trigger sensor
    no_trigger = fish.detect_motion("ckey_miner", (110, 110, 1))
    assert no_trigger is None


def test_mr_deempisi_mob_reaction():
    deempisi = MrDeempisiBarflyMob()
    assert deempisi.name == "Mr. Deempisi"
    assert deempisi.favorite_drink == "Old Fashioned"

    # React to iconic lyrics
    react1 = deempisi.react_to_singing_fish("Take me to the river, drop me in the water!")
    assert "classic" in react1["speech"].lower()

    react_oof = deempisi.react_to_singing_fish("Anyway... four dollars a pound! Oof Madone!")
    assert "oof, madone" in react_oof["speech"].lower()


def test_station_bar_subsystem_orchestration():
    subsystem = StationBarSubsystem()
    interaction = subsystem.trigger_bar_interaction("ckey_tony", action="press_button")

    assert interaction["actor"] == "ckey_tony"
    assert interaction["fish_performance"]["status"] == "SINGING_AND_DANCING"
    assert interaction["deempisi_reaction"] is not None
    assert len(subsystem.bar_logs) == 1


def test_map_and_dreammaker_exports():
    subsystem = StationBarSubsystem()
    maps = subsystem.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "/obj/item/wallmount/singing_bar_fish" in maps["IceBoxStation.dmm"]
    assert "/mob/living/simple_animal/npc/mr_deempisi" in maps["IceBoxStation.dmm"]

    dm = subsystem.export_dreammaker_code()
    assert "/obj/item/wallmount/singing_bar_fish" in dm
    assert "/mob/living/simple_animal/npc/mr_deempisi" in dm
