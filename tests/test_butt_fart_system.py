"""Unit and integration tests for Butt Organ, Flatulence Engine, and Super Fart Subsystem.
Resolves Issue #670: [BOUNTY] 500 USD Add farts and super farts.
"""

import pytest
from scripts.butt_fart_system import (
    ButtOrgan,
    FlatulenceActor,
    FartType,
    DM_BUTT_FART_SYSTEM_SPEC,
)


@pytest.fixture
def crewmember():
    return FlatulenceActor(name="Engineer", health=100.0)


def test_standard_fart_with_intact_butt(crewmember):
    """Verifies that an actor with an intact butt organ can fart normally."""
    assert crewmember.has_functional_butt is True
    res = crewmember.fart()

    assert res["success"] is True
    assert res["fart_type"] == FartType.STANDARD
    assert res["sound"] == "sound/misc/fart.ogg"
    assert "toot" in res["message"]
    assert res["methane_moles"] > 0.0


def test_super_fart_explosion_and_butt_blowout(crewmember):
    """Verifies that a super fart detonates an explosion and blows the butt organ away."""
    assert crewmember.has_functional_butt is True

    res = crewmember.super_fart()

    assert res["success"] is True
    assert res["fart_type"] == FartType.SUPER
    assert res["explosion"] is not None
    assert res["explosion"]["concussive_force"] == 80.0
    assert res["explosion"]["sound"] == "sound/effects/superfart_blast.ogg"
    assert crewmember.health < 100.0  # Recoil damage
    assert crewmember.is_stunned is True

    # Butt organ must now be completely gone
    assert crewmember.butt is None
    assert crewmember.has_functional_butt is False


def test_cannot_fart_without_butt(crewmember):
    """Verifies that with no butt organ, neither standard nor super farts are possible."""
    # Remove butt
    crewmember.butt = None
    assert crewmember.has_functional_butt is False

    # Standard fart fails
    res_std = crewmember.fart()
    assert res_std["success"] is False
    assert res_std["error"] == "no_butt"
    assert "physically impossible" in res_std["message"]

    # Super fart fails
    res_super = crewmember.super_fart()
    assert res_super["success"] is False
    assert res_super["error"] == "no_butt"
    assert res_super["explosion"] is None


def test_surgical_transplant_restores_flatulence(crewmember):
    """Verifies that surgical transplantation of a new butt organ restores fart capability."""
    # Blow out original butt
    crewmember.super_fart()
    assert crewmember.has_functional_butt is False

    # Transplant donor butt organ
    new_donor_butt = ButtOrgan(name="cybernetic butt", durability=80.0)
    success = crewmember.surgical_transplant_butt(new_donor_butt)

    assert success is True
    assert crewmember.has_functional_butt is True
    assert crewmember.butt.name == "cybernetic butt"

    # Can fart again
    res = crewmember.fart()
    assert res["success"] is True
    assert res["fart_type"] == FartType.STANDARD


def test_egyptian_papyrus_documentation_and_dm_export():
    """Verifies Egyptian hieroglyphic documentation and BYOND / DM source definitions."""
    butt = ButtOrgan()
    assert "𓂋 𓈖 𓎛 𓊪 𓅱 𓏏" in butt.papyrus_inscription
    assert "Ebers Papyrus" in butt.papyrus_inscription

    assert "/obj/item/organ/internal/butt" in DM_BUTT_FART_SYSTEM_SPEC
    assert "/mob/living/carbon/human/verb/fart()" in DM_BUTT_FART_SYSTEM_SPEC
    assert "/mob/living/carbon/human/verb/super_fart()" in DM_BUTT_FART_SYSTEM_SPEC
    assert "explosion(" in DM_BUTT_FART_SYSTEM_SPEC
    assert "on_super_fart_blowout()" in DM_BUTT_FART_SYSTEM_SPEC
