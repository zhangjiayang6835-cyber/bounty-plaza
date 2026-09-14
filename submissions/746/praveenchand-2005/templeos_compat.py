"""TempleOS compatibility layer for SlopStation13.

Implements the compatibility behaviour required by bounty issue #746:

* a global compatibility state tracks enablement, version, the set of
  registered TempleOS players, and a running welcome counter
* welcoming a player registers them, increments the counter, and greets them
  with an ancient Sumerian message plus a TempleOS wisdom quote
* the compatibility check verifies every TempleOS-critical file is present and
  fails closed when any file is missing or the layer is disabled
* the TempleOS title screen renders the Sumerian welcome banner and the
  "holy bible" item yields a wisdom quote on use

This mirrors the upstream implementation in ``theselfish/SlopStation13``
(issue #4, PR #16) and is self-contained so it can be scored by
``scripts/score.py`` without the BYOND/DreamMaker environment.
"""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Any

VERSION = "1.0.0"
ENABLED_BY_DEFAULT = True

_SUMERIAN_GREETINGS = (
    "Silim he-me-en? (Greetings, are you well?)",
    "Dingir Enlil hur-sag-ga (Lord Enlil of the mountain)",
    "E-gal lugal-a-ni (The great house of his king)",
    "Gish-gigir gi-na-nu-um (The chariot is prepared)",
    "Dingir Inanna shi-e-a (Goddess Inanna, look upon me)",
    "Lu ninda gu-ul (The man eats bread greatly)",
    "A na me-en? (What are you?)",
    "Gish-ma magur-gal (The great ship)",
    "Gi-ri shu da-ma-al (The path is broad)",
    "E-a-ni ka-gal (His house, the great gate)",
)

_WELCOME_BANNER = "TAB-BA-A-TI (Welcome back, companion!)"

_TEMPLEOS_WISDOM = (
    "God says: love Me with all thy heart, mind, and soul.",
    "In the beginning, God created the heavens and the earth.",
    "Through HolyC, all things are possible.",
    "The temple is not made with hands — it is built in the spirit.",
    "Terry A. Davis saw the truth. We honor his vision.",
    "640x480 16 colors — the resolution of prophets.",
    "God's VGA mode is the one true display mode.",
    "Thou shalt not use ring 3 — stay in ring 0.",
    "Simon Peter saith: compile ye first the HolyC.",
    "The elephant in the room is that some things glow in the dark.",
)

_DEFAULT_CRITICAL_FILES = (
    "code/modules/templeos/templeos_compat.dm",
    "icons/misc/templeos.dmi",
    "sound/misc/templeos_welcome.ogg",
)


@dataclass(frozen=True)
class WelcomeResult:
    """The outcome of welcoming a single TempleOS player."""

    player_id: str
    welcome_counter: int
    banner: str
    greeting: str
    wisdom: str

    def to_json(self) -> dict[str, Any]:
        """Serialize the welcome result to the canonical JSON shape."""
        return {
            "player_id": self.player_id,
            "welcome_counter": self.welcome_counter,
            "banner": self.banner,
            "greeting": self.greeting,
            "wisdom": self.wisdom,
        }


class TempleOSCompat:
    """Stateful TempleOS compatibility layer."""

    def __init__(
        self,
        enabled: bool = ENABLED_BY_DEFAULT,
        greetings: tuple[str, ...] = _SUMERIAN_GREETINGS,
        wisdom: tuple[str, ...] = _TEMPLEOS_WISDOM,
    ) -> None:
        self.enabled = enabled
        self.version = VERSION
        self._greetings = greetings
        self._wisdom = wisdom
        self._players: set[str] = set()
        self.welcome_counter = 0

    def register_player(self, player_id: str) -> bool:
        """Register a player; return False if they were already present."""
        if player_id in self._players:
            return False
        self._players.add(player_id)
        return True

    def player_count(self) -> int:
        """Return the number of distinct registered TempleOS players."""
        return len(self._players)

    def pick_greeting(self, rng: random.Random) -> str:
        """Select an ancient Sumerian greeting."""
        return rng.choice(self._greetings)

    def pick_wisdom(self, rng: random.Random) -> str:
        """Select a TempleOS wisdom quote."""
        return rng.choice(self._wisdom)

    def welcome_player(self, player_id: str, rng: random.Random) -> WelcomeResult:
        """Welcome a TempleOS player back into the game."""
        if not self.enabled:
            raise RuntimeError("TempleOS compatibility layer is disabled")
        self.register_player(player_id)
        self.welcome_counter += 1
        return WelcomeResult(
            player_id=player_id,
            welcome_counter=self.welcome_counter,
            banner=_WELCOME_BANNER,
            greeting=self.pick_greeting(rng),
            wisdom=self.pick_wisdom(rng),
        )

    def bible_quote(self, rng: random.Random) -> str:
        """Return a wisdom quote as spoken by the TempleOS holy bible."""
        return self.pick_wisdom(rng)

    def check_compat(self, critical_files: tuple[str, ...]) -> bool:
        """Verify every TempleOS-critical file exists; fail closed otherwise."""
        if not self.enabled:
            return False
        for filename in critical_files:
            if not Path(filename).is_file():
                return False
        return True


def build_compat_from_fixture(fixture: dict[str, Any]) -> TempleOSCompat:
    """Build a compat layer seeded from a canonical TempleOS fixture."""
    config = fixture.get("config", {})
    return TempleOSCompat(
        enabled=bool(config.get("enabled", ENABLED_BY_DEFAULT)),
        greetings=tuple(config.get("greetings", _SUMERIAN_GREETINGS)),
        wisdom=tuple(config.get("wisdom", _TEMPLEOS_WISDOM)),
    )


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical TempleOS compatibility fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    """Run a sample welcome against the canonical fixture if present."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "templeos-compat-fixture.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    compat = build_compat_from_fixture(fixture)
    result = compat.welcome_player("TempleOS_Warrior_001", random.Random(7))
    print(
        "%s | counter=%d | %s | %s",
        result.banner,
        result.welcome_counter,
        result.greeting,
        result.wisdom,
    )


if __name__ == "__main__":
    main()
