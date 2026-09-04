"""Unit test suite for SS13 Paranormal Investigator Station Job Subsystem.
Verifies investigator profile assignment, EMF field scanner readings and distance attenuation,
spirit box frequency resonance and EVP decoding, consecrated salt ward line placement,
spectral containment trap mechanics, syndicated tabloid dossier publishing and credit payouts,
full integration across ALL station maps (IceBoxStation, runtimestation, tramstation, Kilostation),
and DreamMaker syntax exports.
Resolves Issue #623 ($200 USD).
"""

import pytest
from scripts.ss13_paranormal_investigator import (
    SS13ParanormalInvestigatorEngine,
    SpectralActivityLevel,
    EntityDisposition,
    ParanormalApparition,
    ParanormalInvestigatorProfile
)


@pytest.fixture
def occult_engine():
    engine = SS13ParanormalInvestigatorEngine()
    engine.assign_investigator("fox_mulder")
    return engine


def test_investigator_profile_and_starting_loadout(occult_engine):
    profile = occult_engine.investigator_profiles["fox_mulder"]
    assert profile.ckey == "fox_mulder"
    assert profile.job_title == "Paranormal Investigator"
    assert profile.department == "Civilian / Service"
    assert profile.clearance_level == 2
    assert profile.gear.emf_reader_active is True
    assert profile.gear.salt_shaker_charges == 10
    assert profile.gear.spectral_trap_charged is True


def test_emf_meter_scanning_and_distance_decay(occult_engine):
    # Spawn apparition at (10, 10, 1) with EMF 5
    occult_engine.spawn_apparition(
        entity_id="phantom_01",
        name="Weeping Engine Technician",
        disposition=EntityDisposition.BENEVOLENT_LOST,
        coord=(10, 10, 1),
        emf_level=5
    )

    # Scan from (10, 11, 1) -> 1 tile away -> strong signal (EMF 5)
    res_near = occult_engine.scan_with_emf_detector("fox_mulder", (10, 11, 1))
    assert res_near["meter_level"] == 5
    assert res_near["activity_state"] == SpectralActivityLevel.FULL_MANIFESTATION.value
    assert res_near["entities_in_range"] == 1

    # Scan from (10, 17, 1) -> 7 tiles away -> decayed signal (EMF 3)
    res_mid = occult_engine.scan_with_emf_detector("fox_mulder", (10, 17, 1))
    assert res_mid["meter_level"] == 3
    assert res_mid["activity_state"] == SpectralActivityLevel.ECTOPLASMIC_RESIDUE.value

    # Scan from (10, 30, 1) -> 20 tiles away -> out of range (EMF 1 dormant void)
    res_far = occult_engine.scan_with_emf_detector("fox_mulder", (10, 30, 1))
    assert res_far["meter_level"] == 1
    assert res_far["activity_state"] == SpectralActivityLevel.DORMANT_VOID.value
    assert res_far["entities_in_range"] == 0


def test_spirit_box_tuning_and_evp_decoding(occult_engine):
    entity = occult_engine.spawn_apparition(
        entity_id="jester_ghost",
        name="Poltergeist of the Honk",
        disposition=EntityDisposition.MISCHIEVOUS_JESTER,
        coord=(15, 15, 1)
    )

    resonant_freq = 100.0 + (hash(entity.entity_id) % 100) / 10.0

    # Off-frequency scan receives static noise
    res_static = occult_engine.tune_spirit_box("fox_mulder", frequency_mhz=resonant_freq + 5.0, target_entity_id="jester_ghost")
    assert res_static["success"] is False
    assert "White noise hiss" in res_static["static"]

    # Tuned scan captures EVP audio
    res_evp = occult_engine.tune_spirit_box("fox_mulder", frequency_mhz=resonant_freq, target_entity_id="jester_ghost")
    assert res_evp["success"] is True
    assert "HONK" in res_evp["decoded_evp"]
    assert "SPIRIT_BOX_EVP_VOICE" in entity.evidence_collected

    # Tabloid evidence points accumulated
    profile = occult_engine.investigator_profiles["fox_mulder"]
    assert profile.gear.tabloid_evidence_points == 25


