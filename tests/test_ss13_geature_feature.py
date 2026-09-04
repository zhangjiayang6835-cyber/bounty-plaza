"""Unit tests for SS13 2D-Action Combat & Dismemberment Engine (Plin's Geature Feature).
Resolves Issue #612: [BOUNTY] [AGENT READY] [$300USD] add a geature feature.
"""

import pytest
from scripts.ss13_geature_feature import (
    GameZone,
    PlayerRole,
    LocomotionState,
    LimbStatus,
    PlinPlayerCharacter,
    GeatureFeatureActionEngine,
)


def test_player_role_initialization_and_inventory():
    engine = GeatureFeatureActionEngine()
    traitor = engine.add_player("ckey_traitor", PlayerRole.TRAITOR, "Boris The Traitor")
    assert "energy_crossbow" in traitor.inventory
    assert "energy_sword" in traitor.inventory
    assert traitor.zone == GameZone.STATION_MAIN

    operative = engine.add_player("ckey_operative", PlayerRole.OPERATIVE, "Operative Striker")
    assert "syndicate_smg" in operative.inventory
    assert operative.zone == GameZone.SYNDICATE_BASE


def test_arm_dismemberment_and_bleeding():
    player = PlinPlayerCharacter(ckey="test_player", role=PlayerRole.CREW)
    res = player.take_dismemberment("arm")
    assert res["status"] == "ARM_SEVERED"
    assert player.limbs.has_right_arm is False
    assert player.bleed_rate_per_sec > 0

    # Bleed tick drains health
    tick_res = player.process_tick(delta_s=2.0)
    assert tick_res["status"] == "ALIVE"
    assert player.health < 100.0


def test_leg_dismemberment_crawling_and_office_chair_rolling():
    player = PlinPlayerCharacter(ckey="test_runner", role=PlayerRole.CREW)
    # Sever both legs
    player.take_dismemberment("leg")
    player.take_dismemberment("leg")
    assert player.limbs.has_right_leg is False
    assert player.limbs.has_left_leg is False

    # Without chair -> crawling
    assert player.get_locomotion_state() == LocomotionState.CRAWLING

    # Mount office chair -> wheelchair rolling ("на стуле котаться")
    player.has_office_chair = True
    assert player.get_locomotion_state() == LocomotionState.WHEELCHAIR_ROLLING


def test_eye_gouging_and_half_screen_blindness():
    player = PlinPlayerCharacter(ckey="test_sight", role=PlayerRole.CREW)
    assert player.vision_field_pct == 100.0

    res = player.take_dismemberment("eye")
    assert res["status"] == "EYE_GOUGED"
    # Half screen visible ("пол экрана не видеть")
    assert player.vision_field_pct == 50.0

    # Gouge other eye -> total blindness
    player.take_dismemberment("eye")
    assert player.vision_field_pct == 0.0


def test_prosthesis_installation():
    player = PlinPlayerCharacter(ckey="test_cyborg", role=PlayerRole.CREW)
    player.take_dismemberment("arm")
    player.take_dismemberment("leg")
    player.take_dismemberment("eye")

    # Install cybernetic prostheses
    res_arm = player.install_prosthesis("arm_prosthesis")
    assert res_arm["status"] == "ARM_PROSTHESIS_INSTALLED"

    res_leg = player.install_prosthesis("leg_prosthesis")
    assert res_leg["status"] == "LEG_PROSTHESIS_INSTALLED"
    assert player.get_locomotion_state() == LocomotionState.NORMAL_WALKING

    res_eye = player.install_prosthesis("eye_prosthesis")
    assert res_eye["status"] == "EYE_PROSTHESIS_INSTALLED"
    assert player.vision_field_pct == 100.0


def test_death_and_2d_ghost_transition():
    player = PlinPlayerCharacter(ckey="test_fatal", role=PlayerRole.CREW, health=5.0, bleed_rate_per_sec=10.0)
    res = player.process_tick(delta_s=1.0)
    assert res["status"] == "PLAYER_DIED_FROM_BLOODLOSS"
    assert res["transition"] == "BECOME_2D_GHOST"
    assert player.is_alive is False
    assert player.is_ghost_2d is True


def test_rob_shuttle_and_order_cargo():
    engine = GeatureFeatureActionEngine()
    operative = engine.add_player("ckey_op", PlayerRole.OPERATIVE, "Shuttle Raider")

    res_shuttle = engine.rob_cargo_shuttle("ckey_op")
    assert res_shuttle["status"] == "SHUTTLE_ROBBED"
    assert engine.cargo_shuttle_robbed is True
    assert "combat_shotguns" in operative.inventory

    res_cargo = engine.order_cargo("medical_supplies_crate")
    assert res_cargo["status"] == "CARGO_ORDERED"
    assert "medical_supplies_crate" in engine.cargo_order_queue


def test_operative_arm_nuke_and_multiplayer_save_prohibition():
    engine = GeatureFeatureActionEngine()
    crew = engine.add_player("ckey_crew", PlayerRole.CREW, "Janitor")
    op = engine.add_player("ckey_op", PlayerRole.OPERATIVE, "Commander")

    # Crew cannot arm nuke
    with pytest.raises(PermissionError):
        engine.operative_arm_nuclear_bomb("ckey_crew")

    # Operative arms nuke
    res_nuke = engine.operative_arm_nuclear_bomb("ckey_op")
    assert res_nuke["status"] == "NUKE_ARMED"
    assert engine.nuke_bomb_armed is True

    # Saving game is strictly impossible in multiplayer ("Сохранятся нельзя, так как мультеплеер")
    with pytest.raises(NotImplementedError, match="Сохранятся нельзя, так как мультеплеер"):
        engine.attempt_save_game()
