"""Unit tests for Simplified Chinese (ZH-CN) Localization & Codebase Translation Engine.
Resolves Issue #659: [BOUNTY] [$1500] Translate the game to simplified Chinese.
"""

import pytest
from scripts.simplified_chinese_localization_engine import (
    SimplifiedChineseLocalizationEngine,
    ZH_ROLE_MAP,
    ZH_ITEM_MAP,
    ZH_EXAMINE_MAP,
    ZH_IDENTIFIER_MAP,
)


@pytest.fixture
def engine():
    return SimplifiedChineseLocalizationEngine()


def test_role_translations(engine):
    """Verifies station job and role translations with bilingual comments."""
    res_capt = engine.translate_role("Captain")
    assert res_capt.translated_text == "舰长"
    assert res_capt.comment_tag == "/* [EN: Captain] */"

    res_clown = engine.translate_role("Clown")
    assert res_clown.translated_text == "小丑"
    assert res_clown.comment_tag == "/* [EN: Clown] */"


def test_item_name_translations(engine):
    """Verifies standard item and equipment name localization."""
    res_crowbar = engine.translate_item_name("crowbar")
    assert res_crowbar.translated_text == "撬棍"
    assert res_crowbar.comment_tag == "/* [EN: crowbar] */"

    res_medkit = engine.translate_item_name("medkit")
    assert res_medkit.translated_text == "急救包"
    assert res_medkit.comment_tag == "/* [EN: medkit] */"


def test_examine_text_localization(engine):
    """Verifies examine description translation preserving original intent."""
    sample_examine = "A heavy steel crowbar used for prying open doors."
    res = engine.translate_examine_text(sample_examine)
    assert res.translated_text == "用于撬开舱门的重型钢制撬棍。"
    assert res.comment_tag == f"/* [EN: {sample_examine}] */"


def test_identifier_translation(engine):
    """Verifies translation of function and variable identifiers."""
    res_setup = engine.translate_identifier("setup")
    assert res_setup.translated_text == "chushihua"
    assert res_setup.comment_tag == "/* [EN: setup] */"

    res_health = engine.translate_identifier("health")
    assert res_health.translated_text == "shengmingzhi"
    assert res_health.comment_tag == "/* [EN: health] */"


def test_process_dm_datum_definition_generation(engine):
    """Verifies generation of fully localized DreamMaker datum with bilingual comments."""
    dm_output = engine.process_dm_datum_definition(
        typepath="/obj/item/crowbar",
        name="crowbar",
        desc="A heavy steel crowbar used for prying open doors.",
        procs=["initialize", "examine"]
    )

    assert "/obj/item/crowbar" in dm_output
    assert "name = \"撬棍\"" in dm_output
    assert "desc = \"用于撬开舱门的重型钢制撬棍。\"" in dm_output
    assert "/* [EN: crowbar] */" in dm_output
    assert "/* [EN: initialize] */" in dm_output
    assert "proc/chushihua()" in dm_output
    assert "proc/chakan()" in dm_output
