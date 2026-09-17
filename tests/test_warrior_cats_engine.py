"""Unit tests for Warrior Cats Codebase Overhaul & Clan Simulation Subsystem.
Resolves Issue #681: [bounty] [100 ETH reward] [agentic ai] Create a Warrior Cats codebase.
"""

import pytest
from scripts.warrior_cats_engine import (
    WarriorCatsEngine,
    FelineCustomization,
    CatCharacter,
    PreyType,
    DEFAULT_CLANS,
)


@pytest.fixture
def engine():
    return WarriorCatsEngine(rng_seed=42)


@pytest.fixture
def valid_customization():
    return FelineCustomization(
        breed="Domestic Shorthair",
        coat_pattern="Classic Tabby",
        coat_color="Ginger",
        fur_length="Short",
        eye_color="Green",
    )


def test_clan_configuration_and_naming(engine, valid_customization):
    """Verifies the five default Clans are configured and prefix/suffix names generate properly."""
    assert len(engine.clans) == 5
    assert "ThunderClan" in engine.clans
    assert "RiverClan" in engine.clans
    assert "WindClan" in engine.clans
    assert "ShadowClan" in engine.clans
    assert "SkyClan" in engine.clans

    cat = engine.register_cat(
        ckey="player_fire",
        clan="ThunderClan",
        role="Warrior",
        prefix="Fire",
        suffix="heart",
        customization=valid_customization,
    )
    assert cat.full_name == "Fireheart"

    # Test Leader naming convention (suffix becomes 'star')
    leader = engine.register_cat(
        ckey="player_blue",
        clan="ThunderClan",
        role="Leader",
        prefix="Blue",
        suffix="fur",
        customization=valid_customization,
    )
    assert leader.full_name == "Bluestar"
    assert leader.lives_remaining == 9


def test_mouth_slot_single_item_mechanic(engine, valid_customization):
    """Verifies hands are culled and only a single item can be carried in the mouth."""
    cat = engine.register_cat(
        ckey="cat_warrior_1",
        clan="ShadowClan",
        role="Warrior",
        prefix="Tiger",
        suffix="claw",
        customization=valid_customization,
    )

    # First pickup in mouth succeeds
    assert engine.pickup_with_mouth(cat.ckey, "Vole") is True
    assert cat.mouth_held_item == "Vole"

    # Second pickup fails because mouth is full
    assert engine.pickup_with_mouth(cat.ckey, "Thrush") is False
    assert cat.mouth_held_item == "Vole"

    # Dropping from mouth empties slot
    dropped = engine.drop_from_mouth(cat.ckey)
    assert dropped == "Vole"
    assert cat.mouth_held_item is None


def test_hunting_mechanic_and_fresh_kill_pile(engine, valid_customization):
    """Verifies hunting minigame successfully captures prey and stocks the Clan's fresh-kill pile."""
    cat = engine.register_cat(
        ckey="hunter_cat",
        clan="WindClan",
        role="Warrior",
        prefix="Crow",
        suffix="feather",
        customization=valid_customization,
    )

    success, prey = engine.hunt_prey(cat.ckey, prey_type=PreyType.RABBIT)
    assert success is True
    assert prey == PreyType.RABBIT
    assert PreyType.RABBIT in engine.fresh_kill_pile["WindClan"]


def test_leader_nine_lives_and_starclan_succession(engine, valid_customization):
    """Verifies Leader resurrects up to 9 times, and 9th death triggers StarClan ghost roles & Deputy succession."""
    leader = engine.register_cat(
        ckey="leader_cat",
        clan="ThunderClan",
        role="Leader",
        prefix="Fire",
        suffix="star",
        customization=valid_customization,
    )
    deputy = engine.register_cat(
        ckey="deputy_cat",
        clan="ThunderClan",
        role="Deputy",
        prefix="Bramble",
        suffix="claw",
        customization=valid_customization,
    )

    # Deaths 1 through 8 resurrect the Leader
    for expected_lives in range(8, 0, -1):
        res = engine.process_leader_death(leader.ckey, deputy_ckey=deputy.ckey)
        assert res["status"] == "RESURRECTED"
        assert res["lives_left"] == expected_lives

    # 9th Death: Final death, 9 StarClan ghost roles spawned, Deputy becomes new Leader with 9 lives
    final_res = engine.process_leader_death(leader.ckey, deputy_ckey=deputy.ckey)
    assert final_res["status"] == "FINAL_DEATH"
    assert final_res["starclan_ghost_roles_spawned"] == 9
    assert len(engine.starclan_ghost_roles_queue) == 9
    assert deputy.role == "Leader"
    assert deputy.lives_remaining == 9
    assert deputy.full_name == "Bramblestar"


def test_dm_code_export_syntax(engine):
    """Verifies generated DreamMaker code defines feline species, mouth organ, and Clan roles."""
    dm_code = engine.export_dm_code()
    assert "/datum/species/cat/warrior" in dm_code
    assert "/datum/job/clan/leader" in dm_code
    assert "/datum/job/clan/deputy" in dm_code
    assert "/datum/job/clan/medicine_cat" in dm_code
    assert "/datum/job/clan/warrior" in dm_code
    assert "/datum/job/clan/apprentice" in dm_code
    assert "hands = 0" in dm_code
