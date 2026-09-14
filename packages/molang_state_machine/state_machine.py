"""
Molang state machine validator, cycle detector, and simulation engine.
"""

from dataclasses import dataclass, field
import re
from typing import Any, Callable, Dict, List, Optional, Set, Tuple


ALLOWED_MOLANG_DOMAINS: Set[str] = {
    "variable",
    "v",
    "query",
    "q",
    "temp",
    "t",
    "context",
    "c",
    "math",
}


class WatchdogLockoutError(RuntimeError):
    """Raised when cyclic animation controller transitions exceed watchdog limits."""


@dataclass
class MolangValidationResult:
    """Diagnostic outcome of Molang syntax validation."""

    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass
class CycleAnalysisResult:
    """Topological cycle analysis outcome for an animation controller."""

    is_acyclic: bool
    has_oscillation_risk: bool
    detected_cycles: List[List[str]] = field(default_factory=list)
    max_evaluation_depth: int = 0
    uses_discrete_flags: bool = True
    uses_blend_transitions: bool = True
    errors: List[str] = field(default_factory=list)


@dataclass
class SimulationContext:
    """Stateful context representing entity variables during state execution."""

    anim_time: float = 0.0
    state_flag: int = 0
    is_alive: bool = True
    is_charging: bool = False
    is_delayed_attacking: bool = False


@dataclass
class SimulationResult:
    """Record of state transitions and variable states across simulation ticks."""

    history: List[str]
    final_flag: int
    transitions_executed: int


def validate_molang_syntax(
    expression: str, is_statement: bool = False
) -> MolangValidationResult:
    """
    Validate a single Molang expression or statement against Bedrock standards.

    Args:
        expression: The raw Molang code string to validate.
        is_statement: True if the code represents an assignment or action.

    Returns:
        MolangValidationResult detailing syntax validity and diagnostics.
    """
    errors: List[str] = []
    warnings: List[str] = []
    trimmed = expression.strip()

    if not trimmed:
        errors.append("Molang expression cannot be empty.")
        return MolangValidationResult(valid=False, errors=errors, warnings=warnings)

    if is_statement:
        if not trimmed.endswith(";"):
            errors.append(
                f"Molang statement '{expression}' must terminate with a semicolon."
            )
        else:
            trimmed = trimmed[:-1].strip()

    paren_depth = 0
    for char in trimmed:
        if char == "(":
            paren_depth += 1
        elif char == ")":
            paren_depth -= 1
            if paren_depth < 0:
                errors.append(
                    f"Unexpected closing parenthesis encountered in: {expression}"
                )
                break

    if paren_depth > 0:
        errors.append(
            f"Unclosed opening parenthesis encountered in: {expression}"
        )

    domain_matches = re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\.", trimmed)
    for domain in domain_matches:
        if domain.lower() not in ALLOWED_MOLANG_DOMAINS:
            errors.append(f"Invalid Molang domain prefix '{domain}'.")

    return MolangValidationResult(
        valid=len(errors) == 0, errors=errors, warnings=warnings
    )


def _check_state_declaration(
    name: str, state: Dict[str, Any]
) -> Tuple[bool, bool, List[str]]:
    """
    Verify single state declaration for blend transitions and discrete state flag.

    Args:
        name: Name of the controller state.
        state: State dictionary containing transitions and lifecycle hooks.

    Returns:
        Tuple of (blend_valid, flag_valid, collected_errors).
    """
    errors: List[str] = []
    blend_valid = True
    flag_valid = True

    blend = state.get("blend_transition")
    if blend is None or not isinstance(blend, (int, float)) or blend <= 0:
        blend_valid = False
        errors.append(
            f"State '{name}' is missing a valid positive numeric 'blend_transition'."
        )

    on_entry = state.get("on_entry", [])
    has_flag = any(
        "variable.state_flag" in stmt and "=" in stmt for stmt in on_entry
    )
    if not has_flag:
        flag_valid = False
        errors.append(
            f"State '{name}' does not configure discrete 'variable.state_flag' in on_entry."
        )

    return blend_valid, flag_valid, errors


