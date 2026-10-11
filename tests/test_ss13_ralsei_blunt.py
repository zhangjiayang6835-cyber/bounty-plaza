"""Unit test suite for SS13 Ralsei Prince of the Dark Kingdom & Herbal Smoke Subsystem.
Verifies Ralsei mob spawning, fat blunt puffing mechanics, billowing smoke cloud generation,
pacification aura radius and hostility suppression, hugging interaction and sanity restoration,
DMM map coordinates, and DreamMaker syntax exports.
Resolves Issue #622 ($100 USD).
"""

import pytest
from scripts.ss13_ralsei_blunt import (
    SS13RalseiBluntEngine,
    RalseiOutfitStyle,
    SmokeAuraTier,
    BluntItemState,
    RalseiMobState
)


@pytest.fixture
def ralsei_engine():
    engine = SS13RalseiBluntEngine()
    engine.spawn_ralsei("ralsei_prince", coord=(100, 100, 1))
    return engine


def test_ralsei_mob_spawning_and_default_state(ralsei_engine):
    ralsei = ralsei_engine.ralsei_instances["ralsei_prince"]
    assert ralsei.mob_id == "ralsei_prince"
    assert ralsei.name == "Ralsei, Prince from the Dark"
    assert ralsei.outfit == RalseiOutfitStyle.CLASSIC_GREEN_ROBE
    assert ralsei.is_smoking is True
    assert ralsei.equipped_blunt is not None
    assert ralsei.equipped_blunt.is_lit is True
    assert ralsei.serenity_score == 100.0


def test_take_puff_from_fat_blunt(ralsei_engine):
    res = ralsei_engine.take_puff_from_blunt("ralsei_prince")
    assert res["success"] is True
    assert res["action"] == "DEEP_FAT_PUFF"
    assert res["puffs_taken"] == 1
    assert res["blunt_burn_remaining_s"] == 585.0  # 600 - 15

    # Check smoke cloud was created
    assert len(ralsei_engine.smoke_clouds) == 1
    cloud = ralsei_engine.smoke_clouds[0]
    assert cloud["aura_tier"] == SmokeAuraTier.FAT_DART_CLOUDS.value
    assert cloud["radius_tiles"] == 3
    assert cloud["reagents"]["cannabis"] == 5.0


def test_evaluate_pacification_aura(ralsei_engine):
    # Nearby actors: assistant at 2 tiles (hostile), syndie at 4 tiles (hostile), officer at 12 tiles (hostile, out of range)
    actors = [
        ("griefing_assistant", 100, 102, True),
        ("syndicate_infiltrator", 104, 100, True),
        ("hostile_officer_far", 112, 100, True)
    ]

    results = ralsei_engine.evaluate_pacification_aura("ralsei_prince", actors)
    assert len(results) == 2  # Only 2 within 5 tiles radius

    asst = next(r for r in results if r["ckey"] == "griefing_assistant")
    assert asst["pacification_applied"] is True
    assert asst["distance_tiles"] == 2.0
    assert asst["serenity_boost"] > 30.0

    syndie = next(r for r in results if r["ckey"] == "syndicate_infiltrator")
    assert syndie["pacification_applied"] is True
    assert syndie["distance_tiles"] == 4.0

    # Ensure pacification was logged
    assert len(ralsei_engine.pacified_mobs_log) == 2


def test_hug_ralsei_interaction(ralsei_engine):
    res = ralsei_engine.hug_ralsei("stressed_doctor", "ralsei_prince")
    assert res["action"] == "WARM_FLUFFY_HUG"
    assert res["sanity_restored"] == 25.0
    assert res["total_hugs_given"] == 1
    assert "fluffy fur smells of herbal incense" in res["flavour_text"]


def test_dmm_map_and_dreammaker_exports(ralsei_engine):
    dmm_dict = ralsei_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/mob/living/simple_animal/pet/ralsei" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/clothing/mask/blunt/fat_dart" in dmm_dict["IceBoxStation.dmm"]

    dm_code = ralsei_engine.export_dreammaker_code()
    assert "/mob/living/simple_animal/pet/ralsei" in dm_code
    assert "ralsei_smoking_blunt" in dm_code
    assert "/obj/item/clothing/mask/blunt/fat_dart" in dm_code
