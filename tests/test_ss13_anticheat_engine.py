"""Unit tests for SS13 Server-Authoritative Anti-Cheat & Exploit Mitigation Subsystem.
Resolves Issue #639: [BOUNTY] [IMPORTANT] [TIME-SENSITIVE] [$300] [AGENTIC / Opire] Anti-Cheat.
Upstream Reference: Iamgoofball/-tg-station#138.
"""

import pytest
from scripts.ss13_anticheat_engine import (
    SS13AntiCheatEngine,
    CheatType,
    Severity,
    PlayerState,
)


@pytest.fixture
def anticheat():
    ac = SS13AntiCheatEngine()
    # Place a solid reinforced wall at (15, 10)
    ac.set_tile_opaque(15, 10, is_opaque=True)
    return ac


def test_sleepfeet_exploit_blocked_when_sleeping_or_resting(anticheat):
    player = anticheat.register_player("CheaterMcGrief", x=10, y=10)

    # Valid movement while awake and standing
    m1 = anticheat.validate_movement_packet("CheaterMcGrief", target_x=11, target_y=10)
    assert m1["accepted"] is True
    assert m1["authoritative_x"] == 11

    # Exploit Attempt 1: Sleeping
    player.is_sleeping = True
    m2 = anticheat.validate_movement_packet("CheaterMcGrief", target_x=12, target_y=10)
    assert m2["accepted"] is False
    assert m2["exploit_mitigated"] == "SLEEPFEET"
    assert m2["authoritative_x"] == 11  # Coordinate remains unchanged

    # Exploit Attempt 2: Resting on wet floor
    player.is_sleeping = False
    player.is_resting = True
    m3 = anticheat.validate_movement_packet("CheaterMcGrief", target_x=12, target_y=10)
    assert m3["accepted"] is False
    assert m3["exploit_mitigated"] == "SLEEPFEET"

    # Exploit Attempt 3: Unconscious
    player.is_resting = False
    player.is_unconscious = True
    m4 = anticheat.validate_movement_packet("CheaterMcGrief", target_x=12, target_y=10)
    assert m4["accepted"] is False

    # Check alert was raised
    assert len(anticheat.alerts) == 3
    assert anticheat.alerts[0].cheat_type == CheatType.SLEEPFEET_EXPLOIT
    assert anticheat.alerts[0].severity == Severity.CRITICAL


def test_autoclicker_rate_limit_exceeded(anticheat):
    anticheat.register_player("ClickerBot", x=5, y=5)

    # Simulate 25 clicks in a single second (> 20 CPS limit)
    t = 100.0
    for _ in range(25):
        t += 0.03
        anticheat.record_click_event("ClickerBot", timestamp_s=t)

    # The 25th click should be rejected
    res = anticheat.record_click_event("ClickerBot", timestamp_s=t + 0.01)
    assert res["accepted"] is False
    assert res["reason"] == "AUTOCLICKER_CPS_LIMIT_EXCEEDED"
    assert any(a.cheat_type == CheatType.AUTOCLICKER for a in anticheat.alerts)


def test_autoclicker_uniform_variance_macro_detected(anticheat):
    anticheat.register_player("MacroSpammer", x=5, y=5)

    # Simulate 15 perfectly identical 50ms intervals (zero jitter)
    t = 100.0
    for _ in range(15):
        t += 0.0500000
        res = anticheat.record_click_event("MacroSpammer", timestamp_s=t)

    assert res["accepted"] is False
    assert res["reason"] == "UNIFORM_MACRO_DETECTED"


def test_aimbot_snap_turn_detection(anticheat):
    player = anticheat.register_player("Sniper360", x=10, y=10)
    player.facing_angle_deg = 0.0
    player.last_turn_timestamp = 10.0

    # Normal human turn: 45 degrees over 100ms
    res1 = anticheat.validate_target_aim("Sniper360", new_angle_deg=45.0, timestamp_s=10.10)
    assert res1["accepted"] is True
    assert player.facing_angle_deg == 45.0

    # Instant snap turn: 180 degrees over 5ms (0.005s)
    res2 = anticheat.validate_target_aim("Sniper360", new_angle_deg=225.0, timestamp_s=10.105)
    assert res2["accepted"] is False
    assert res2["reason"] == "AIMBOT_SNAP_TURN_REJECTED"
    assert any(a.cheat_type == CheatType.AIMBOT_SNAP for a in anticheat.alerts)


def test_wallhack_line_of_sight_raycast_mitigation(anticheat):
    player = anticheat.register_player("XRayViewer", x=10, y=10)

    # Clear line of sight to (14, 10)
    los1 = anticheat.validate_line_of_sight("XRayViewer", target_x=14, target_y=10)
    assert los1["has_los"] is True

    # Opaque barrier sits at (15, 10). Target is at (20, 10) behind wall
    los2 = anticheat.validate_line_of_sight("XRayViewer", target_x=20, target_y=10)
    assert los2["has_los"] is False
    assert los2["reason"] == "LINE_OF_SIGHT_OCCLUDED"
    assert any(a.cheat_type == CheatType.WALLHACK_LOS_BYPASS for a in anticheat.alerts)

    # Thermal vision bypasses opaque wall
    player.has_thermal_vision = True
    los3 = anticheat.validate_line_of_sight("XRayViewer", target_x=20, target_y=10)
    assert los3["has_los"] is True
    assert los3["vision_mode"] == "AUGMENTED_SENSORS"


def test_dreammaker_export_syntax(anticheat):
    dm = anticheat.export_dreammaker_code()
    assert "/datum/subsystem/anticheat" in dm
    assert "validate_client_movement" in dm
    assert "Sleepfeet exploit packet blocked" in dm
