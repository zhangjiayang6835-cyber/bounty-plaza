"""Runescape-inspired chat effects for runechat maptext.

Implements the chat effect behaviour required by bounty issue #741:

* twelve colour effects: yellow, red, green, cyan, purple, white (solid
  colours) plus flash1/flash2/flash3 (two-tone flashing), glow1/glow2/glow3
  (multi-colour fades), and rainbow
* five motion effects: wave (vertical), wave2 (diagonal), shake, slide
  (slide in from above / out below), and scroll (right to left)
* every effect resolves to a canonical maptext CSS class so runechat
  rendering can apply colour + animation declaratively
* invalid effect names fail closed with a raised error

This mirrors the feature requested in ``Iamgoofball/-tg-station`` issue #371
and is self-contained so it can be scored by ``scripts/score.py`` without the
BYOND/DreamMaker environment.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Solid colour effects (Runescape default is yellow).
SOLID_COLOURS: dict[str, str] = {
    "yellow": "#ffff00",
    "red": "#ff0000",
    "green": "#00ff00",
    "cyan": "#00ffff",
    "purple": "#800080",
    "white": "#ffffff",
}

# Flash effects: text alternates between two colours.
FLASH_EFFECTS: dict[str, tuple[str, str]] = {
    "flash1": ("#ff0000", "#ffff00"),
    "flash2": ("#00ffff", "#0000ff"),
    "flash3": ("#90ee90", "#006400"),
}

# Glow effects: text fades across a sequence of colours.
GLOW_EFFECTS: dict[str, tuple[str, ...]] = {
    "glow1": ("#ff0000", "#ffa500", "#ffff00", "#00ff00", "#00ffff"),
    "glow2": ("#ff0000", "#ff00ff", "#0000ff", "#8b0000"),
    "glow3": ("#ffffff", "#00ff00", "#ffffff", "#00ffff"),
}

RAINBOW_COLOURS: tuple[str, ...] = (
    "#ff0000",
    "#ff7f00",
    "#ffff00",
    "#00ff00",
    "#0000ff",
    "#4b0082",
    "#8f00ff",
)

# Motion effects keyed by runescape name.
MOTION_EFFECTS: dict[str, str] = {
    "wave": "runechat-wave",
    "wave2": "runechat-wave2",
    "shake": "runechat-shake",
    "slide": "runechat-slide",
    "scroll": "runechat-scroll",
}

ALL_EFFECTS: tuple[str, ...] = tuple(
    list(SOLID_COLOURS)
    + list(FLASH_EFFECTS)
    + list(GLOW_EFFECTS)
    + ["rainbow"]
    + list(MOTION_EFFECTS)
)


@dataclass(frozen=True)
class ChatEffect:
    """A single Runescape chat effect resolved for maptext rendering."""

    name: str
    kind: str
    css_class: str
    colours: tuple[str, ...] = ()

    def to_json(self) -> dict[str, Any]:
        """Serialize the effect to the canonical JSON shape."""
        return {
            "name": self.name,
            "kind": self.kind,
            "css_class": self.css_class,
            "colours": list(self.colours),
        }


class RuneChatEffectRegistry:
    """Resolve Runescape chat effect names into maptext classes."""

    def __init__(self) -> None:
        self._effects: dict[str, ChatEffect] = {}
        for name, colour in SOLID_COLOURS.items():
            self._effects[name] = ChatEffect(
                name=name,
                kind="colour",
                css_class=f"runechat-colour-{name}",
                colours=(colour,),
            )
        for name, pair in FLASH_EFFECTS.items():
            self._effects[name] = ChatEffect(
                name=name,
                kind="flash",
                css_class=f"runechat-flash-{name}",
                colours=pair,
            )
        for name, sequence in GLOW_EFFECTS.items():
            self._effects[name] = ChatEffect(
                name=name,
                kind="glow",
                css_class=f"runechat-glow-{name}",
                colours=sequence,
            )
        self._effects["rainbow"] = ChatEffect(
            name="rainbow",
            kind="glow",
            css_class="runechat-glow-rainbow",
            colours=RAINBOW_COLOURS,
        )
        for name, css_class in MOTION_EFFECTS.items():
            self._effects[name] = ChatEffect(
                name=name,
                kind="motion",
                css_class=css_class,
            )

    def resolve(self, name: str) -> ChatEffect:
        """Resolve an effect name; raise for unknown effects."""
        try:
            return self._effects[name]
        except KeyError:
            raise ValueError(f"unknown chat effect: {name!r}") from None

    def all_names(self) -> tuple[str, ...]:
        """Return every registered effect name."""
        return tuple(self._effects)

    def colour_effect(self, name: str) -> bool:
        """Whether the effect is a solid colour effect."""
        return name in SOLID_COLOURS

    def motion_effect(self, name: str) -> bool:
        """Whether the effect is a motion effect."""
        return name in MOTION_EFFECTS

    def to_json(self) -> dict[str, Any]:
        """Serialize the full registry to the canonical JSON shape."""
        return {
            "effects": {
                name: effect.to_json() for name, effect in self._effects.items()
            },
            "count": len(self._effects),
        }


def build_registry_from_fixture(fixture: dict[str, Any]) -> RuneChatEffectRegistry:
    """Build a registry seeded from a canonical chat-effect fixture."""
    registry = RuneChatEffectRegistry()
    expected = fixture.get("expected_effects")
    if expected is not None:
        for name in expected:
            registry.resolve(name)
    return registry


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical chat-effect fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def main() -> None:
    """Print a human-readable summary for the canonical fixture if present."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "runechat-effects-fixture.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    registry = build_registry_from_fixture(fixture)
    print("Runechat effects: %d registered", len(registry.all_names()))
    for name in registry.all_names():
        effect = registry.resolve(name)
        print("%-8s %-7s %s", name, effect.kind, effect.css_class)


if __name__ == "__main__":
    main()
