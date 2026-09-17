"""Unit and integration tests for Extraction Shooter Gamemode, Godot Bridge, and Ballistics.
Resolves Issue #685: [BOUNTY] [$3000] Secondary extraction shooter gamemode.
"""

import json
import pytest
from scripts.extraction_shooter import (
    Contractor,
    ExtractionShooterGameMode,
    ExtractionZone,
    GodotByondBridge,
    LootItem,
    RaidState,
    WeaponSpec,
    DM_EXTRACTION_SHOOTER_SPEC,
)


@pytest.fixture
def fresh_raid():
    raid = ExtractionShooterGameMode(raid_duration_seconds=300.0)
    contractor = Contractor(
        id="PMC-001",
        name="Operator Vance",
        x=95,
        y=95,
        health=100.0,
        armor=50.0,
        inventory=[
            LootItem(id="intel_drive", name="Encrypted Intel Drive", value_credits=2500, weight_kg=0.5),
            LootItem(id="military_medkit", name="Combat Stimpack", value_credits=800, weight_kg=1.2),
        ],
    )
    raid.register_contractor(contractor)
    return raid, contractor


def test_ballistic_firing_and_armor_penetration():
    """Verifies weapon ballistics, AP calculations, and magazine depletion."""
    weapon = WeaponSpec(
        name="SR-25 DMR",
        caliber="7.62x51mm M61 AP",
        damage=65.0,
        armor_penetration=0.85,
        fire_rate_rpm=450,
        mag_capacity=20,
        current_mag=20,
        recoil_factor=1.8,
    )

    # Fire at heavily armored target (75 armor)
    res = weapon.fire(target_armor_val=75.0)
    assert res["fired"] is True
    assert res["rounds_left"] == 19
    assert res["damage"] >= 20.0
    assert res["sound"] == "sound/weapons/tactical_shot.ogg"

    # Deplete magazine and verify empty firing fails
    weapon.current_mag = 0
    empty_res = weapon.fire(target_armor_val=50.0)
    assert empty_res["fired"] is False
    assert empty_res["reason"] == "empty_magazine"

    # Reload
    reloaded = weapon.reload(15)
    assert reloaded == 15
    assert weapon.current_mag == 15


def test_extraction_countdown_and_successful_exfil(fresh_raid):
    """Verifies that remaining in an exfil zone completes countdown and secures loot."""
    raid, contractor = fresh_raid
    # Contractor starts at (95, 95), which is inside "exfil_bunker" AABB (90, 90, 100, 100)

    # Step 1: Step into zone (dt=2.0s) -> Countdown active (remaining 3.0s)
    res1 = raid.process_extraction(contractor.id, dt=2.0)
    assert res1["status"] == "extracting"
    assert res1["remaining"] == 3.0
    assert contractor.is_extracted is False

    # Step 2: Remain for another 3.0s (total 5.0s >= 5.0s required) -> Extraction successful
    res2 = raid.process_extraction(contractor.id, dt=3.0)
    assert res2["status"] == "extracted"
    assert res2["zone"] == "Deep Bunker Gate"
    assert res2["loot_secured"] == 2
    assert res2["total_credits"] == 3300  # 2500 + 800
    assert contractor.is_extracted is True


def test_gated_exfil_requires_item(fresh_raid):
    """Verifies that an exfil zone requiring an item (e.g. flare) rejects extraction if missing."""
    raid, contractor = fresh_raid
    # Move contractor to emergency helipad (requires "green_flare")
    contractor.x = 15
    contractor.y = 85

    res = raid.process_extraction(contractor.id, dt=1.0)
    assert res["status"] == "missing_requirement"
    assert res["required"] == "green_flare"
    assert contractor.is_extracted is False

    # Add green flare and retry
    contractor.inventory.append(LootItem(id="green_flare", name="Signal Flare", value_credits=100, weight_kg=0.2))
    res_with_flare = raid.process_extraction(contractor.id, dt=1.0)
    assert res_with_flare["status"] == "extracting"


def test_raid_clock_expiry_and_mia_status(fresh_raid):
    """Verifies that when raid time expires, non-extracted operators become MIA."""
    raid, contractor = fresh_raid
    # Move contractor outside exfils
    contractor.x = 50
    contractor.y = 50

    # Advance clock to near end -> urgent soundtrack triggers
    raid.update_raid_clock(250.0)
    assert raid.state == RaidState.EXTRACTION_WINDOW_CLOSING
    assert "raid_urgency.ogg" in raid.current_soundtrack

    # Advance clock past total duration (300s)
    raid.update_raid_clock(60.0)
    assert raid.state == RaidState.RAID_ENDED
    assert contractor.is_mia is True


def test_godot_byond_bridge_transform_encoding():
    """Verifies JSON-RPC transform serialization between Godot 4 and BYOND."""
    bridge = GodotByondBridge()
    json_packet = bridge.encode_entity_transform(
        entity_id="mob_vance",
        x=95.421,
        y=95.889,
        rotation_rad=1.5708,
        velocity=(2.5, 0.0),
    )

    data = json.loads(json_packet)
    assert data["jsonrpc"] == "2.0"
    assert data["method"] == "sync_transform"
    assert data["params"]["id"] == "mob_vance"
    assert data["params"]["x"] == 95.421
    assert data["params"]["y"] == 95.889
    assert data["params"]["rot"] == 1.5708
    assert data["params"]["vx"] == 2.5


def test_dm_specification_export():
    """Verifies that BYOND / DM source specification includes gamemode and beacon machinery."""
    assert "/datum/game_mode/extraction_shooter" in DM_EXTRACTION_SHOOTER_SPEC
    assert "/obj/machinery/exfil_beacon" in DM_EXTRACTION_SHOOTER_SPEC
    assert "exfil_countdown.ogg" in DM_EXTRACTION_SHOOTER_SPEC
    assert "exfil_success.ogg" in DM_EXTRACTION_SHOOTER_SPEC
