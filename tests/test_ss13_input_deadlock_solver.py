"""Unit tests for SS13 SSinput Subsystem Deadlock Mitigation & Non-Blocking Queue.
Resolves Issue #633: [BOUNTY] [$50] Fix SSinput Deadlocking.
Upstream Reference: Iamgoofball/-tg-station#123.
"""

import pytest
from scripts.ss13_input_deadlock_solver import (
    SS13InputSubsystem,
    InputType,
    InputEvent,
    ClientInputBuffer,
)


@pytest.fixture
def input_subsystem():
    # Watchdog timeout of 50ms
    return SS13InputSubsystem(watchdog_timeout_ms=50.0)


def test_enqueue_and_process_input_events_cleanly(input_subsystem):
    input_subsystem.register_client("CrewMemberDave")

    # Enqueue 3 valid key events
    ok1 = input_subsystem.enqueue_event("CrewMemberDave", InputType.KEY_DOWN, "W", timestamp_ms=10.0)
    ok2 = input_subsystem.enqueue_event("CrewMemberDave", InputType.KEY_DOWN, "D", timestamp_ms=15.0)
    ok3 = input_subsystem.enqueue_event("CrewMemberDave", InputType.KEY_UP, "W", timestamp_ms=25.0)

    assert ok1 and ok2 and ok3
    buf = input_subsystem.client_buffers["CrewMemberDave"]
    assert len(buf.queue) == 3

    # Fire subsystem tick
    res = input_subsystem.fire(current_time_ms=30.0)
    assert res["status"] == "OK"
    assert res["processed_events"] == 3
    assert res["recovered_deadlocks"] == 0
    assert len(buf.queue) == 0
    assert buf.total_processed_count == 3


def test_buffer_overflow_protection_drops_excess_macro_spam(input_subsystem):
    input_subsystem.register_client("SpammerBot")
    buf = input_subsystem.client_buffers["SpammerBot"]

    # Enqueue up to capacity (64)
    for i in range(64):
        success = input_subsystem.enqueue_event("SpammerBot", InputType.KEY_DOWN, "E", timestamp_ms=100.0 + i)
        assert success is True

    # 65th event must be rejected
    rejected = input_subsystem.enqueue_event("SpammerBot", InputType.KEY_DOWN, "E", timestamp_ms=200.0)
    assert rejected is False
    assert buf.dropped_events_count == 1
    assert len(buf.queue) == 64


def test_watchdog_detects_and_recovers_stuck_deadlock(input_subsystem):
    buf = input_subsystem.register_client("FrozenClient")
    input_subsystem.enqueue_event("FrozenClient", InputType.CLICK, "Button1", timestamp_ms=100.0)

    # Artificially simulate a deadlocked proc holding the lock at time 100ms
    buf.is_processing = True
    buf.lock_acquired_time_ms = 100.0

    # Tick at 120ms (within 50ms timeout): no watchdog trigger yet
    res1 = input_subsystem.fire(current_time_ms=120.0)
    assert res1["recovered_deadlocks"] == 0
    assert buf.is_processing is True

    # Tick at 160ms (60ms elapsed > 50ms timeout): watchdog forcefully frees lock!
    res2 = input_subsystem.fire(current_time_ms=160.0)
    assert res2["recovered_deadlocks"] == 1
    assert len(input_subsystem.deadlock_incidents) == 1
    assert input_subsystem.deadlock_incidents[0]["ckey"] == "FrozenClient"
    # Lock is freed and deadlocked packet popped
    assert buf.is_processing is False
    assert len(buf.queue) == 0


def test_reentrancy_protection_skips_recursive_fire(input_subsystem):
    input_subsystem.is_firing = True
    res = input_subsystem.fire(current_time_ms=100.0)
    assert res["status"] == "REENTRANCY_SKIPPED"
    assert res["processed_events"] == 0


def test_client_disconnect_cleans_up_orphaned_locks(input_subsystem):
    input_subsystem.register_client("DisconnectingPlayer")
    input_subsystem.enqueue_event("DisconnectingPlayer", InputType.KEY_DOWN, "Space", timestamp_ms=10.0)
    assert "DisconnectingPlayer" in input_subsystem.client_buffers

    input_subsystem.unregister_client("DisconnectingPlayer")
    assert "DisconnectingPlayer" not in input_subsystem.client_buffers

    # Firing does not error on missing client
    res = input_subsystem.fire(current_time_ms=20.0)
    assert res["status"] == "OK"


def test_dreammaker_export_contains_deadlock_watchdog(input_subsystem):
    dm = input_subsystem.export_dreammaker_code()
    assert "/datum/subsystem/input" in dm
    assert "watchdog_timeout_ds" in dm
    assert "SSinput watchdog released stuck lock" in dm
    assert "enqueue_key_event" in dm
