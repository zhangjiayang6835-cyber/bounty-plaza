"""
Comprehensive pytest test suite for Issue #1307 Molang state machine fix.
"""

import json
from pathlib import Path
import pytest

from packages.molang_state_machine.state_machine import (
    SimulationContext,
    WatchdogLockoutError,
    analyze_controller_transitions,
    simulate_state_machine,
    validate_animation_controllers_file,
    validate_boss_golem_entity,
    validate_molang_syntax,
)
from packages.molang_state_machine.verifier import MolangStateMachineVerifier


WORKSPACE_ROOT = Path(__file__).resolve().parent.parent


def test_entity_binding_schema() -> None:
    """Verify entities/boss_golem.json binds controller and animation scripts."""
    entity_path = WORKSPACE_ROOT / "entities" / "boss_golem.json"
    assert entity_path.is_file(), f"Missing entity file at {entity_path}"

    data = json.loads(entity_path.read_text(encoding="utf-8"))
    assert data.get("format_version") == "1.21.50"

    desc = data.get("minecraft:entity", {}).get("description", {})
    assert desc.get("identifier") == "custom:boss_golem"

    anims = desc.get("animations", {})
    assert anims.get("state_machine") == "controller.animation.boss_golem.state_machine"

    script_animate = desc.get("scripts", {}).get("animate", [])
    assert "state_machine" in script_animate

    res = validate_boss_golem_entity(data)
    assert res.valid is True
    assert len(res.errors) == 0


def test_controller_conforms_to_bedrock_schema() -> None:
    """Verify animation controller file structure and state declarations."""
    ctrl_path = (
        WORKSPACE_ROOT
        / "animation_controllers"
        / "boss_golem.animation_controllers.json"
    )
    assert ctrl_path.is_file(), f"Missing controller file at {ctrl_path}"

    data = json.loads(ctrl_path.read_text(encoding="utf-8"))
    assert data.get("format_version") == "1.10.0"

    controllers = data.get("animation_controllers", {})
    assert "controller.animation.boss_golem.state_machine" in controllers

    target_ctrl = controllers["controller.animation.boss_golem.state_machine"]
    assert target_ctrl.get("initial_state") == "default"

    required_states = ["default", "charging", "eval_charge", "slam_attack", "recovery"]
    for s in required_states:
        assert s in target_ctrl.get("states", {}), f"State '{s}' must be defined"

    res = validate_animation_controllers_file(data)
    assert res.valid is True
    assert len(res.errors) == 0


def test_discrete_state_flags_and_blend_transitions() -> None:
    """Verify discrete state flags and blend transitions prevent oscillation."""
    ctrl_path = (
        WORKSPACE_ROOT
        / "animation_controllers"
        / "boss_golem.animation_controllers.json"
    )
    data = json.loads(ctrl_path.read_text(encoding="utf-8"))
    ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]

    expected_flags = {
        "default": 0,
        "charging": 1,
        "eval_charge": 2,
        "slam_attack": 3,
        "recovery": 4,
    }
    for state_name, expected_flag in expected_flags.items():
        state_obj = ctrl["states"][state_name]
        assert isinstance(state_obj.get("blend_transition"), (int, float))
        assert state_obj.get("blend_transition") >= 0.2

        on_entry = state_obj.get("on_entry", [])
        has_flag = any(f"variable.state_flag = {expected_flag};" in s for s in on_entry)
        assert has_flag, f"State '{state_name}' must set variable.state_flag = {expected_flag};"

    eval_trans = ctrl["states"]["eval_charge"].get("transitions", [])
    has_cyclic_charging = any("charging" in t for t in eval_trans)
    assert not has_cyclic_charging, "eval_charge must not contain transition to charging"


def test_strict_molang_parser_standards() -> None:
    """Verify Molang parser rejects unclosed parentheses and invalid domains."""
    valid_stmt = validate_molang_syntax("variable.state_flag = 1;", is_statement=True)
    assert valid_stmt.valid is True

    missing_semi = validate_molang_syntax("variable.state_flag = 1", is_statement=True)
    assert missing_semi.valid is False
    assert any("must terminate with a semicolon" in e for e in missing_semi.errors)

    bad_domain = validate_molang_syntax("invalid_domain.val == 1", is_statement=False)
    assert bad_domain.valid is False
    assert any("Invalid Molang domain prefix" in e for e in bad_domain.errors)

    unbalanced = validate_molang_syntax("(query.anim_time > 1.0 && (variable.state_flag == 1)")
    assert unbalanced.valid is False
    assert any("Unclosed opening parenthesis" in e for e in unbalanced.errors)


