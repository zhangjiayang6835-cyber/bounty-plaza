"""Unit tests for Game Playability Bootstrap & Lobby Initialization Recovery.
Resolves Issue #644: [BOUNTY] [$1,000] Bug preventing the expected behavior of the game being played.
Upstream Reference: Iamgoofball/-tg-station#149.
"""

import pytest
from scripts.game_playability_bootstrap_fix import (
    GamePlayabilityBootstrapEngine,
    BlockerType,
    DiagnosticResult,
)


@pytest.fixture
def engine():
    return GamePlayabilityBootstrapEngine()


def test_clean_environment_diagnostic(engine):
    clean_env = {
        "tgui_bundle_present": True,
        "tgui_asset_error": False,
        "subsystems_frozen": False,
        "controller_initialized": True,
        "client_mob_type": "/mob/dead/new_player",
        "rsc_cache_corrupted": False,
    }
    diag = engine.scan_and_diagnose(clean_env)
    assert diag.is_playable is True
    assert len(diag.detected_blockers) == 0
    assert diag.client_ready_for_join is True


def test_unplayable_environment_diagnostics(engine):
    broken_env = {
        "tgui_bundle_present": False,
        "tgui_asset_error": True,
        "subsystems_frozen": True,
        "controller_initialized": False,
        "client_mob_type": None,
        "rsc_cache_corrupted": True,
    }
    diag = engine.scan_and_diagnose(broken_env)
    assert diag.is_playable is False
    assert len(diag.detected_blockers) == 4
    assert BlockerType.TGUI_BUNDLE_FAILURE in diag.detected_blockers
    assert BlockerType.CONTROLLER_INIT_TIMEOUT in diag.detected_blockers
    assert BlockerType.CLIENT_MOB_LINK_CORRUPTION in diag.detected_blockers
    assert BlockerType.RSC_ASSET_CACHE_DESYNC in diag.detected_blockers
    assert len(diag.errors_preventing_play) == 4


def test_self_healing_recovery_execution(engine):
    broken_env = {
        "tgui_bundle_present": False,
        "tgui_asset_error": True,
        "subsystems_frozen": True,
        "controller_initialized": False,
        "client_mob_type": None,
        "rsc_cache_corrupted": True,
    }
    diag = engine.scan_and_diagnose(broken_env)
    healed = engine.execute_self_healing_recovery(diag)

    assert healed.is_playable is True
    assert len(healed.detected_blockers) == 0
    assert len(healed.recovery_actions_applied) == 4
    assert engine.tgui_fallback_active is True
    assert "SScontroller" in engine.subsystems_recovered
    assert len(engine.recovery_log) == 4


def test_player_join_flow_simulation(engine):
    # Simulate joining after recovery
    engine.tgui_fallback_active = True
    join_state = engine.simulate_player_join_flow("FriendlyGamer123")

    assert join_state["player_ckey"] == "FriendlyGamer123"
    assert join_state["connected"] is True
    assert join_state["lobby_screen_visible"] is True
    assert join_state["ready_status"] == "READY_FOR_ROUND"
    assert join_state["assigned_job"] == "Assistant"
    assert join_state["can_move"] is True
    assert join_state["can_interact"] is True
    assert join_state["status"] == "PLAYER_SUCCESSFULLY_IN_GAME"


def test_dreammaker_export_syntax(engine):
    dm_code = engine.export_dreammaker_code()
    assert "/client/proc/handle_playability_recovery()" in dm_code
    assert "/mob/dead/new_player" in dm_code
    assert "new_player_panel()" in dm_code
