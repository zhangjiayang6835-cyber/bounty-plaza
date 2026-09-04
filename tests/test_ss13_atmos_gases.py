"""Unit tests for SS13 Atmos Gases: Shitium, Kurchatov-Quantium, and Adskiderium (Issue #610)."""

import pytest
from scripts.ss13_atmos_gases import (
    AtmosExoticGasSubsystem,
    ExposedItem,
    ExposedMob,
    ExposedTile,
    GasType,
    SpeciesType,
)


def test_shitium_synthesis_and_biological_transformation():
    atmos = AtmosExoticGasSubsystem()

    # Fail conditions
    fail_yield, msg = atmos.synthesize_shitium(miasma_moles=2.0, temp_k=300.0)
    assert fail_yield == 0.0
    assert msg == "REACTION_CONDITIONS_NOT_MET"

    # Successful synthesis
    shitium_yield, msg = atmos.synthesize_shitium(miasma_moles=10.0, temp_k=380.0)
    assert shitium_yield == 8.5
    assert msg == "SHITIUM_SYNTHESIS_SUCCESS"

    # Exposure: Mob, Tile, Item
    mob = ExposedMob(ckey="ckey_clown", name="Honk McHonkerson")
    tile = ExposedTile(coord=(100, 100, 1))
    item = ExposedItem(item_id="item_pen", name="ballpoint pen")

    exposure_res = atmos.apply_shitium_exposure(mob, tile, item)
    assert exposure_res["status"] == "SHITIUM_TRANSFORMATION_COMPLETE"
    assert mob.species == SpeciesType.SHITMAN
    assert "You're now a shitmen!" in mob.chat_messages_received
    assert tile.is_brown_sludge is True
    assert item.is_fecal_sludge is True
    assert "soiled ballpoint pen" in item.name


def test_kurchatov_quantium_synthesis_and_quantum_mutations():
    atmos = AtmosExoticGasSubsystem()

    # Fails if quantum emitter is offline
    fail_yield, msg = atmos.synthesize_kurchatov_quantium(
        anti_noblium_moles=5.0,
        hyper_noblium_moles=5.0,
        emitter_active=False
    )
    assert fail_yield == 0.0
    assert msg == "QUANTUM_EMITTER_OFFLINE"

    # Successful synthesis with active emitter
    quantium_yield, msg = atmos.synthesize_kurchatov_quantium(
        anti_noblium_moles=10.0,
        hyper_noblium_moles=12.0,
        emitter_active=True
    )
    assert quantium_yield == 14.5
    assert msg == "KURCHATOV_QUANTIUM_SYNTHESIS_SUCCESS"

    # Apply quantum mutation
    mob = ExposedMob(ckey="ckey_engineer", name="Chief Engineer")
    tile = ExposedTile(coord=(105, 95, 1))
    item = ExposedItem(item_id="item_pen", name="ballpoint pen")

    mutation_res = atmos.apply_kurchatov_quantium_mutation(mob, tile, item, mutation_seed=123)
    assert mutation_res["status"] == "QUANTUM_MUTATION_APPLIED"
    # Item acquires bizarre property (edible, explosive, or radioactive)
    assert item.is_edible or item.is_explosive_on_touch or item.is_radioactive
    # Tile acquires Goliath tentacles pulling actors
    assert tile.has_goliath_tentacles is True
    # Human organ mutation: lungs lose respiratory function and generate cobblestones
    lungs = mob.organs["lungs"]
    assert lungs.is_functional is False
    assert lungs.generated_debris == "cobblestones"


def test_adskiderium_classified_event_and_eldritch_corruption():
    atmos = AtmosExoticGasSubsystem()

    # Canister sealed
    sealed_yield, msg = atmos.release_adskiderium_classified_event(canister_seal_broken=False)
    assert sealed_yield == 0.0
    assert msg == "CENTCOM_CLASSIFIED_CANISTER_SEALED"

    # Canister seal breached
    outbreak_yield, msg = atmos.release_adskiderium_classified_event(canister_seal_broken=True)
    assert outbreak_yield == 50.0
    assert msg == "ADSKIDERIUM_CENTCOM_OUTBREAK"

    # Eldritch corruption exposure
    mob = ExposedMob(ckey="ckey_officer", name="Security Officer")
    tile = ExposedTile(coord=(110, 110, 1))

    corruption_res = atmos.apply_adskiderium_eldritch_corruption(mob, tile)
    assert corruption_res["status"] == "ELDRITCH_CORRUPTION_APPLIED"
    assert mob.sanity_level < 50.0
    assert mob.eldritch_corruption_pct >= 75.0
    assert tile.void_crack_open is True
    assert any("consume your name" in msg for msg in mob.chat_messages_received)


def test_map_and_dreammaker_exports():
    atmos = AtmosExoticGasSubsystem()
    maps = atmos.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in maps
    assert "runtimestation.dmm" in maps
    assert "/obj/machinery/atmospherics/components/binary/quantum_emitter" in maps["IceBoxStation.dmm"]
    assert "/obj/structure/canister/classified/adskiderium" in maps["IceBoxStation.dmm"]

    dm = atmos.export_dreammaker_code()
    assert "/datum/gas/shitium" in dm
    assert "/datum/gas/kurchatov_quantium" in dm
    assert "/datum/gas/adskiderium" in dm
    assert "/obj/machinery/atmospherics/components/binary/quantum_emitter" in dm