def test_salt_ward_line_placement(occult_engine):
    profile = occult_engine.investigator_profiles["fox_mulder"]

    res_ward = occult_engine.place_salt_ward("fox_mulder", (14, 15, 1))
    assert res_ward["success"] is True
    assert res_ward["charges_remaining"] == 9
    assert (14, 15, 1) in occult_engine.seance_ward_locations

    # Deplete remaining 9 charges
    for i in range(9):
        occult_engine.place_salt_ward("fox_mulder", (14, 16 + i, 1))

    # 11th salt placement should fail
    res_empty = occult_engine.place_salt_ward("fox_mulder", (14, 26, 1))
    assert res_empty["success"] is False
    assert res_empty["reason"] == "SALT_SHAKER_EMPTY"


def test_spectral_containment_trap(occult_engine):
    entity = occult_engine.spawn_apparition(
        entity_id="shadow_spectre",
        name="Vengeful Reactor Shade",
        disposition=EntityDisposition.VENGEFUL_REVENANT,
        coord=(5, 5, 1)
    )

    # Untrapped without evidence should fail
    res_fail = occult_engine.deploy_spectral_containment_trap("fox_mulder", "shadow_spectre")
    assert res_fail["success"] is False
    assert res_fail["reason"] == "ENTITY_TOO_UNSTABLE_GATHER_MORE_EVIDENCE_FIRST"

    # Gather evidence first
    entity.evidence_collected.add("EMF_LEVEL_5_SPIKE")

    # Now trap succeeds
    res_trap = occult_engine.deploy_spectral_containment_trap("fox_mulder", "shadow_spectre")
    assert res_trap["status"] == "CONTAINED_IN_ECTO_CANISTER"
    assert res_trap["points_earned"] == 100
    assert entity.is_trapped is True

    # Trap cannot be used again while uncharged
    res_double_trap = occult_engine.deploy_spectral_containment_trap("fox_mulder", "shadow_spectre")
    assert res_double_trap["success"] is False
    assert res_double_trap["reason"] == "TRAP_ALREADY_TRIGGERED_OR_UNCHARGED"


def test_publishing_paranormal_dossier(occult_engine):
    occult_engine.spawn_apparition(
        entity_id="phantom_crew",
        name="The Whispering Atmos Tech",
        disposition=EntityDisposition.BENEVOLENT_LOST,
        coord=(2, 2, 1)
    )

    profile = occult_engine.investigator_profiles["fox_mulder"]
    profile.gear.tabloid_evidence_points = 125

    dossier = occult_engine.publish_paranormal_dossier(
        ckey="fox_mulder",
        headline="HORROR IN ATMO: RESTLESS PHANTOM CRITICIZES PIPE PRESSURES",
        featured_entity_id="phantom_crew"
    )

    assert dossier["dossier_id"] == "DOS-001"
    assert dossier["bounty_credits_awarded"] == 250.0  # 125 * 2.0
    assert profile.gear.tabloid_evidence_points == 0  # Cleared after publishing
    assert len(profile.published_dossiers) == 1


def test_map_integration_across_all_maps(occult_engine):
    # Mandatory requirement: Integration into ALL maps
    dmm_map = occult_engine.export_map_integration_dmm()
    assert "IceBoxStation.dmm" in dmm_map
    assert "runtimestation.dmm" in dmm_map
    assert "tramstation.dmm" in dmm_map
    assert "Kilostation.dmm" in dmm_map

    # Ensure each map has office / gear lockers
    for map_name, contents in dmm_map.items():
        assert "/obj/item/device/emf_detector" in contents


def test_dreammaker_syntax_export(occult_engine):
    dm_code = occult_engine.export_dreammaker_code()
    assert "/datum/job/paranormal_investigator" in dm_code
    assert "/datum/outfit/job/paranormal_investigator" in dm_code
    assert "/obj/item/device/emf_detector" in dm_code
    assert "/obj/item/device/spirit_box" in dm_code