def test_static_graph_analysis_confirms_acyclic() -> None:
    """Verify static analysis reports refactored controller as acyclic and safe."""
    ctrl_path = (
        WORKSPACE_ROOT
        / "animation_controllers"
        / "boss_golem.animation_controllers.json"
    )
    data = json.loads(ctrl_path.read_text(encoding="utf-8"))
    ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]

    analysis = analyze_controller_transitions(ctrl)
    assert analysis.is_acyclic is True
    assert analysis.has_oscillation_risk is False
    assert len(analysis.detected_cycles) == 0
    assert analysis.uses_discrete_flags is True
    assert analysis.uses_blend_transitions is True
    assert len(analysis.errors) == 0


def test_reproduces_and_detects_cyclic_watchdog_lockout() -> None:
    """Verify cycle detector catches cyclic anim_time dependency and simulator halts."""
    buggy_controller = {
        "initial_state": "charging",
        "states": {
            "charging": {
                "blend_transition": 0.2,
                "on_entry": ["variable.state_flag = 1;"],
                "transitions": [{"eval_charge": "query.anim_time > 1.0"}],
            },
            "eval_charge": {
                "blend_transition": 0.2,
                "on_entry": ["variable.state_flag = 2;"],
                "transitions": [
                    {"charging": "query.anim_time < 0.5"},
                    {"slam_attack": "query.anim_time >= 0.5"},
                ],
            },
            "slam_attack": {
                "blend_transition": 0.2,
                "on_entry": ["variable.state_flag = 3;"],
                "transitions": [],
            },
        },
    }

    analysis = analyze_controller_transitions(buggy_controller)
    assert analysis.is_acyclic is False
    assert analysis.has_oscillation_risk is True
    assert len(analysis.detected_cycles) > 0
    assert any("trips Molang watchdog lockout" in err for err in analysis.errors)

    ctx = SimulationContext(
        anim_time=0.0,
        state_flag=1,
        is_alive=True,
        is_charging=True,
        is_delayed_attacking=False,
    )
    with pytest.raises(WatchdogLockoutError, match="Maximum execution depth exceeded"):
        simulate_state_machine(buggy_controller, ctx, ticks=1)


def test_state_machine_simulation_monotonic_combat_sequence() -> None:
    """Verify discrete state machine simulator advances through combat states."""
    ctrl_path = (
        WORKSPACE_ROOT
        / "animation_controllers"
        / "boss_golem.animation_controllers.json"
    )
    data = json.loads(ctrl_path.read_text(encoding="utf-8"))
    ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]

    ctx = SimulationContext(
        anim_time=0.0,
        state_flag=0,
        is_alive=True,
        is_charging=True,
        is_delayed_attacking=False,
    )
    sim = simulate_state_machine(ctrl, ctx, ticks=100)
    assert "default" in sim.history
    assert "charging" in sim.history
    assert "eval_charge" in sim.history
    assert "slam_attack" in sim.history
    assert "recovery" in sim.history
    assert sim.final_flag == 0
    assert sim.transitions_executed == 5


def test_animations_json_defines_required_clips() -> None:
    """Verify animations/boss_golem.animation.json declares necessary animation clips."""
    anim_path = WORKSPACE_ROOT / "animations" / "boss_golem.animation.json"
    assert anim_path.is_file(), f"Missing animation file at {anim_path}"

    data = json.loads(anim_path.read_text(encoding="utf-8"))
    assert data.get("format_version") == "1.8.0"

    anims = data.get("animations", {})
    assert "animation.boss_golem.idle" in anims
    assert "animation.boss_golem.charge" in anims
    assert "animation.boss_golem.slam_attack" in anims
    assert "animation.boss_golem.recovery" in anims


def test_scripts_lifecycle_safety() -> None:
    """Verify TypeScript and compiled JS comply with Bedrock lifecycle rules."""
    ts_path = WORKSPACE_ROOT / "scripts" / "main.ts"
    js_path = WORKSPACE_ROOT / "scripts" / "main.js"
    assert ts_path.is_file(), f"Missing TypeScript entry at {ts_path}"
    assert js_path.is_file(), f"Missing compiled JS entry at {js_path}"

    ts_content = ts_path.read_text(encoding="utf-8")
    js_content = js_path.read_text(encoding="utf-8")

    assert "@minecraft/server" in ts_content
    assert "@minecraft/server" in js_content
    assert "world.sendMessage(" not in ts_content
    assert "system.runInterval" in ts_content


def test_verifier_all_checks() -> None:
    """Verify MolangStateMachineVerifier reports all 6 invariants passing."""
    report = MolangStateMachineVerifier.run_all_checks(WORKSPACE_ROOT)
    assert report.all_passed is True
    assert report.checks_passed == 6
    assert report.checks_run == 6
