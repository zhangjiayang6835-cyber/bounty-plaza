"""Tests for the Runescape-inspired chat effects.

Covers the acceptance criteria for bounty #741:

1. Colour effects: yellow (default), red, green, cyan, purple, white.
2. Flash effects: flash1 (red/yellow), flash2 (cyan/blue), flash3 (light/dark green).
3. Glow effects: glow1, glow2, glow3, rainbow.
4. Motion effects: wave, wave2, shake, slide, scroll.
"""

from __future__ import annotations

import json
from pathlib import Path

from runechat_effects import (
    ALL_EFFECTS,
    ChatEffect,
    RuneChatEffectRegistry,
    build_registry_from_fixture,
    load_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "runechat-effects-fixture.json"
).resolve()

REGISTRY = RuneChatEffectRegistry()


def test_yellow_is_default_colour() -> None:
    """Yellow is the default chat colour."""
    effect = REGISTRY.resolve("yellow")
    assert effect.kind == "colour"
    assert effect.colours == ("#ffff00",)


def test_solid_colours_resolve() -> None:
    """All six solid colour effects resolve."""
    for name in ("red", "green", "cyan", "purple", "white"):
        effect = REGISTRY.resolve(name)
        assert effect.kind == "colour"
        assert len(effect.colours) == 1


def test_flash1_red_yellow() -> None:
    """flash1 alternates red and yellow."""
    effect = REGISTRY.resolve("flash1")
    assert effect.kind == "flash"
    assert effect.colours == ("#ff0000", "#ffff00")


def test_flash2_cyan_blue() -> None:
    """flash2 alternates cyan and blue."""
    effect = REGISTRY.resolve("flash2")
    assert effect.kind == "flash"
    assert effect.colours == ("#00ffff", "#0000ff")


def test_flash3_light_dark_green() -> None:
    """flash3 alternates light and dark green."""
    effect = REGISTRY.resolve("flash3")
    assert effect.kind == "flash"
    assert effect.colours == ("#90ee90", "#006400")


def test_glow1_fade_sequence() -> None:
    """glow1 fades red->orange->yellow->green->cyan."""
    effect = REGISTRY.resolve("glow1")
    assert effect.kind == "glow"
    assert effect.colours == ("#ff0000", "#ffa500", "#ffff00", "#00ff00", "#00ffff")


def test_glow2_fade_sequence() -> None:
    """glow2 fades red->magenta->blue->dark red."""
    effect = REGISTRY.resolve("glow2")
    assert effect.kind == "glow"
    assert effect.colours == ("#ff0000", "#ff00ff", "#0000ff", "#8b0000")


def test_glow3_fade_sequence() -> None:
    """glow3 fades white->green->white->cyan."""
    effect = REGISTRY.resolve("glow3")
    assert effect.kind == "glow"
    assert effect.colours == ("#ffffff", "#00ff00", "#ffffff", "#00ffff")


def test_rainbow_is_glow() -> None:
    """Rainbow turns text into a rainbow colour sequence."""
    effect = REGISTRY.resolve("rainbow")
    assert effect.kind == "glow"
    assert len(effect.colours) >= 5


def test_wave_motion() -> None:
    """Wave moves text up and down like a wave."""
    effect = REGISTRY.resolve("wave")
    assert effect.kind == "motion"
    assert effect.css_class == "runechat-wave"


def test_wave2_motion() -> None:
    """Wave2 waves text diagonally."""
    effect = REGISTRY.resolve("wave2")
    assert effect.kind == "motion"
    assert effect.css_class == "runechat-wave2"


def test_shake_motion() -> None:
    """Shake shakes text wackily."""
    effect = REGISTRY.resolve("shake")
    assert effect.kind == "motion"
    assert effect.css_class == "runechat-shake"


def test_slide_motion() -> None:
    """Slide moves text in from above and out below."""
    effect = REGISTRY.resolve("slide")
    assert effect.kind == "motion"
    assert effect.css_class == "runechat-slide"


def test_scroll_motion() -> None:
    """Scroll moves text from right to left."""
    effect = REGISTRY.resolve("scroll")
    assert effect.kind == "motion"
    assert effect.css_class == "runechat-scroll"


def test_unknown_effect_raises() -> None:
    """An unknown effect name fails closed."""
    try:
        REGISTRY.resolve("neon_pink")
    except ValueError:
        return
    raise AssertionError("expected ValueError for unknown effect")


def test_effect_count_matches_spec() -> None:
    """The registry covers all 18 specified effects."""
    assert len(ALL_EFFECTS) == 18
    assert len(REGISTRY.all_names()) == 18


def test_colour_effect_classifier() -> None:
    """The colour classifier only accepts solid colours."""
    assert REGISTRY.colour_effect("yellow") is True
    assert REGISTRY.colour_effect("wave") is False


def test_motion_effect_classifier() -> None:
    """The motion classifier only accepts motion effects."""
    assert REGISTRY.motion_effect("scroll") is True
    assert REGISTRY.motion_effect("red") is False


def test_every_effect_has_css_class() -> None:
    """Every effect resolves to a css_class for maptext rendering."""
    for name in REGISTRY.all_names():
        assert REGISTRY.resolve(name).css_class.startswith("runechat-")


def test_json_shape() -> None:
    """An effect serializes to the canonical JSON shape."""
    effect: ChatEffect = REGISTRY.resolve("glow2")
    payload = effect.to_json()
    for field in ("name", "kind", "css_class", "colours"):
        assert field in payload
    assert payload["name"] == "glow2"
    assert len(payload["colours"]) == 4


def test_fixture_builds_registry() -> None:
    """The canonical fixture resolves every expected effect."""
    fixture = load_fixture(FIXTURE)
    registry = build_registry_from_fixture(fixture)
    for name in fixture["expected_effects"]:
        assert registry.resolve(name).name == name
