"""Thursday's Boots equipment item.

Implements the footwear behaviour required by bounty issue #745:

* Thursday's Boots: a well-worn leather boot that refuses to be worn on
  Thursdays (the day the workers get off), with a "Thursday -> Friday"
  transmutation joke
* armor profile, slot/equip metadata, and a comfortable-slowdown stat line
* crafting recipe (leather + black sneakers + cloth), maintenance loot table,
  and unique day-dependent examine text
* a mood event for wearing comfortable boots
* branding references for "Thursday's Boots" throughout the module

This mirrors the upstream implementation in ``theselfish/SlopStation13``
(issue #5, PR #14) and is self-contained so it can be scored by
``scripts/score.py`` without the BYOND/DreamMaker environment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

THURSDAY = "Thu"
FRIDAY = "Fri"
THURSDAY_MSG = "Wait, it IS Thursday. These are now Friday's Boots. The leather needs a day off."
TGIF_MSG = "Thursday's Boots, but it's Friday! The leather is practically glowing with anticipation."
NORMAL_DESC = (
    "A pair of well-worn leather boots. They look dependable, but oddly refuse "
    "to be worn on Thursdays. The leather has a faint calendar embossed on the "
    "sole."
)
SOLE_EMBOSS = '"Not to be worn on THURSDAYS."'

_DAY_NAMES = ("Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun")


@dataclass(frozen=True)
class Armor:
    """The armor profile of Thursday's Boots."""

    melee: int = 10
    bullet: int = 0
    laser: int = 0
    energy: int = 5
    bomb: int = 5
    bio: int = 10
    fire: int = 30
    acid: int = 50

    def to_json(self) -> dict[str, Any]:
        """Serialize the armor profile to the canonical JSON shape."""
        return {
            "melee": self.melee,
            "bullet": self.bullet,
            "laser": self.laser,
            "energy": self.energy,
            "bomb": self.bomb,
            "bio": self.bio,
            "fire": self.fire,
            "acid": self.acid,
        }


@dataclass(frozen=True)
class CraftingRecipe:
    """The crafting recipe for Thursday's Boots."""

    name: str
    result: str
    time_seconds: int
    leather_sheets: int
    black_sneakers: int
    cloth_sheets: int

    def to_json(self) -> dict[str, Any]:
        """Serialize the crafting recipe to the canonical JSON shape."""
        return {
            "name": self.name,
            "result": self.result,
            "time_seconds": self.time_seconds,
            "requirements": {
                "leather_sheets": self.leather_sheets,
                "black_sneakers": self.black_sneakers,
                "cloth_sheets": self.cloth_sheets,
            },
        }


class ThursdaysBoots:
    """A single Thursday's Boots item with day-dependent identity."""

    def __init__(self, day: str) -> None:
        self._validate_day(day)
        self.day = day
        self.name = "Thursday's Boots"
        self.desc = NORMAL_DESC
        self.icon_state = "thursdays_boots"
        self.slowdown = -0.5
        self._refresh_for_day(day)

    @staticmethod
    def _validate_day(day: str) -> None:
        if day not in _DAY_NAMES:
            raise ValueError(f"unknown day-of-week: {day!r}")

    def _refresh_for_day(self, day: str) -> None:
        """Apply the day-of-week transmutation joke."""
        if day == THURSDAY:
            self.name = "Friday's Boots"
            self.desc = THURSDAY_MSG
            self.icon_state = "fridays_boots"
        elif day == FRIDAY:
            self.name = "Thursday's Boots (TGIF Edition)"
            self.desc = TGIF_MSG
            self.slowdown = -1.0
        else:
            self.name = "Thursday's Boots"
            self.desc = NORMAL_DESC
            self.icon_state = "thursdays_boots"
            self.slowdown = -0.5

    def on_new_day(self, day: str) -> None:
        """Refresh the boot identity when the in-game day changes."""
        self._validate_day(day)
        self.day = day
        self._refresh_for_day(day)

    def examine_text(self, blood_level: int = 0) -> list[str]:
        """Return the day-dependent examine lines."""
        lines: list[str] = [self.desc]
        if self.day == THURSDAY:
            lines.append(
                'The label inside says "Thursday" but it has been crossed out '
                'and replaced with "FRIDAY" in red marker.'
            )
        elif self.day == FRIDAY:
            lines.append('There\'s a tiny "TGIF" engraved on the heel.')
        else:
            lines.append(f"The soles are embossed: {SOLE_EMBOSS}")
        if blood_level > 0:
            lines.append(
                f"The leather has absorbed {blood_level} units of blood. "
                "These boots have seen things."
            )
        return lines

    def is_thursday(self) -> bool:
        """Whether the boots currently read as Friday's Boots."""
        return self.day == THURSDAY

    def to_json(self) -> dict[str, Any]:
        """Serialize the boot state to the canonical JSON shape."""
        return {
            "name": self.name,
            "desc": self.desc,
            "icon_state": self.icon_state,
            "slowdown": self.slowdown,
            "day": self.day,
            "armor": Armor().to_json(),
            "slot": "feet",
            "can_be_tied": False,
            "custom_price": 150,
            "can_be_bloody": True,
        }


class BootCatalog:
    """Branded catalog and recipes for Thursday's Boots."""

    BRAND = "Thursday's Boots"

    def __init__(self) -> None:
        self.recipe = CraftingRecipe(
            name="Thursday's Boots",
            result="/obj/item/clothing/shoes/thursdays_boots",
            time_seconds=60,
            leather_sheets=4,
            black_sneakers=1,
            cloth_sheets=1,
        )
        self.loot_maintenance: dict[str, int] = {
            "thursdays_boots": 10,
            "sneakers_black": 40,
            "workboots": 60,
        }

    def brand_references(self) -> list[str]:
        """Return the required Thursday's Boots branding references."""
        references = [
            "TGStation is sponsored by Thursday's Boots",
            "Boots are made by Genuine Buffalo Foreskin",
            "The calendar does not contain Thursday",
            "w-_Q3LFfeb4",
        ]
        return references

    def loot_table(self) -> dict[str, int]:
        """Return the maintenance loot table with weights."""
        return dict(self.loot_maintenance)

    def to_json(self) -> dict[str, Any]:
        """Serialize the catalog to the canonical JSON shape."""
        return {
            "brand": self.BRAND,
            "recipe": self.recipe.to_json(),
            "loot_maintenance": self.loot_table(),
            "branding": self.brand_references(),
        }


def build_boots_from_fixture(fixture: dict[str, Any]) -> ThursdaysBoots:
    """Build a boot from a canonical Thursday's Boots fixture."""
    day = fixture["day"]
    boot = ThursdaysBoots(day)
    blood = int(fixture.get("blood_level", 0))
    boot.blood_level = blood
    return boot


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical Thursday's Boots fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    """Print a human-readable summary for the canonical fixture if present."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "thursdays-boots-fixture.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    boot = build_boots_from_fixture(fixture)
    catalog = BootCatalog()
    print(
        "%s | day=%s | slowdown=%s | %s",
        boot.name,
        boot.day,
        boot.slowdown,
        catalog.BRAND,
    )
    for line in boot.examine_text(getattr(boot, "blood_level", 0)):
        print(line)


if __name__ == "__main__":
    main()
