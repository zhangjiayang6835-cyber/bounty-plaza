"""Tests for the TempleOS compatibility layer.

Covers the acceptance criteria for bounty #746:

1. The compatibility layer is enabled by default and tracks a version.
2. Welcoming a player registers them, increments the welcome counter, and
   returns an ancient Sumerian banner plus a wisdom quote.
3. The compatibility check fails closed when any critical file is missing or
   the layer is disabled.
4. Distinct players are counted exactly once; re-welcoming does not double
   count.
"""

from __future__ import annotations

import json
import random
from pathlib import Path

from templeos_compat import (
    TempleOSCompat,
    WelcomeResult,
    build_compat_from_fixture,
    load_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "templeos-compat-fixture.json"
).resolve()

SEED = random.Random(7)
P1 = "TempleOS_Warrior_001"
P2 = "Kernel_Dancer_042"
P3 = "Ring0_Prophet_777"


def test_enabled_by_default() -> None:
    """The compatibility layer is enabled by default."""
    compat = TempleOSCompat()
    assert compat.enabled is True
    assert compat.version == "1.0.0"


def test_disabled_layer_can_be_constructed() -> None:
    """A disabled compatibility layer can be constructed explicitly."""
    compat = TempleOSCompat(enabled=False)
    assert compat.enabled is False


def test_welcome_returns_banner() -> None:
    """A welcome result carries the Sumerian welcome banner."""
    compat = TempleOSCompat()
    result = compat.welcome_player(P1, SEED)
    assert "TAB-BA-A-TI" in result.banner


def test_welcome_returns_greeting() -> None:
    """A welcome result carries a Sumerian greeting."""
    compat = TempleOSCompat()
    result = compat.welcome_player(P1, SEED)
    assert result.greeting in compat._greetings


def test_welcome_returns_wisdom() -> None:
    """A welcome result carries a TempleOS wisdom quote."""
    compat = TempleOSCompat()
    result = compat.welcome_player(P1, SEED)
    assert result.wisdom in compat._wisdom


def test_welcome_increments_counter() -> None:
    """Each welcome increments the running welcome counter."""
    compat = TempleOSCompat()
    compat.welcome_player(P1, SEED)
    compat.welcome_player(P2, SEED)
    assert compat.welcome_counter == 2


def test_distinct_players_counted_once() -> None:
    """Distinct players are registered exactly once."""
    compat = TempleOSCompat()
    compat.register_player(P1)
    compat.register_player(P2)
    compat.register_player(P3)
    assert compat.player_count() == 3


def test_rewelcome_does_not_duplicate() -> None:
    """Re-registering an existing player returns False and does not add."""
    compat = TempleOSCompat()
    assert compat.register_player(P1) is True
    assert compat.register_player(P1) is False
    assert compat.player_count() == 1


def test_welcome_disabled_raises() -> None:
    """Welcoming while disabled fails closed with an error."""
    compat = TempleOSCompat(enabled=False)
    try:
        compat.welcome_player(P1, SEED)
    except RuntimeError:
        return
    raise AssertionError("expected RuntimeError for disabled welcome")


def test_check_compat_passes_with_all_files() -> None:
    """The compatibility check passes when every critical file is present."""
    compat = TempleOSCompat()
    # The patch file itself is a real TempleOS-critical file on disk.
    critical = (
        str(Path(__file__).resolve().parents[1] / "templeos_compat.py"),
    )
    assert compat.check_compat(critical) is True


def test_check_compat_fails_closed_on_missing_file() -> None:
    """The compatibility check fails closed when a file is missing."""
    compat = TempleOSCompat()
    critical = ("code/modules/templeos/does_not_exist.dm",)
    assert compat.check_compat(critical) is False


def test_check_compat_fails_closed_when_disabled() -> None:
    """The compatibility check fails closed when the layer is disabled."""
    compat = TempleOSCompat(enabled=False)
    critical = (str(Path(__file__).resolve().parents[1] / "templeos_compat.py"),)
    assert compat.check_compat(critical) is False


def test_default_critical_files_are_absent_by_default() -> None:
    """The DM/asset files only exist inside the game checkout."""
    compat = TempleOSCompat()
    assert (
        compat.check_compat(
            (
                "code/modules/templeos/templeos_compat.dm",
                "icons/misc/templeos.dmi",
            )
        )
        is False
    )


def test_bible_quote_is_wisdom() -> None:
    """The holy bible yields a wisdom quote on use."""
    compat = TempleOSCompat()
    quote = compat.bible_quote(SEED)
    assert quote in compat._wisdom


def test_fixture_builds_layer() -> None:
    """The canonical fixture builds an enabled compatibility layer."""
    fixture = load_fixture(FIXTURE)
    compat = build_compat_from_fixture(fixture)
    assert compat.enabled is True
    assert compat.player_count() == 0


def test_fixture_players_register() -> None:
    """Players listed in the fixture can be registered."""
    fixture = load_fixture(FIXTURE)
    compat = build_compat_from_fixture(fixture)
    for player_id in fixture["players"]:
        compat.register_player(player_id)
    assert compat.player_count() == len(fixture["players"])


def test_welcome_result_json_shape() -> None:
    """A welcome result serializes to the canonical JSON shape."""
    compat = TempleOSCompat()
    result: WelcomeResult = compat.welcome_player(P1, SEED)
    payload = result.to_json()
    for field in ("player_id", "welcome_counter", "banner", "greeting", "wisdom"):
        assert field in payload
    assert payload["player_id"] == P1
    assert payload["welcome_counter"] == 1
