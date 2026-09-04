"""Comprehensive unit test suite for Cultivation Skill subsystem.
Tests Issue #678 requirements:
- Cultivation stages and thresholds (Qi Condensation to Heavenly Immortal)
- 7 cultivation paths (Feng Shui, meditation, extreme cold, training, acupuncture, herbs, lightning strikes)
- Martial arts scaling with cultivation rank
- Immunity to Aunt's Special Osmanthus Soup for trained cultivators
- Essence transfer between cultivators
- BYOND / DM export validation
"""

import pytest
from scripts.cultivation_skill import (
    CultivatorStats,
    CultivationStage,
    CultivationMethod,
    CultivationSystem,
    DM_CULTIVATION_SPEC,
)


def test_cultivation_stage_progression():
    cultivator = CultivatorStats(name="Zhang San")
    assert cultivator.stage == CultivationStage.MORTAL
    assert not cultivator.has_osmanthus_soup_immunity
    assert len(cultivator.unlocked_spells) == 0

    # Cultivate to Qi Condensation (>= 100 Qi)
    CultivationSystem.meditate(cultivator, duration_seconds=25.0)  # 125 Qi
    assert cultivator.stage == CultivationStage.QI_CONDENSATION
    assert "Qi Palm Blast" in cultivator.unlocked_spells
    assert not cultivator.has_osmanthus_soup_immunity

    # Cultivate to Foundation Establishment (>= 500 Qi)
    CultivationSystem.consume_herb_or_elixir(cultivator, "Dragon Marrow Pill")  # +450 Qi -> 575 Qi
    assert cultivator.stage == CultivationStage.FOUNDATION_ESTABLISHMENT
    assert "Celestial Spirit Barrier" in cultivator.unlocked_spells
    assert cultivator.has_osmanthus_soup_immunity is True


def test_all_seven_cultivation_methods():
    c = CultivatorStats(name="Li Feng")

    # 1. Feng Shui
    res1 = CultivationSystem.practice_feng_shui(c, "Harmonious North-Facing")
    assert res1["qi_gained"] == 35.0

    # 2. Meditation
    res2 = CultivationSystem.meditate(c, duration_seconds=10.0)
    assert res2["qi_gained"] == 50.0

    # 3. Extreme Cold Realm
    res3 = CultivationSystem.survive_extreme_cold(c, temperature_kelvin=60.0)
    assert res3["qi_gained"] > 0

    # 4. Rigorous Martial Training
    res4 = CultivationSystem.rigorous_training(c, reps=40)
    assert res4["qi_gained"] == 60.0

    # 5. Acupuncture
    res5 = CultivationSystem.acupuncture(c, silver_needles=10)
    assert res5["qi_gained"] == 120.0
    assert c.health == 120.0

    # 6. Herbs & Elixirs
    res6 = CultivationSystem.consume_herb_or_elixir(c, "Nine-Turn Golden Elixir")
    assert res6["qi_gained"] == 2500.0
    assert c.stage == CultivationStage.CORE_FORMATION

    # 7. Lightning Tribulation
    res7 = CultivationSystem.lightning_tribulation_strike(c)
    assert res7["consecutive_strikes"] == 1
    assert res7["qi_gained"] == 100.0


def test_consecutive_lightning_tribulation_exponential_reward():
    c = CultivatorStats(name="Lei Zhenzi")
    strike1 = CultivationSystem.lightning_tribulation_strike(c)
    strike2 = CultivationSystem.lightning_tribulation_strike(c)
    strike3 = CultivationSystem.lightning_tribulation_strike(c)

    assert strike1["consecutive_strikes"] == 1
    assert strike2["consecutive_strikes"] == 2
    assert strike3["consecutive_strikes"] == 3
    assert strike3["qi_gained"] > strike2["qi_gained"] > strike1["qi_gained"]
    assert c.health > 0  # Still alive


def test_aunts_special_osmanthus_soup_lethality_and_immunity():
    mortal = CultivatorStats(name="Unlucky Mortal")
    mortal_result = CultivationSystem.drink_aunt_osmanthus_soup(mortal)
    assert mortal_result["survived"] is False
    assert mortal.health == 0.0

    master = CultivatorStats(name="Immortal Elder")
    CultivationSystem.consume_herb_or_elixir(master, "Nine-Turn Golden Elixir")  # Foundation+
    assert master.has_osmanthus_soup_immunity is True

    master_result = CultivationSystem.drink_aunt_osmanthus_soup(master)
    assert master_result["survived"] is True
    assert master_result["damage"] == 0.0
    assert master.health == master.max_health


def test_martial_arts_strike_scaling():
    novice = CultivatorStats(name="Novice")
    novice_strike = CultivationSystem.execute_martial_arts_strike(novice, "Training Dummy")
    assert novice_strike["damage"] == 10.0

    immortal = CultivatorStats(name="Grandmaster")
    immortal.total_cultivated_qi = 16000.0
    immortal.update_stage()
    assert immortal.stage == CultivationStage.HEAVENLY_IMMORTAL

    immortal_strike = CultivationSystem.execute_martial_arts_strike(immortal, "Demon King")
    assert immortal_strike["damage"] > novice_strike["damage"] * 4.0
    assert immortal_strike["knockdown_seconds"] > 2.0


def test_essence_transfer_to_disciple():
    master = CultivatorStats(name="Master Gu", current_qi=1000.0, total_cultivated_qi=3000.0)
    master.update_stage()

    disciple = CultivatorStats(name="Young Disciple")
    assert disciple.stage == CultivationStage.MORTAL

    transfer_res = CultivationSystem.transfer_essence(master, disciple, 600.0)
    assert transfer_res["success"] is True
    assert master.current_qi == 400.0
    assert disciple.current_qi == 600.0
    assert disciple.stage == CultivationStage.FOUNDATION_ESTABLISHMENT


def test_byond_dm_export_contains_key_elements():
    assert "/datum/skill/cultivation" in DM_CULTIVATION_SPEC
    assert "drink_osmanthus_soup" in DM_CULTIVATION_SPEC
    assert "/datum/spell/targeted/qi_blast" in DM_CULTIVATION_SPEC
    assert "Qi Condensation" in DM_CULTIVATION_SPEC
