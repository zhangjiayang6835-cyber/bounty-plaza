"""Unit tests for SS13 Uzbek Localization Engine subsystem.
Resolves Issue #584: [READY FOR AGENT] [$250 USD Opire Bounty] translate all user-facing text.
"""

import pytest
from scripts.ss13_uzbek_localization import (
    UZBEK_LOCALIZATION_DATA,
    UzbekGrammarHelper,
    UzbekLocalizationEngine,
)


def test_localization_breadth_and_coverage():
    # Verify coverage across jobs, HUD, chat, alerts, and cultural puns
    assert len(UZBEK_LOCALIZATION_DATA) >= 60

    engine = UzbekLocalizationEngine()
    # Check core job roles
    assert engine.translate("role.captain") == "Kapitan (Stansiya Rahbari)"
    assert engine.translate("role.clown") == "Qiziqchi Kloun (Kulgi Ustasi)"
    assert engine.translate("role.janitor") == "Farrosh / Tozalik Posboni"

    # Check HUD elements
    assert engine.translate("hud.health") == "Salomatlik Holati"
    assert engine.translate("hud.oxygen") == "Kislorod Darajasi"


def test_parameter_interpolation():
    engine = UzbekLocalizationEngine()
    # Test shuttle alert interpolation
    res_shuttle = engine.translate("alert.shuttle_called", minutes=5)
    assert "Yetib kelish vaqti: 5 daqiqa" in res_shuttle

    res_dock = engine.translate("alert.shuttle_docked", seconds=45)
    assert "jo'nashga 45 soniya qoldi!" in res_dock


def test_culturally_adapted_puns():
    engine = UzbekLocalizationEngine()
    # Banana slip with regional bazaar pun
    res_slip = engine.translate("pun.banana_slip", victim="Janitor Bob")
    assert "Janitor Bob" in res_slip
    assert "Samarqand bozoridagi qovun ustida yiqilgandek" in res_slip

    # Chef mystery meat pun
    res_chef = engine.translate("pun.chef_mystery_burger")
    assert "Oshpazning sirli somsasidan" in res_chef

    # Clown signature pun
    res_honk = engine.translate("pun.clown_honk")
    assert "Xonq-xonq!" in res_honk


def test_uzbek_grammar_helper_suffixes():
    # Locative (-da)
    assert UzbekGrammarHelper.get_locative_suffix("stansiya") == "stansiyada"
    assert UzbekGrammarHelper.get_locative_suffix("brig") == "brigda"

    # Accusative (-ni)
    assert UzbekGrammarHelper.get_accusative_suffix("kloun") == "klounni"

    # Genitive (-ning)
    assert UzbekGrammarHelper.get_genitive_suffix("kapitan") == "kapitanning"

    # Plural (-lar)
    assert UzbekGrammarHelper.get_plural_suffix("xodim") == "xodimlar"


def test_runtime_override_and_fallback():
    engine = UzbekLocalizationEngine()
    # Fallback representation for missing key
    assert engine.translate("nonexistent.station.key") == "[nonexistent.station.key]"

    # Runtime override
    engine.register_override("role.captain", "Buyuk Kosmik Kapitan")
    assert engine.translate("role.captain") == "Buyuk Kosmik Kapitan"


def test_dreammaker_export():
    engine = UzbekLocalizationEngine()
    dm = engine.export_dreammaker_definitions()
    assert "/datum/localization/uzbek" in dm
    assert 'language_code = "uz_UZ"' in dm
    assert "GLOB.uzbek_translations" in dm
