"""Unit tests for Albuquerque/Turkey Refactor Engine.
Resolves Issue #658: [BOUNTY] [$250] [EASY] [AGENTIC AI] Albuquerque/Turkey Refactor.
Upstream Reference: Iamgoofball/-tg-station#202.
"""

import pytest
from scripts.albuquerque_turkey_refactor import (
    AlbuquerqueTurkeyRefactorer,
    ALBUQUERQUE_TURKEY_FLAG_ASCII,
)


@pytest.fixture
def refactorer():
    return AlbuquerqueTurkeyRefactorer()


def test_lexical_transformation_space_and_station(refactorer):
    raw_text = "Welcome to space station 13. The deep space is dangerous near the station."
    transformed, changes = refactorer.refactor_text(raw_text)

    assert changes == 4
    assert "Albuquerque_Turkey" in transformed or "albuquerque_turkey" in transformed
    assert "Jerky" in transformed or "jerky" in transformed
    assert "space" not in transformed.lower()
    assert "station" not in transformed.lower()


def test_lexical_case_preservation(refactorer):
    raw_text = "SPACE STATION space station Space Station"
    transformed, changes = refactorer.refactor_text(raw_text)

    assert changes == 6
    assert "ALBUQUERQUE_TURKEY JERKY" in transformed
    assert "albuquerque_turkey jerky" in transformed
    assert "Albuquerque_Turkey Jerky" in transformed


def test_empire_flag_structure(refactorer):
    flag = refactorer.get_empire_flag()
    assert refactorer.verify_flag_structure(flag) is True

    # 13 stripes
    for i in range(1, 14):
        assert f"[STRIPE {i:02d}]" in flag

    # KFC bucket and space station 13
    assert "KFC_CHICKEN_BUCKET" in flag or "K F C" in flag
    assert "Space Station 13" in flag

    # 50 stars
    assert flag.count("*") >= 50


def test_drink_verification_can_protocol(refactorer):
    result = refactorer.drink_verification_can(volume_ml=500)
    assert result["status"] == "VERIFIED_COMPLIANT"
    assert result["peace_treaty_active"] is True
    assert result["volume_consumed_ml"] == 500
    assert "Verification Can" in result["item_consumed"]


def test_flag_injection_into_codebase(refactorer):
    sample_dm_code = (
        "/obj/machinery/door/airlock/glass\n"
        "\tname = \"glass airlock\"\n"
        "\ticon = 'icons/obj/doors/airlocks/station/airlocks.dmi'\n"
    )

    injected = refactorer.inject_empire_flag(sample_dm_code)
    assert "ALBUQUERQUE TURKEY UNITED SPACE EMPIRE" in injected
    assert "/obj/machinery/door/airlock/glass" in injected

    # Calling inject again does not duplicate
    double_injected = refactorer.inject_empire_flag(injected)
    assert double_injected.count("ALBUQUERQUE TURKEY UNITED SPACE EMPIRE") == 1