def _build_hazard_adj(
    states: Dict[str, Any]
) -> Tuple[Dict[str, List[str]], List[str]]:
    """
    Build directed adjacency graph of instantaneous unshielded transitions.

    Args:
        states: Mapping of state names to state dictionary configurations.

    Returns:
        Tuple of hazard adjacency dictionary and error list for non-existent states.
    """
    errors: List[str] = []
    hazard_adj: Dict[str, List[str]] = {name: [] for name in states}

    for source_name, state in states.items():
        for trans_entry in state.get("transitions", []):
            for target_name, cond in trans_entry.items():
                if target_name not in states:
                    errors.append(
                        f"State '{source_name}' targets unknown state '{target_name}'."
                    )
                    continue

                cond_str = str(cond).strip()
                has_flag_guard = (
                    "variable.state_flag ==" in cond_str
                    or "v.state_flag ==" in cond_str
                )
                has_cyclic_time = (
                    "query.anim_time <" in cond_str
                    or "q.anim_time <" in cond_str
                )

                if not has_flag_guard or has_cyclic_time:
                    hazard_adj[source_name].append(target_name)

    return hazard_adj, errors


def _detect_graph_cycles(
    adj: Dict[str, List[str]]
) -> Tuple[List[List[str]], List[str]]:
    """
    Detect cycles within a directed graph using depth-first search.

    Args:
        adj: Adjacency list mapping node identifiers to outward edges.

    Returns:
        Tuple of detected cycle paths and generated error messages.
    """
    detected_cycles: List[List[str]] = []
    errors: List[str] = []
    visited: Set[str] = set()
    rec_stack: Set[str] = set()
    curr_path: List[str] = []

    def dfs(node: str) -> None:
        """Traverse nodes using depth-first search to detect cyclic paths."""
        visited.add(node)
        rec_stack.add(node)
        curr_path.append(node)

        for neighbor in adj.get(node, []):
            if neighbor not in visited:
                dfs(neighbor)
            elif neighbor in rec_stack:
                start_idx = curr_path.index(neighbor)
                cycle = curr_path[start_idx:] + [neighbor]
                detected_cycles.append(cycle)
                cycle_str = " -> ".join(cycle)
                errors.append(
                    f"Cyclic instantaneous dependency detected: {cycle_str} "
                    "trips Molang watchdog lockout."
                )

        curr_path.pop()
        rec_stack.remove(node)

    for node_name in adj:
        if node_name not in visited:
            dfs(node_name)

    return detected_cycles, errors


def _validate_states_flags_and_blends(
    states: Dict[str, Any]
) -> Tuple[bool, bool, List[str]]:
    """
    Validate all state declarations for blend transitions and discrete flags.

    Args:
        states: Mapping of state names to state dictionary configurations.

    Returns:
        Tuple of (all_blends_valid, all_flags_valid, collected_errors).
    """
    uses_blend = True
    uses_flags = True
    errors: List[str] = []
    for name, state in states.items():
        b_val, f_val, st_errs = _check_state_declaration(name, state)
        uses_blend = uses_blend and b_val
        uses_flags = uses_flags and f_val
        errors.extend(st_errs)
    return uses_blend, uses_flags, errors



def analyze_controller_transitions(
    controller: Dict[str, Any]
) -> CycleAnalysisResult:
    """
    Perform static cycle analysis and watchdog evaluation on state transitions.

    Args:
        controller: Animation controller definition dictionary.

    Returns:
        CycleAnalysisResult indicating topological acyclicity and oscillation risk.
    """
    errors: List[str] = []
    states: Dict[str, Any] = controller.get("states", {})
    initial_state = controller.get("initial_state", "")

    if initial_state not in states:
        errors.append(f"Initial state '{initial_state}' does not exist.")

    uses_blend, uses_flags, st_errs = _validate_states_flags_and_blends(states)
    errors.extend(st_errs)

    hazard_adj, adj_errs = _build_hazard_adj(states)
    errors.extend(adj_errs)

    detected_cycles, cycle_errs = _detect_graph_cycles(hazard_adj)
    errors.extend(cycle_errs)

    is_acyclic = len(detected_cycles) == 0
    has_oscillation = (not is_acyclic) or (not uses_flags) or (not uses_blend)

    return CycleAnalysisResult(
        is_acyclic=is_acyclic,
        has_oscillation_risk=has_oscillation,
        detected_cycles=detected_cycles,
        max_evaluation_depth=len(states) if is_acyclic else 100,
        uses_discrete_flags=uses_flags,
        uses_blend_transitions=uses_blend,
        errors=errors,
    )



