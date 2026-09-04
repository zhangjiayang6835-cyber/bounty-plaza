"""Unit test suite for SS13 Station Event: The Metamorphosis by Franz Kafka (Issue #593)."""

import pytest
from scripts.ss13_metamorphosis_event import (
    InsectBehavior,
    KAFKA_DIE_VERWANDLUNG_TEXT,
    MetamorphosisStationEvent,
    SamsaInsectState,
)


def test_kafka_original_german_text_inclusion():
    """Verify that the entirety of Kafka's Die Verwandlung is included in the codebase."""
    assert "DIE VERWANDLUNG" in KAFKA_DIE_VERWANDLUNG_TEXT
    assert "Franz Kafka" in KAFKA_DIE_VERWANDLUNG_TEXT
    assert "ungeheuren Ungeziefer" in KAFKA_DIE_VERWANDLUNG_TEXT
    assert "Gregor Samsa" in KAFKA_DIE_VERWANDLUNG_TEXT
    assert len(KAFKA_DIE_VERWANDLUNG_TEXT) > 5000


def test_roundstart_gregor_samsa_transformation():
    event = MetamorphosisStationEvent()
    # Non-Gregor player should not transform
    res_normal = event.evaluate_roundstart_player("ckey_clown", "Honk McHonkerson", (100, 100, 1))
    assert res_normal is None
    assert len(event.active_insects) == 0

    # Player named Gregor Samsa must transform
    insect = event.evaluate_roundstart_player("ckey_samsa", "Gregor Samsa", (110, 140, 1))
    assert insect is not None
    assert insect.is_transformed is True
    assert insect.legs_count == 6
    assert insect.antennae_twitching is True
    assert "ckey_samsa" in event.active_insects
    assert len(event.event_log) == 1


def test_insect_crawl_around():
    event = MetamorphosisStationEvent()
    event.evaluate_roundstart_player("ckey_samsa", "Gregor Samsa", (100, 100, 1))

    crawl_res = event.crawl_around("ckey_samsa", (105, 108, 1), surface="ceiling")
    assert crawl_res["action"] == InsectBehavior.CRAWL_AROUND.value
    assert crawl_res["surface"] == "ceiling"
    assert crawl_res["new_coord"] == (105, 108, 1)
    assert event.active_insects["ckey_samsa"].current_coord == (105, 108, 1)


def test_insect_unnerve_people():
    event = MetamorphosisStationEvent()
    event.evaluate_roundstart_player("ckey_samsa", "Gregor Samsa", (100, 100, 1))

    nearby_crew = [
        ("ckey_grete", 102, 100),   # 2 tiles away -> within 4 tile radius
        ("ckey_father", 103, 100),  # 3 tiles away -> within 4 tile radius
        ("ckey_captain", 120, 120)  # 28 tiles away -> outside radius
    ]
    unnerved = event.unnerve_people("ckey_samsa", nearby_crew)
    assert len(unnerved) == 2
    assert unnerved[0]["target_ckey"] == "ckey_grete"
    assert unnerved[0]["horror_intensity"] > 0


def test_do_bug_things():
    event = MetamorphosisStationEvent()
    event.evaluate_roundstart_player("ckey_samsa", "Gregor Samsa", (100, 100, 1))

    res = event.do_bug_things("ckey_samsa", thing_type="chew_picture_frame")
    assert res["action"] == InsectBehavior.DO_BUG_THINGS.value
    assert "framed magazine clipping" in res["narrative"]

    res_brown = event.do_bug_things("ckey_samsa", thing_type="secrete_brown_liquid")
    assert "viscous brown trail" in res_brown["narrative"]


def test_get_neglected_by_family_and_apple_projectile():
    event = MetamorphosisStationEvent()
    event.evaluate_roundstart_player("ckey_samsa", "Gregor Samsa", (100, 100, 1))

    res = event.get_neglected_by_family("ckey_samsa", father_throws_apple=True)
    assert res["action"] == InsectBehavior.GET_NEGLECTED_BY_FAMILY.value
    assert res["apple_lodged_in_back"] is True
    assert event.active_insects["ckey_samsa"].apple_lodged_in_back is True
    assert event.active_insects["ckey_samsa"].carapace_integrity < 100.0


def test_map_and_dreammaker_exports():
    event = MetamorphosisStationEvent()
    maps = event.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "/obj/structure/bed/samsa_bed" in maps["IceBoxStation.dmm"]

    dm = event.export_dreammaker_code()
    assert "/datum/round_event_control/metamorphosis" in dm
    assert "/mob/living/simple_animal/hostile/vermin/gregor" in dm
