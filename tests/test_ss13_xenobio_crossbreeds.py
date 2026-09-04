"""Unit test suite for SS13 Xenobiology Crossbreeds Subsystem.
Verifies all 12 slime crossbreed thematic mechanics: charged green spiky cuticle,
bluespace warping coordinate displacement, sepia lengthened duration multipliers,
pink gentle bioluminescence, red destabilization forces, green mutative transmutations,
gold symbiot cytology organ hooks, oil 2010 Minecraft TNT detonating dynamics,
black transformative matrix rendering, pink loyal single-datum limits,
adamantine crystalline lattice room environmental energy effects, rainbow hyperchromatic buffs/drawbacks,
DMM map additions, and DreamMaker syntax exports.
Resolves Issue #629 ($130 USD).
"""

import pytest
from scripts.ss13_xenobio_crossbreeds import (
    SS13XenobioCrossbreedsEngine,
    SlimeColor,
    CrossbreedTheme,
    CarbonOrganismState
)


@pytest.fixture
def xenobio_engine():
    return SS13XenobioCrossbreedsEngine()


def test_charged_green_spiky_mechanics(xenobio_engine):
    res = xenobio_engine.apply_charged_green_spiky("test_carbon_spiky")
    assert res["theme"] == CrossbreedTheme.SPIKY.value
    assert res["is_spiky"] is True
    assert res["contact_brute_damage"] == 18.0
    assert res["can_wear_outer_suit"] is False
    # Verify state in carbon registry
    carbon = xenobio_engine.carbon_registry["test_carbon_spiky"]
    assert carbon.is_spiky is True
    assert carbon.can_wear_outer_suit is False


def test_bluespace_warping_displacement(xenobio_engine):
    origin = (100, 100, 1)
    res = xenobio_engine.apply_bluespace_warping(origin, SlimeColor.RED)
    assert res["theme"] == CrossbreedTheme.WARPING.value
    assert res["origin_coord"] == origin
    assert res["warped_coord"] != origin
    assert res["secondary_color"] == SlimeColor.RED.value


def test_sepia_lengthened_multipliers(xenobio_engine):
    res = xenobio_engine.apply_sepia_lengthened(base_duration_s=20.0, extract_potency=1.2)
    assert res["theme"] == CrossbreedTheme.LENGTHENED.value
    assert res["base_duration_s"] == 20.0
    # 20.0 * 2.5 * 1.2 = 60.0
    assert abs(res["lengthened_duration_s"] - 60.0) < 0.01


def test_pink_gentle_luminescence(xenobio_engine):
    res = xenobio_engine.apply_pink_gentle("peaceful_clown")
    assert res["theme"] == CrossbreedTheme.GENTLE.value
    assert res["luminescent_glow_radius"] == 5
    assert res["calming_aura_active"] is True


def test_red_destabilized_and_green_mutative(xenobio_engine):
    res_destab = xenobio_engine.apply_red_destabilized("titanium_wall", SlimeColor.ADAMANTINE)
    assert res_destab["theme"] == CrossbreedTheme.DESTABILIZED.value
    assert res_destab["destabilization_force"] == 100.0
    assert res_destab["integrity_lost_percent"] == 80.0

    res_mut = xenobio_engine.apply_green_mutative("iron_ingot", SlimeColor.GOLD)
    assert res_mut["theme"] == CrossbreedTheme.MUTATIVE.value
    assert "gold_chitin" in res_mut["result_object"]


def test_gold_symbiot_cytology_integration(xenobio_engine):
    res = xenobio_engine.apply_gold_symbiot("xenobiologist_alice", "neural_accelerator")
    assert res["theme"] == CrossbreedTheme.SYMBIOT.value
    assert res["cytology_integration"] is True
    assert "neural_accelerator" in res["symbiot_organ"]
    assert res["active_organs_count"] == 1


def test_oil_detonating_minecraft_tnt(xenobio_engine):
    res = xenobio_engine.apply_oil_detonating(fuse_seconds=4.0)
    assert res["theme"] == CrossbreedTheme.DETONATING.value
    assert res["explosion_flavor"] == "2010_MINECRAFT_TNT_RETRO_VOXEL"
    assert res["blast_yield"]["devastation_range"] == 2
    assert res["blast_yield"]["light_knockback_range"] == 7


def test_black_transformative_matrix_rendering(xenobio_engine):
    res = xenobio_engine.apply_black_transformative("morphed_subject", scale_x=2.0, scale_y=0.5)
    assert res["theme"] == CrossbreedTheme.TRANSFORMATIVE.value
    assert res["render_matrix"] == (2.0, 0.0, 0.0, 0.5)
    assert res["visual_aspect_ratio"] == 4.0


def test_pink_loyal_single_datum_limit(xenobio_engine):
    # First datum attachment succeeds
    res1 = xenobio_engine.apply_pink_loyal("sentient_toolbox", "loyal_friend_datum", {"loyalty_level": 100})
    assert res1["success"] is True
    assert res1["theme"] == CrossbreedTheme.LOYAL.value

    # Second datum attachment must be rejected (only one datum per object)
    res2 = xenobio_engine.apply_pink_loyal("sentient_toolbox", "secondary_buff_datum", {"power": 50})
    assert res2["success"] is False
    assert res2["reason"] == "STRICT_SINGLE_DATUM_LIMIT_EXCEEDED"


def test_adamantine_crystalline_room_energies(xenobio_engine):
    res = xenobio_engine.apply_adamantine_crystalline("Science_Main_Lab", metal_element="titanium", non_metal_element="silicon")
    assert res["theme"] == CrossbreedTheme.CRYSTALLINE.value
    assert "Titanium-Silicon" in res["structure"]
    assert res["room_effects"]["ambient_pressure_stabilization"] == 101.325
    assert "Science_Main_Lab" in xenobio_engine.room_crystal_energies


def test_rainbow_hyperchromatic_buff_and_drawback(xenobio_engine):
    res = xenobio_engine.apply_rainbow_hyperchromatic("transcendent_pilot")
    assert res["theme"] == CrossbreedTheme.HYPERCHROMATIC.value
    assert res["max_health"] == 150.0
    assert res["buff_active"] is True
    assert res["drawback_active"] is True
    assert res["heavy_drawback"] == "CELLULAR_HYPER_ENTROPY_NECROSIS"


def test_dmm_map_and_dreammaker_exports(xenobio_engine):
    dmm_dict = xenobio_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_dict
    assert "/obj/machinery/xenobio/crossbreed_centrifuge" in dmm_dict["IceBoxStation.dmm"]
    assert "/obj/item/slime_extract/charged_green/spiky" in dmm_dict["IceBoxStation.dmm"]

    dm_code = xenobio_engine.export_dreammaker_code()
    assert "/datum/slime_crossbreed" in dm_code
    assert "/datum/slime_crossbreed/spiky" in dm_code
    assert "/datum/slime_crossbreed/adamantine_crystalline" in dm_code
    assert "/datum/slime_crossbreed/hyperchromatic" in dm_code
