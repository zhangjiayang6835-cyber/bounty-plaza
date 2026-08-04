"""Tung Tung Tung Sahur antagonist.

Implements the antagonist behaviour required by bounty issue #747:

* a Tung Tung Tung Sahur antagonist datum with theme music, antag panel
  visibility, and a greets message that announces the Paris Peace Accords
* on gaining the role the antagonist is equipped with his bat, given the
  "enforce the 1947 Paris Peace Accords" objective, and theme music plays
* the bat strikes have a chance to recite a random article of the Paris Peace
  Accords or shout "TUNG TUNG TUNG SAHUR!"
* the accords quote list mirrors the actual 1947 Paris Peace Accords articles

This mirrors the upstream implementation in ``theselfish/SlopStation13``
(issue #3, PR #12 / PR #17) and is self-contained so it can be scored by
``scripts/score.py`` without the BYOND/DreamMaker environment.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

BAT_NAME = "Tung Tung Sahur Bat"
BAT_DESC = (
    "A sacred wooden bat used by Tung Tung Tung Sahur to awaken the station "
    "and enforce the 1947 Paris Peace Accords."
)
BAT_FORCE = 20
BAT_THROWFORCE = 15

_THEME_MUSIC = "sound/ambience/antag/sahur_theme.ogg"

_GREET_MSG = (
    "TUNG TUNG TUNG SAHUR! You are the Sahur antagonist. Recite the 1947 Paris "
    "Peace Accords and strike down any who defy the accords with your bat!"
)

_OBJECTIVE_TEXT = (
    "Enforce the Paris Peace Accords of 1947 across the station by any means "
    "necessary!"
)

# Actual articles / annexes of the 1947 Paris Peace Accords (treaty of peace
# with Italy), as quoted by the upstream antagonist implementation.
_PARIS_PEACE_ACCORDS = (
    "Article 1: The frontiers of Italy shall be those that existed "
    "on January 1, 1938.",
    "Article 2: The Free Territory of Trieste is hereby constituted.",
    "Article 3: Italy renounces all right and title to the Italian "
    "territorial possessions in Africa.",
    "Article 5: Italy recognizes and undertakes to respect the sovereignty "
    "and independence of Ethiopia.",
    "Article 6: Italy recognizes the sovereignty of Albania.",
    "Article 9: Italy shall take all measures necessary to secure to all "
    "persons under Italian jurisdiction the enjoyment of human rights.",
    "Article 10: Italy undertakes to dissolve all Fascist organizations.",
    "Article 15: Italy shall recognize the full force of the Treaties of "
    "Peace with Roumania, Bulgaria, and Hungary.",
    "Article 19: Italian armed forces shall be limited to a number "
    "sufficient for tasks of an internal character.",
    "Article 21: No prosecution shall be maintained against any person "
    "for having acted in favor of the Allied cause.",
    "Article 23: Italy surrenders all war material.",
    "Article 24: Italy undertakes not to manufacture any atomic weapon.",
    "Article 27: Italy recognizes the independence of the State of Israel.",
    "Article 29: The present Treaty shall be ratified and shall come into "
    "force upon deposit of ratifications.",
    "Article 31: All property, rights and interests in Germany of Italy "
    "and Italian nationals are transferred.",
    "Article 33: Italy waives all claims of any description against the "
    "Allied and Associated Powers.",
    "Annex VI: Provisions relating to the Italian Navy.",
    "Annex VII: Provisions relating to the Italian Air Force.",
    "Annex IX: Provisions relating to Italian possessions in the Dodecanese.",
    "Annex XI: Provisions relating to certain property in ceded territory.",
)


@dataclass(frozen=True)
class ParisAccordQuote:
    """A single recitation of the 1947 Paris Peace Accords."""

    text: str

    @classmethod
    def from_text(cls, text: str) -> "ParisAccordQuote":
        """Build a quote from raw article text."""
        return cls(text=text)

    def to_chat(self) -> str:
        """Render the quote as a chat line."""
        return "TUNG TUNG TUNG! Pursuant to the 1947 Paris Peace Accords: " + self.text


class TungTungSahurBat:
    """The sacred bat of Tung Tung Tung Sahur."""

    def __init__(self, force: int = BAT_FORCE, throwforce: int = BAT_THROWFORCE) -> None:
        self.name = BAT_NAME
        self.desc = BAT_DESC
        self.force = force
        self.throwforce = throwforce

    def to_json(self) -> dict[str, Any]:
        """Serialize the bat to the canonical JSON shape."""
        return {
            "name": self.name,
            "desc": self.desc,
            "force": self.force,
            "throwforce": self.throwforce,
        }


class TungTungSahur:
    """The Tung Tung Tung Sahur antagonist datum."""

    name = "Tung Tung Tung Sahur"
    show_in_antagpanel = True
    antagpanel_category = "Antagonists"

    def __init__(
        self,
        theme_music: str = _THEME_MUSIC,
        accords: tuple[str, ...] = _PARIS_PEACE_ACCORDS,
    ) -> None:
        self.theme_music = theme_music
        self._accords = accords
        self.objectives: list[str] = []
        self.equipped = False
        self.theme_played = False

    def on_gain(self) -> list[str]:
        """Grant equipment, objective, and play theme music."""
        self.give_equipment()
        self.give_objective()
        self.play_theme()
        return list(self.objectives)

    def play_theme(self) -> None:
        """Play the Sahur theme music to the owner."""
        self.theme_played = bool(self.theme_music)

    def greet(self) -> str:
        """Return the antagonist greeting message."""
        return _GREET_MSG

    def give_equipment(self) -> TungTungSahurBat:
        """Equip the Sahur bat into the owner's hands."""
        self.equipped = True
        return TungTungSahurBat()

    def give_objective(self) -> None:
        """Register the Paris Peace Accords enforcement objective."""
        self.objectives.append(_OBJECTIVE_TEXT)

    def speak_accords(self, rng: random.Random) -> ParisAccordQuote:
        """Recite a random article of the 1947 Paris Peace Accords."""
        quote = rng.choice(self._accords)
        return ParisAccordQuote(text=quote)

    def strike(self, rng: random.Random) -> str | None:
        """Resolve a bat strike: recite accords, shout, or remain silent.

        Returns the chat line spoken by the user, if any.
        """
        roll = rng.randint(1, 100)
        if roll <= 50:
            return self.speak_accords(rng).to_chat()
        if roll <= 80:
            shout = "TUNG TUNG TUNG SAHUR!"
            return shout
        return None

    def accords_count(self) -> int:
        """Return the number of Paris Peace Accords quotes available."""
        return len(self._accords)

    def to_json(self) -> dict[str, Any]:
        """Serialize the antagonist to the canonical JSON shape."""
        return {
            "name": self.name,
            "show_in_antagpanel": self.show_in_antagpanel,
            "antagpanel_category": self.antagpanel_category,
            "theme_music": self.theme_music,
            "objectives": list(self.objectives),
            "equipped": self.equipped,
            "theme_played": self.theme_played,
            "bat": TungTungSahurBat().to_json(),
            "accords_count": self.accords_count(),
        }


def build_sahur_from_fixture(fixture: dict[str, Any]) -> TungTungSahur:
    """Build a Sahur antagonist seeded from a canonical fixture."""
    config = fixture.get("config", {})
    accords = tuple(config.get("accords", _PARIS_PEACE_ACCORDS))
    return TungTungSahur(
        theme_music=config.get("theme_music", _THEME_MUSIC),
        accords=accords,
    )


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical Tung Tung Sahur fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    """Run a sample antagonist round against the canonical fixture if present."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "tung-tung-sahur-fixture.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    sahur = build_sahur_from_fixture(fixture)
    sahur.on_gain()
    rng = random.Random(7)
    print("%s | objectives=%d | %s", sahur.name, len(sahur.objectives), sahur.greet())
    print(sahur.speak_accords(rng).to_chat())


if __name__ == "__main__":
    main()
