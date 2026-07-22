"""Tests for sleepfeet / aimbot / autoclick anticheat heuristics."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anticheat import (
    AIMBOT_HIT_MIN_SCORE,
    AIMBOT_HIT_WARN_THRESHOLD,
    AUTOCLICK_TRIP_WARN_THRESHOLD,
    SLEEPFEET_CLICK_WARN_THRESHOLD,
    SLEEPFEET_MOVE_WARN_THRESHOLD,
    ClientState,
    check_aimbot_score,
    check_autoclick_trip,
    check_sleepfeet_click,
    check_sleepfeet_move,
    is_sleepfeet_incapacitated,
)


def test_sleep_immune_not_incapacitated():
    client = ClientState(is_sleeping=True, sleep_immune=True)
    assert is_sleepfeet_incapacitated(client) is False
    assert check_sleepfeet_move(client) is False


def test_sleepfeet_move_blocks_and_reports():
    client = ClientState(is_sleeping=True, time=100)
    for _ in range(SLEEPFEET_MOVE_WARN_THRESHOLD - 1):
        assert check_sleepfeet_move(client) is True
        assert not any(r.startswith("sleepfeet_move:") for r in client.reports)

    assert check_sleepfeet_move(client) is True
    assert any(r.startswith("sleepfeet_move:") for r in client.reports)
    assert client.move_delay >= client.time + 10


def test_conscious_move_not_blocked():
    client = ClientState(is_sleeping=False, is_knocked_out=False)
    assert check_sleepfeet_move(client) is False


def test_sleepfeet_click_blocks_and_reports():
    client = ClientState(is_knocked_out=True, time=50)
    for _ in range(SLEEPFEET_CLICK_WARN_THRESHOLD - 1):
        assert check_sleepfeet_click(client) is True
    assert check_sleepfeet_click(client) is True
    assert any(r.startswith("sleepfeet_click:") for r in client.reports)


def test_aimbot_requires_strong_repeated_hits():
    client = ClientState()
    check_aimbot_score(client, AIMBOT_HIT_MIN_SCORE - 1)
    assert client.reports == []

    for _ in range(AIMBOT_HIT_WARN_THRESHOLD - 1):
        check_aimbot_score(client, AIMBOT_HIT_MIN_SCORE)
    assert client.reports == []

    check_aimbot_score(client, AIMBOT_HIT_MIN_SCORE)
    assert any(r.startswith("aimbot:") for r in client.reports)


def test_autoclick_trip_escalation():
    client = ClientState(time=10)
    for _ in range(AUTOCLICK_TRIP_WARN_THRESHOLD - 1):
        check_autoclick_trip(client)
    assert client.reports == []

    check_autoclick_trip(client)
    assert any(r.startswith("autoclick:") for r in client.reports)


def test_holders_are_exempt():
    client = ClientState(is_holder=True, is_sleeping=True)
    assert check_sleepfeet_move(client) is False
    check_aimbot_score(client, 99)
    check_autoclick_trip(client)
    assert client.reports == []
