"""Tests for the Tung Tung Tung Sahur antagonist.

Covers the acceptance criteria for bounty #747:

1. The antagonist datum exists with theme music, antag panel visibility, and
   a greeting that announces the Paris Peace Accords.
2. Gaining the role equips the bat, registers the objective, and plays theme
   music.
3. Bat strikes recite random articles of the 1947 Paris Peace Accords or shout
   "TUNG TUNG TUNG SAHUR!".
4. The accords quote list mirrors the actual 1947 Paris Peace Accords.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from tung_tung_sahur import (
    ParisAccordQuote,
    TungTungSahur,
    TungTungSahurBat,
    build_sahur_from_fixture,
    load_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "tung-tung-sahur-fixture.json"
).resolve()

SEED = random.Random(7)


def test_antagonist_has_name() -> None:
    """The antagonist is named Tung Tung Tung Sahur."""
    sahur = TungTungSahur()
    assert sahur.name == "Tung Tung Tung Sahur"


def test_theme_music_present() -> None:
    """The antagonist has theme music configured."""
    sahur = TungTungSahur()
    assert sahur.theme_music == "sound/ambience/antag/sahur_theme.ogg"


def test_antagpanel_visible() -> None:
    """The antagonist appears in the antag panel."""
    sahur = TungTungSahur()
    assert sahur.show_in_antagpanel is True
    assert sahur.antagpanel_category == "Antagonists"


def test_greet_announces_accords() -> None:
    """The greeting announces the Paris Peace Accords."""
    sahur = TungTungSahur()
    greeting = sahur.greet()
    assert "TUNG TUNG TUNG SAHUR" in greeting
    assert "Paris Peace Accords" in greeting


def test_on_gain_equips_bat() -> None:
    """Gaining the role equips the bat."""
    sahur = TungTungSahur()
    sahur.on_gain()
    assert sahur.equipped is True


def test_on_gain_adds_objective() -> None:
    """Gaining the role registers the enforce-accords objective."""
    sahur = TungTungSahur()
    sahur.on_gain()
    assert any("Enforce the Paris Peace Accords" in o for o in sahur.objectives)


def test_on_gain_plays_theme() -> None:
    """Gaining the role plays the theme music."""
    sahur = TungTungSahur()
    sahur.on_gain()
    assert sahur.theme_played is True


def test_bat_has_name_and_force() -> None:
    """The bat is named and has a damage force."""
    bat = TungTungSahurBat()
    assert bat.name == "Tung Tung Sahur Bat"
    assert bat.force == 20
    assert bat.throwforce == 15


def test_speak_accords_returns_article() -> None:
    """Speaking the accords returns a random article quote."""
    sahur = TungTungSahur()
    quote = sahur.speak_accords(SEED)
    assert isinstance(quote, ParisAccordQuote)
    assert "Article" in quote.text or "Annex" in quote.text


def test_quote_to_chat_prefix() -> None:
    """The chat line is prefixed with the Tung Tung call."""
    sahur = TungTungSahur()
    quote = sahur.speak_accords(SEED)
    assert "TUNG TUNG TUNG!" in quote.to_chat()
    assert "Pursuant to the 1947 Paris Peace Accords" in quote.to_chat()


def test_strike_may_recite_accords() -> None:
    """A bat strike can recite the accords."""
    sahur = TungTungSahur()
    found = False
    for seed in range(50):
        line = sahur.strike(random.Random(seed))
        if line and "Pursuant to the 1947 Paris Peace Accords" in line:
            found = True
            break
    assert found is True


def test_strike_may_shout() -> None:
    """A bat strike can shout TUNG TUNG TUNG SAHUR."""
    sahur = TungTungSahur()
    found = False
    for seed in range(50):
        line = sahur.strike(random.Random(seed))
        if line == "TUNG TUNG TUNG SAHUR!":
            found = True
            break
    assert found is True


def test_strike_may_be_silent() -> None:
    """A bat strike can produce no chat line."""
    sahur = TungTungSahur()
    silent = any(sahur.strike(random.Random(seed)) is None for seed in range(50))
    assert silent is True


def test_accords_include_real_articles() -> None:
    """The quote list mirrors the actual 1947 Paris Peace Accords."""
    sahur = TungTungSahur()
    assert sahur.accords_count() >= 6
    assert any("Trieste" in q for q in sahur._accords)
    assert any("Dodecanese" in q for q in sahur._accords)


def test_fixture_builds_sahur() -> None:
    """The canonical fixture builds a Sahur antagonist."""
    fixture = load_fixture(FIXTURE)
    sahur = build_sahur_from_fixture(fixture)
    assert sahur.name == "Tung Tung Tung Sahur"
    assert sahur.accords_count() == 4


def test_fixture_uses_canonical_accords() -> None:
    """The fixture's accords are part of the real 1947 treaty."""
    fixture = load_fixture(FIXTURE)
    sahur = build_sahur_from_fixture(fixture)
    all_text = " ".join(sahur._accords)
    assert "Trieste" in all_text
    assert "Ethiopia" in all_text


def test_json_shape() -> None:
    """The antagonist serializes to the canonical JSON shape."""
    sahur = TungTungSahur()
    sahur.on_gain()
    payload = sahur.to_json()
    for field in ("name", "theme_music", "objectives", "bat", "accords_count"):
        assert field in payload
    assert payload["theme_played"] is True
    assert payload["equipped"] is True
    assert payload["bat"]["force"] == 20
