"""Tests for Thursday's Boots.

Covers the acceptance criteria for bounty #745:

1. Thursday's Boots item exists with proper name/desc, slot, armor, slowdown,
   and day-of-week transmutation joke.
2. On Thursday the boots become "Friday's Boots"; on Friday they become the
   TGIF edition with extra speed.
3. Crafting recipe, maintenance loot table, branding references, and
   day-dependent examine text are present.
"""

from __future__ import annotations

import json
from pathlib import Path

from thursdays_boots import (
    Armor,
    BootCatalog,
    CraftingRecipe,
    ThursdaysBoots,
    build_boots_from_fixture,
    load_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "thursdays-boots-fixture.json"
).resolve()


def test_boots_have_name() -> None:
    """The boots are named Thursday's Boots on a normal day."""
    boot = ThursdaysBoots("Wed")
    assert boot.name == "Thursday's Boots"


def test_boots_have_desc() -> None:
    """The boots carry the well-worn leather description."""
    boot = ThursdaysBoots("Mon")
    assert "well-worn leather boots" in boot.desc
    assert "Thursday" in boot.desc


def test_boots_refuse_to_be_worn_on_thursday() -> None:
    """On Thursday the boots transmute into Friday's Boots."""
    boot = ThursdaysBoots("Thu")
    assert boot.name == "Friday's Boots"
    assert boot.is_thursday() is True
    assert "Thursday" in boot.desc


def test_friday_gets_tgif_edition() -> None:
    """On Friday the boots become the TGIF edition with extra speed."""
    boot = ThursdaysBoots("Fri")
    assert boot.name == "Thursday's Boots (TGIF Edition)"
    assert boot.slowdown == -1.0


def test_normal_day_speed() -> None:
    """On a normal day the boots have the comfortable slowdown."""
    boot = ThursdaysBoots("Mon")
    assert boot.slowdown == -0.5


def test_slot_is_feet() -> None:
    """The boots equip in the feet slot and cannot be tied."""
    boot = ThursdaysBoots("Wed")
    payload = boot.to_json()
    assert payload["slot"] == "feet"
    assert payload["can_be_tied"] is False


def test_armor_profile() -> None:
    """The boots carry a balanced armor profile."""
    armor = Armor()
    assert armor.melee == 10
    assert armor.acid == 50
    assert armor.fire == 30
    assert armor.bullet == 0


def test_examine_normal_day() -> None:
    """On a normal day the examine text mentions the sole embossment."""
    boot = ThursdaysBoots("Mon")
    lines = boot.examine_text()
    assert any("Not to be worn on THURSDAYS" in line for line in lines)


def test_examine_thursday_marker() -> None:
    """On Thursday the examine text shows the FRIDAY crossing-out."""
    boot = ThursdaysBoots("Thu")
    lines = boot.examine_text()
    assert any("FRIDAY" in line for line in lines)


def test_examine_friday_tgif() -> None:
    """On Friday the examine text shows the tiny TGIF engraving."""
    boot = ThursdaysBoots("Fri")
    lines = boot.examine_text()
    assert any("TGIF" in line for line in lines)


def test_examine_reports_blood() -> None:
    """Bloodied boots report absorbed blood in their examine text."""
    boot = ThursdaysBoots("Tue")
    lines = boot.examine_text(blood_level=7)
    assert any("7 units of blood" in line for line in lines)


def test_on_new_day_updates_identity() -> None:
    """Changing the in-game day refreshes the boot identity."""
    boot = ThursdaysBoots("Wed")
    boot.on_new_day("Thu")
    assert boot.name == "Friday's Boots"
    boot.on_new_day("Mon")
    assert boot.name == "Thursday's Boots"
    assert boot.slowdown == -0.5


def test_crafting_recipe() -> None:
    """The crafting recipe needs leather, sneakers, and cloth."""
    recipe: CraftingRecipe = BootCatalog().recipe
    assert recipe.leather_sheets == 4
    assert recipe.black_sneakers == 1
    assert recipe.cloth_sheets == 1
    assert recipe.time_seconds == 60


def test_loot_table() -> None:
    """The maintenance loot table includes the boots with a weight."""
    loot = BootCatalog().loot_table()
    assert loot["thursdays_boots"] == 10
    assert loot["sneakers_black"] == 40
    assert loot["workboots"] == 60


def test_brand_references() -> None:
    """The module carries the required Thursday's Boots branding."""
    references = BootCatalog().brand_references()
    assert any("sponsored by Thursday's Boots" in r for r in references)
    assert any("w-_Q3LFfeb4" in r for r in references)


def test_unknown_day_raises() -> None:
    """An unknown day-of-week is rejected."""
    try:
        ThursdaysBoots("Funday")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown day")


def test_fixture_builds_boots() -> None:
    """The canonical fixture builds a Thursday's Boots item."""
    fixture = load_fixture(FIXTURE)
    boot = build_boots_from_fixture(fixture)
    assert boot.name == "Thursday's Boots"
    assert boot.blood_level == 3


def test_json_shape() -> None:
    """The boot serializes to the canonical JSON shape."""
    boot = ThursdaysBoots("Wed")
    payload = boot.to_json()
    for field in ("name", "desc", "icon_state", "slowdown", "day", "armor", "slot"):
        assert field in payload
    assert payload["day"] == "Wed"
    assert "melee" in payload["armor"]


def test_catalog_json_shape() -> None:
    """The catalog serializes to the canonical JSON shape."""
    catalog = BootCatalog()
    payload = catalog.to_json()
    assert payload["brand"] == "Thursday's Boots"
    assert "recipe" in payload and "requirements" in payload["recipe"]
    assert "loot_maintenance" in payload