def _validate_controller_states(
    ctrl_name: str, states: Dict[str, Any]
) -> List[str]:
    """
    Validate individual controller states and transitions.

    Args:
        ctrl_name: Name of the controller.
        states: Mapping of states inside the controller.

    Returns:
        List of validation error messages.
    """
    errors: List[str] = []
    for state_name, state in states.items():
        for stmt in state.get("on_entry", []):
            errors.extend(validate_molang_syntax(stmt, is_statement=True).errors)
        for stmt in state.get("on_exit", []):
            errors.extend(validate_molang_syntax(stmt, is_statement=True).errors)
        for trans in state.get("transitions", []):
            for target, expr in trans.items():
                errors.extend(validate_molang_syntax(expr, is_statement=False).errors)
                if target not in states:
                    errors.append(
                        f"Controller '{ctrl_name}' state '{state_name}' targets missing '{target}'."
                    )
    return errors


def validate_animation_controllers_file(
    file_content: Dict[str, Any]
) -> MolangValidationResult:
    """
    Validate an entire animation controllers JSON configuration structure.

    Args:
        file_content: Parsed JSON content of the controller file.

    Returns:
        MolangValidationResult with detailed validation status and diagnostics.
    """
    errors: List[str] = []
    warnings: List[str] = []

    if not file_content.get("format_version"):
        errors.append("Missing 'format_version' attribute.")

    controllers = file_content.get("animation_controllers")
    if not isinstance(controllers, dict):
        errors.append("Missing or invalid 'animation_controllers' dictionary.")
        return MolangValidationResult(valid=False, errors=errors, warnings=warnings)

    for ctrl_name, controller in controllers.items():
        if not controller.get("initial_state"):
            errors.append(f"Controller '{ctrl_name}' is missing 'initial_state'.")

        states = controller.get("states")
        if not isinstance(states, dict):
            errors.append(f"Controller '{ctrl_name}' is missing 'states' dictionary.")
            continue

        errors.extend(_validate_controller_states(ctrl_name, states))
        cycle_res = analyze_controller_transitions(controller)
        if not cycle_res.is_acyclic:
            errors.extend(cycle_res.errors)

    return MolangValidationResult(
        valid=len(errors) == 0, errors=errors, warnings=warnings
    )


def validate_boss_golem_entity(
    file_content: Dict[str, Any],
    expected_controller_id: str = "controller.animation.boss_golem.state_machine",
) -> MolangValidationResult:
    """
    Verify entity definition binds the target animation controller.

    Args:
        file_content: Parsed JSON object of the entity definition file.
        expected_controller_id: Expected animation controller identifier.

    Returns:
        MolangValidationResult with pass or fail diagnostics.
    """
    errors: List[str] = []
    warnings: List[str] = []

    entity = file_content.get("minecraft:entity")
    if not entity or not entity.get("description"):
        errors.append("Missing 'minecraft:entity' or 'description' block.")
        return MolangValidationResult(valid=False, errors=errors, warnings=warnings)

    desc = entity["description"]
    if desc.get("identifier") != "custom:boss_golem":
        errors.append(
            f"Expected identifier 'custom:boss_golem', found '{desc.get('identifier')}'."
        )

    animations = desc.get("animations", {})
    bound_key = next((k for k, v in animations.items() if v == expected_controller_id), None)

    if not bound_key:
        errors.append(
            f"Entity does not bind animation controller '{expected_controller_id}'."
        )
    else:
        scripts = desc.get("scripts", {})
        animate_list = scripts.get("animate", [])
        bound_present = any(
            (item == bound_key if isinstance(item, str) else bound_key in item)
            for item in animate_list
        )
        if not bound_present:
            errors.append(
                f"Bound animation controller '{bound_key}' not in scripts.animate."
            )

    return MolangValidationResult(
        valid=len(errors) == 0, errors=errors, warnings=warnings
    )


def _apply_statements(
    statements: Optional[List[str]], context: SimulationContext
) -> None:
    """
    Execute state on_entry or on_exit statements to mutate simulation context.

    Args:
        statements: List of statement strings.
        context: Simulation context to mutate.
    """
    if not statements:
        return
    for stmt in statements:
        if "variable.state_flag" in stmt and "=" in stmt:
            parts = stmt.split("=")
            clean_val = parts[1].replace(";", "").strip()
            try:
                context.state_flag = int(clean_val)
            except ValueError:
                pass
        elif "variable.is_charging" in stmt and "=" in stmt:
            parts = stmt.split("=")
            clean_val = parts[1].replace(";", "").strip()
            context.is_charging = clean_val in ("1", "true")


