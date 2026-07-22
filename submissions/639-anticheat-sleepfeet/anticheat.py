"""
Anticheat heuristics for SS13 sleepfeet / aimbot / autoclick detection.

Python reference of the DreamMaker logic shipped upstream so Plaza scoring
can exercise behavior with pytest. The production patch lives under patch/.
"""

from __future__ import annotations

from dataclasses import dataclass, field


SLEEPFEET_MOVE_WARN_THRESHOLD = 8
SLEEPFEET_MOVE_WINDOW = 30  # 3s in dm ticks of 0.1s ≈ abstracted units
SLEEPFEET_CLICK_WARN_THRESHOLD = 6
SLEEPFEET_CLICK_WINDOW = 30
AIMBOT_HIT_WARN_THRESHOLD = 2
AIMBOT_HIT_MIN_SCORE = 10
AUTOCLICK_TRIP_WARN_THRESHOLD = 3
AUTOCLICK_TRIP_WINDOW = 100
REPORT_COOLDOWN = 300


@dataclass
class ClientState:
    is_holder: bool = False
    is_living: bool = True
    is_sleeping: bool = False
    is_knocked_out: bool = False
    sleep_immune: bool = False
    time: int = 0
    move_delay: int = 0
    sleepfeet_move_count: int = 0
    sleepfeet_move_reset: int = 0
    sleepfeet_click_count: int = 0
    sleepfeet_click_reset: int = 0
    aimbot_hits: int = 0
    autoclick_trip_count: int = 0
    autoclick_trip_reset: int = 0
    last_report: dict[str, int] = field(default_factory=dict)
    reports: list[str] = field(default_factory=list)


def is_sleepfeet_incapacitated(client: ClientState) -> bool:
    if client.is_holder or not client.is_living:
        return False
    if client.sleep_immune:
        return False
    return client.is_sleeping or client.is_knocked_out


def report_anticheat(client: ClientState, reason: str, detail: str) -> bool:
    if not reason:
        return False
    last = client.last_report.get(reason)
    if last is not None and (client.time - last) < REPORT_COOLDOWN:
        return False
    client.last_report[reason] = client.time
    client.reports.append(f"{reason}:{detail}")
    return True


def check_sleepfeet_move(client: ClientState) -> bool:
    """Return True if the move must be hard-blocked."""
    if not is_sleepfeet_incapacitated(client):
        return False

    if client.time > client.sleepfeet_move_reset:
        client.sleepfeet_move_count = 0
        client.sleepfeet_move_reset = client.time + SLEEPFEET_MOVE_WINDOW

    client.sleepfeet_move_count += 1

    if client.sleepfeet_move_count >= SLEEPFEET_MOVE_WARN_THRESHOLD:
        report_anticheat(
            client,
            "sleepfeet_move",
            f"Repeated movement while asleep ({client.sleepfeet_move_count})",
        )
        client.move_delay = max(client.move_delay, client.time + 10)

    return True


def check_sleepfeet_click(client: ClientState) -> bool:
    """Return True if the click must be ignored."""
    if not is_sleepfeet_incapacitated(client):
        return False

    if client.time > client.sleepfeet_click_reset:
        client.sleepfeet_click_count = 0
        client.sleepfeet_click_reset = client.time + SLEEPFEET_CLICK_WINDOW

    client.sleepfeet_click_count += 1

    if client.sleepfeet_click_count >= SLEEPFEET_CLICK_WARN_THRESHOLD:
        report_anticheat(
            client,
            "sleepfeet_click",
            f"Repeated clicks while asleep ({client.sleepfeet_click_count})",
        )

    return True


def check_aimbot_score(client: ClientState, ab_score: int) -> None:
    if client.is_holder or ab_score < AIMBOT_HIT_MIN_SCORE:
        return
    client.aimbot_hits += 1
    if client.aimbot_hits >= AIMBOT_HIT_WARN_THRESHOLD:
        report_anticheat(
            client,
            "aimbot",
            f"Middle-click aimbot pattern ({client.aimbot_hits} hits, score {ab_score})",
        )
        client.aimbot_hits = 0


def check_autoclick_trip(client: ClientState) -> None:
    if client.is_holder:
        return
    if client.time > client.autoclick_trip_reset:
        client.autoclick_trip_count = 0
        client.autoclick_trip_reset = client.time + AUTOCLICK_TRIP_WINDOW

    client.autoclick_trip_count += 1
    if client.autoclick_trip_count >= AUTOCLICK_TRIP_WARN_THRESHOLD:
        report_anticheat(
            client,
            "autoclick",
            f"Repeated second-click-limit trips ({client.autoclick_trip_count})",
        )
        client.autoclick_trip_count = 0
