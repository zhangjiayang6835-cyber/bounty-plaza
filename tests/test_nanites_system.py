"""Unit and integration test suite for re-added Nanites subsystem.
Resolves Issue #729: [BOUNTY] [$300] re-add nanites (reverting PR #60473).
"""

import pytest
from scripts.nanites_system import (
    NaniteHost,
    CellularRepairProgram,
    DermalHardeningProgram,
    NaniteChamber,
    NaniteProgramCategory,
    BYOND_NANITES_DM_SOURCE,
)


@pytest.fixture
def host():
    h = NaniteHost(
        mob_id="mob_human_nanite_01",
        name="Engineer Davis",
        max_volume=500.0,
        nanite_volume=100.0,
        replication_rate=2.0,
        safety_threshold=30.0,
    )
    return h


def test_nanite_replication_and_passive_consumption(host):
    """Verifies cellular population growth up to max volume and upkeep deduction."""
    prog = CellularRepairProgram()
    host.install_program(prog)

    # Initial volume 100.0 -> +2.0 replication -> -0.5 passive = 101.5 (no damage to repair)
    tick_result = host.process_tick()

    assert tick_result["status"] == "ok"
    assert host.nanite_volume == 101.5


def test_cellular_repair_program_execution(host):
    """Verifies that nanites actively heal brute and burn damage when above safety threshold."""
    repair_prog = CellularRepairProgram(heal_rate=10.0)
    host.install_program(repair_prog)
    host.brute_loss = 25.0
    host.burn_loss = 15.0

    # Tick with damage: volume 100 + 2 - 0.5 - 5.0 (activation) = 96.5
    tick_res = host.process_tick()

    assert tick_res["program_executions"]["med_cellular_repair"]["executed"] is True
    assert host.brute_loss == 15.0  # 25 - 10
    assert host.burn_loss == 5.0    # 15 - 10
    assert host.nanite_volume == 96.5


def test_safety_threshold_prevents_drain(host):
    """Verifies that nanite programs stop executing when volume falls below safety threshold."""
    repair_prog = CellularRepairProgram(heal_rate=10.0)
    host.install_program(repair_prog)
    host.nanite_volume = 25.0  # Below safety threshold of 30.0
    host.brute_loss = 20.0

    tick_res = host.process_tick()

    assert tick_res["program_executions"]["med_cellular_repair"]["executed"] is False
    assert tick_res["program_executions"]["med_cellular_repair"]["status"] == "safety_threshold_lock"
    assert host.brute_loss == 20.0


def test_dermal_hardening_mitigation():
    """Verifies armor mitigation ratio calculation."""
    armor_prog = DermalHardeningProgram(armor_bonus=25.0)
    raw_damage = 40.0
    mitigated = armor_prog.calculate_mitigation(raw_damage)

    assert mitigated == 30.0  # 40 * (1 - 0.25)


def test_nanite_chamber_cloud_synchronization(host):
    """Verifies chamber occupancy and automated cloud program installation."""
    chamber = NaniteChamber()

    assert chamber.enter_chamber(host) is True
    # Cannot enter already occupied chamber
    other_host = NaniteHost(mob_id="mob_02", name="Assistant John")
    assert chamber.enter_chamber(other_host) is False

    # Sync cloud programs
    sync_res = chamber.sync_cloud_programs()
    assert sync_res["status"] == "success"
    assert sync_res["synced_programs"] == 2
    assert "med_cellular_repair" in host.programs
    assert "def_dermal_hardening" in host.programs

    # Exit chamber
    exited = chamber.exit_chamber()
    assert exited.mob_id == host.mob_id
    assert chamber.occupant is None


def test_byond_dm_nanites_syntax():
    """Ensures BYOND DM restoration file contains core datums and procs."""
    assert "/datum/nanites" in BYOND_NANITES_DM_SOURCE
    assert "/datum/nanite_program" in BYOND_NANITES_DM_SOURCE
    assert "/obj/machinery/nanite_chamber" in BYOND_NANITES_DM_SOURCE
    assert "replication_rate" in BYOND_NANITES_DM_SOURCE
