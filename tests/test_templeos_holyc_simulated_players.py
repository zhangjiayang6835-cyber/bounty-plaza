"""Unit tests for TempleOS HolyC Simulated Player Bot Engine.
Resolves Issue #660: [BOUNTY] [AGENTIC AI] [$500] Simulate players to save my dying server.
"""

import pytest
from scripts.templeos_holyc_simulated_players import (
    TempleOSSimulatedPlayerEngine,
    SimulatedBotProfile,
    BotConnectionState,
    DYING_COMPLAINTS,
)


@pytest.fixture
def engine():
    return TempleOSSimulatedPlayerEngine(host="127.0.0.1", port=1337, rng_seed=42)


def test_spawn_bot_connection_and_job(engine):
    """Verifies simulated bot connection, initial state, and job assignment."""
    bot = engine.spawn_bot(ckey="HolyC_Bot_Terry", preferred_job="Clown")
    assert bot.ckey == "HolyC_Bot_Terry"
    assert bot.job == "Clown"
    assert bot.state == BotConnectionState.PLAYING
    assert bot.is_alive is True
    assert bot.health == 100.0
    assert any("Connected to" in log for log in bot.chat_log)


def test_plan_and_execute_rule_violation(engine):
    """Verifies that the bot reads server rules and executes deliberate violations."""
    engine.spawn_bot(ckey="GrieferBot", preferred_job="Janitor")
    violation = engine.plan_rule_violation("GrieferBot")

    assert "Deliberately violating rule" in violation
    bot = engine.bots["GrieferBot"]
    assert len(bot.active_violations) == 1
    assert any("Rulebreak executed" in log for log in bot.chat_log)


def test_death_complaint_and_instant_rage_quit(engine):
    """Verifies character death triggers dying complaints and immediately disconnects via rage quit."""
    engine.spawn_bot(ckey="RageQuitBot", preferred_job="Assistant")
    complaint, final_state = engine.trigger_death_and_rage_quit("RageQuitBot", cause="singularity ingestion")

    assert complaint in DYING_COMPLAINTS
    assert final_state == BotConnectionState.DISCONNECTED
    bot = engine.bots["RageQuitBot"]
    assert bot.is_alive is False
    assert bot.health == 0.0
    assert any("RageQuit protocol" in log for log in bot.chat_log)


def test_holyc_source_code_generation(engine):
    """Verifies TempleOS HolyC source code contains proper class defs, ring-0 syntax, and rage quit procs."""
    code = engine.generate_holyc_source_code()
    assert "class CBotPlayer" in code
    assert "BotConnect(CBotPlayer *bot)" in code
    assert "BotBreakRules(CBotPlayer *bot)" in code
    assert "BotRageQuit(CBotPlayer *bot)" in code
    assert "U0 Main()" in code
    assert "TempleOS HolyC" in code