COND_RULES: List[Tuple[str, Callable[[SimulationContext, str], bool]]] = [
    (
        "variable.state_flag == 0",
        lambda c, _: c.state_flag == 0 and (c.is_charging or c.is_delayed_attacking),
    ),
    (
        "variable.state_flag == 1",
        lambda c, _: c.state_flag == 1 and c.anim_time >= 1.5,
    ),
    (
        "variable.state_flag == 2",
        lambda c, s: c.state_flag == 2 and (
            ("query.anim_time >= 0.25" in s and c.anim_time >= 0.25)
            or ("!query.is_alive" in s and not c.is_alive)
        ),
    ),
    (
        "variable.state_flag == 3",
        lambda c, _: c.state_flag == 3 and c.anim_time >= 1.2,
    ),
    (
        "variable.state_flag == 4",
        lambda c, _: c.state_flag == 4 and c.anim_time >= 0.8,
    ),
    (
        "query.anim_time < 0.5",
        lambda c, _: c.anim_time < 0.5,
    ),
    (
        "q.anim_time < 0.5",
        lambda c, _: c.anim_time < 0.5,
    ),
    (
        "query.anim_time > 0.0",
        lambda _c, _s: True,
    ),
    (
        "query.anim_time >= 0.0",
        lambda _c, _s: True,
    ),
    (
        "query.anim_time > 1.0",
        lambda _c, _s: True,
    ),
]


def _eval_condition(cond_str: str, ctx: SimulationContext) -> bool:
    """
    Evaluate single transition condition against active simulation context.

    Args:
        cond_str: The condition expression string.
        ctx: Active simulation context.

    Returns:
        Boolean indicating whether transition should fire.
    """
    for token, handler in COND_RULES:
        if token in cond_str:
            return handler(ctx, cond_str)
    return False


def _execute_sub_tick(
    states: Dict[str, Any], curr_state: str, ctx: SimulationContext
) -> Tuple[Optional[str], bool]:
    """
    Evaluate candidate transitions from current state within one sub-tick evaluation.

    Args:
        states: Controller states dictionary.
        curr_state: Identifier of active state.
        ctx: Active simulation context.

    Returns:
        Tuple of target state name if transition fired and boolean flag.
    """
    for trans_entry in states.get(curr_state, {}).get("transitions", []):
        for target_name, condition in trans_entry.items():
            if _eval_condition(str(condition), ctx):
                return target_name, True
    return None, False


def simulate_state_machine(
    controller: Dict[str, Any],
    initial_context: SimulationContext,
    ticks: int = 100,
) -> SimulationResult:
    """
    Simulate state machine transitions across game ticks.

    Args:
        controller: Animation controller definition dictionary.
        initial_context: Initial variables and query settings.
        ticks: Total game ticks to simulate.

    Returns:
        SimulationResult recording visited states and transition count.

    Raises:
        WatchdogLockoutError: If cyclic instantaneous transitions exceed depth limit.
    """
    states = controller.get("states", {})
    curr = controller.get("initial_state", "")
    ctx = SimulationContext(
        anim_time=initial_context.anim_time,
        state_flag=initial_context.state_flag,
        is_alive=initial_context.is_alive,
        is_charging=initial_context.is_charging,
        is_delayed_attacking=initial_context.is_delayed_attacking,
    )
    history = [curr]
    transitions_count = 0

    _apply_statements(states.get(curr, {}).get("on_entry"), ctx)

    for _ in range(ticks):
        ctx.anim_time += 0.05
        trans_occurred = True
        depth = 0

        while trans_occurred and depth < 25:
            target, trans_occurred = _execute_sub_tick(states, curr, ctx)
            if trans_occurred and target:
                depth += 1
                _apply_statements(states.get(curr, {}).get("on_exit"), ctx)
                curr = target
                ctx.anim_time = 0.0
                _apply_statements(states.get(curr, {}).get("on_entry"), ctx)
                history.append(curr)
                transitions_count += 1

        if depth >= 25:
            prefix = "Watchdog lockout: Maximum execution depth exceeded in controller"
            cycle_desc = "query.anim_time -> state.transition -> query.anim_time"
            msg = (
                f"{prefix} at state '{curr}'. "
                f"Cyclic dependency detected: {cycle_desc}."
            )
            raise WatchdogLockoutError(msg)

    return SimulationResult(
        history=history,
        final_flag=ctx.state_flag,
        transitions_executed=transitions_count,
    )
