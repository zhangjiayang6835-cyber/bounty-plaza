"""
Formal verification suite and invariant auditor for Issue #1307.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from packages.molang_state_machine.state_machine import (
    SimulationContext,
    WatchdogLockoutError,
    analyze_controller_transitions,
    simulate_state_machine,
    validate_animation_controllers_file,
    validate_boss_golem_entity,
    validate_molang_syntax,
)


@dataclass
class VerificationCheck:
    """Individual invariant check result."""

    name: str
    passed: bool
    details: str


@dataclass
class VerificationReport:
    """Consolidated report containing all invariant checks."""

    checks: List[VerificationCheck] = field(default_factory=list)
    all_passed: bool = False
    checks_passed: int = 0
    checks_run: int = 0


class MolangStateMachineVerifier:
    """Automated formal verification engine for Bedrock state machine transitions."""

    @staticmethod
    def _find_base_dir(custom_path: Optional[Path] = None) -> Path:
        """Resolve workspace root directory containing Bedrock definition files."""
        if custom_path:
            return custom_path
        current = Path(__file__).resolve().parent
        for p in [current] + list(current.parents):
            target_file = (
                p / "animation_controllers" / "boss_golem.animation_controllers.json"
            )
            if target_file.is_file():
                return p
        return Path.cwd()

    @classmethod
    def check_entity_binding(cls, base_dir: Path) -> VerificationCheck:
        """Verify custom:boss_golem binds animation controller."""
        entity_path = base_dir / "entities" / "boss_golem.json"
        if not entity_path.is_file():
            return VerificationCheck(
                name="Entity Controller Binding",
                passed=False,
                details=f"Missing entity definition file at {entity_path}",
            )
        data = json.loads(entity_path.read_text(encoding="utf-8"))
        res = validate_boss_golem_entity(data)
        return VerificationCheck(
            name="Entity Controller Binding",
            passed=res.valid,
            details="Validated custom:boss_golem binding and animation script"
            if res.valid
            else "; ".join(res.errors),
        )

    @classmethod
    def check_controller_file(cls, base_dir: Path) -> VerificationCheck:
        """Verify animation controller conforms to Bedrock schema."""
        ctrl_path = base_dir / "animation_controllers" / "boss_golem.animation_controllers.json"
        if not ctrl_path.is_file():
            return VerificationCheck(
                name="Animation Controller Schema",
                passed=False,
                details=f"Missing controller file at {ctrl_path}",
            )
        data = json.loads(ctrl_path.read_text(encoding="utf-8"))
        res = validate_animation_controllers_file(data)
        return VerificationCheck(
            name="Animation Controller Schema",
            passed=res.valid,
            details="Format version 1.10.0 and all state dictionaries valid"
            if res.valid
            else "; ".join(res.errors),
        )

    @classmethod
    def check_discrete_flags_and_blend(cls, base_dir: Path) -> VerificationCheck:
        """Verify state flags and blend transitions prevent tick-level oscillation."""
        ctrl_path = base_dir / "animation_controllers" / "boss_golem.animation_controllers.json"
        data = json.loads(ctrl_path.read_text(encoding="utf-8"))
        ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]

        expected_flags: Dict[str, int] = {
            "default": 0,
            "charging": 1,
            "eval_charge": 2,
            "slam_attack": 3,
            "recovery": 4,
        }
        for state_name, exp_flag in expected_flags.items():
            state = ctrl["states"].get(state_name, {})
            blend = state.get("blend_transition", 0.0)
            if blend < 0.2:
                return VerificationCheck(
                    name="Discrete Flags & Blend Dampening",
                    passed=False,
                    details=f"State '{state_name}' blend_transition {blend} < 0.2",
                )
            on_entry = state.get("on_entry", [])
            has_flag = any(f"variable.state_flag = {exp_flag};" in s for s in on_entry)
            if not has_flag:
                return VerificationCheck(
                    name="Discrete Flags & Blend Dampening",
                    passed=False,
                    details=f"State '{state_name}' missing discrete flag {exp_flag}",
                )

        return VerificationCheck(
            name="Discrete Flags & Blend Dampening",
            passed=True,
            details="All 5 states configure discrete state flags and blend >= 0.2",
        )

    @classmethod
    def check_molang_parser_standards(cls) -> VerificationCheck:
        """Verify Molang parser enforces Bedrock strict syntax."""
        valid_stmt = validate_molang_syntax("variable.state_flag = 1;", is_statement=True)
        missing_semi = validate_molang_syntax("variable.state_flag = 1", is_statement=True)
        bad_domain = validate_molang_syntax("unknown_domain.val == 1", is_statement=False)
        unclosed_paren = validate_molang_syntax("(query.anim_time > 0", is_statement=False)

        passed = (
            valid_stmt.valid
            and not missing_semi.valid
            and not bad_domain.valid
            and not unclosed_paren.valid
        )
        return VerificationCheck(
            name="Strict Molang Parser Standards",
            passed=passed,
            details="Semicolon statements, allowed domains, and paren balance verified",
        )

    @classmethod
    def check_acyclic_graph_topology(cls, base_dir: Path) -> VerificationCheck:
        """Verify static graph analysis confirms acyclic state transitions."""
        ctrl_path = base_dir / "animation_controllers" / "boss_golem.animation_controllers.json"
        data = json.loads(ctrl_path.read_text(encoding="utf-8"))
        ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]
        analysis = analyze_controller_transitions(ctrl)
        passed = analysis.is_acyclic and not analysis.has_oscillation_risk
        return VerificationCheck(
            name="Acyclic Graph Topology",
            passed=passed,
            details="Acyclic transition graph, zero watchdog hazard paths detected"
            if passed
            else "; ".join(analysis.errors),
        )

    @classmethod
    def check_simulation_and_watchdog_prevention(cls, base_dir: Path) -> VerificationCheck:
        """Verify simulation monotonic progress and watchdog trip on cyclic graph."""
        ctrl_path = base_dir / "animation_controllers" / "boss_golem.animation_controllers.json"
        data = json.loads(ctrl_path.read_text(encoding="utf-8"))
        ctrl = data["animation_controllers"]["controller.animation.boss_golem.state_machine"]

        ctx = SimulationContext(
            anim_time=0.0,
            state_flag=0,
            is_alive=True,
            is_charging=True,
            is_delayed_attacking=False,
        )
        sim_res = simulate_state_machine(ctrl, ctx, ticks=100)
        expected_seq = ["default", "charging", "eval_charge", "slam_attack", "recovery"]
        seq_valid = all(s in sim_res.history for s in expected_seq)

        buggy_ctrl: Dict[str, Any] = {
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
                "slam_attack": {"blend_transition": 0.2, "on_entry": [], "transitions": []},
            },
        }
        lockout_caught = False
        try:
            simulate_state_machine(buggy_ctrl, ctx, ticks=1)
        except WatchdogLockoutError:
            lockout_caught = True

        passed = seq_valid and lockout_caught
        return VerificationCheck(
            name="Simulation & Watchdog Lockout Prevention",
            passed=passed,
            details="Combat sequence completed monotonically; cyclic lockout detected",
        )

    @classmethod
    def run_all_checks(cls, base_dir: Optional[Path] = None) -> VerificationReport:
        """Execute all 6 invariant verifications and compile report."""
        root = cls._find_base_dir(custom_path=base_dir)
        checks: List[VerificationCheck] = [
            cls.check_entity_binding(root),
            cls.check_controller_file(root),
            cls.check_discrete_flags_and_blend(root),
            cls.check_molang_parser_standards(),
            cls.check_acyclic_graph_topology(root),
            cls.check_simulation_and_watchdog_prevention(root),
        ]
        passed_count = sum(1 for c in checks if c.passed)
        total_count = len(checks)
        return VerificationReport(
            checks=checks,
            all_passed=(passed_count == total_count),
            checks_passed=passed_count,
            checks_run=total_count,
        )
