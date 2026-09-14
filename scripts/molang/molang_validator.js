const VALID_DOMAINS = new Set([
    "variable",
    "v",
    "query",
    "q",
    "temp",
    "t",
    "context",
    "c",
    "math"
]);
const VALID_QUERIES = new Set([
    "anim_time",
    "life_time",
    "is_alive",
    "is_delayed_attacking",
    "is_moving",
    "has_target",
    "distance_from_camera",
    "all_animations_finished",
    "any_animation_finished"
]);
/**
 * Validates Molang expression syntax against Bedrock strict parsing standards.
 *
 * @param expression Raw Molang string.
 * @param isStatement Whether the string is expected to be a statement with side-effects.
 * @returns Result object containing validity status and diagnostic error messages.
 */
export function validateMolangSyntax(expression, isStatement = false) {
    const errors = [];
    const warnings = [];
    const trimmed = expression.trim();
    if (trimmed.length === 0) {
        errors.push("Empty Molang expression encountered.");
        return { valid: false, errors, warnings };
    }
    if (isStatement) {
        if (!trimmed.endsWith(";")) {
            errors.push(`Strict Molang violation: Statement '${trimmed}' must terminate with a semicolon ';'.`);
        }
    }
    const parenStack = [];
    for (let i = 0; i < trimmed.length; i++) {
        const char = trimmed[i];
        if (char === "(") {
            parenStack.push("(");
        }
        else if (char === ")") {
            if (parenStack.length === 0) {
                errors.push(`Unbalanced closing parenthesis in expression: '${trimmed}'`);
                break;
            }
            parenStack.pop();
        }
    }
    if (parenStack.length > 0) {
        errors.push(`Unclosed opening parenthesis in expression: '${trimmed}'`);
    }
    const identifierRegex = /([a-zA-Z_][a-zA-Z0-9_]*)\.([a-zA-Z0-9_]+)/g;
    let match;
    while ((match = identifierRegex.exec(trimmed)) !== null) {
        const domain = match[1].toLowerCase();
        const identifier = match[2].toLowerCase();
        if (!VALID_DOMAINS.has(domain)) {
            errors.push(`Invalid Molang domain prefix '${match[1]}' in token '${match[0]}'.`);
        }
        if ((domain === "query" || domain === "q") && !VALID_QUERIES.has(identifier)) {
            warnings.push(`Unverified query token '${match[0]}'.`);
        }
    }
    return {
        valid: errors.length === 0,
        errors,
        warnings
    };
}
/**
 * Performs static cycle analysis and watchdog evaluation on state machine transitions.
 *
 * @param definition Animation controller definition object.
 * @returns CycleAnalysisResult containing graph topology and oscillation hazard flags.
 */
export function analyzeControllerTransitions(definition) {
    const errors = [];
    const detectedCycles = [];
    let usesDiscreteFlags = true;
    let usesBlendTransitions = true;
    const states = definition.states;
    const stateNames = Object.keys(states);
    if (!states[definition.initial_state]) {
        errors.push(`Initial state '${definition.initial_state}' does not exist.`);
    }
    for (const [name, state] of Object.entries(states)) {
        if (state.blend_transition === undefined || typeof state.blend_transition !== "number" || state.blend_transition <= 0) {
            usesBlendTransitions = false;
            errors.push(`State '${name}' is missing a valid positive numeric 'blend_transition'.`);
        }
        const onEntry = state.on_entry ?? [];
        const hasFlagAssignment = onEntry.some((stmt) => stmt.includes("variable.state_flag") && stmt.includes("="));
        if (!hasFlagAssignment) {
            usesDiscreteFlags = false;
            errors.push(`State '${name}' does not configure discrete 'variable.state_flag' in on_entry.`);
        }
    }
    const hazardAdj = new Map();
    for (const name of stateNames) {
        hazardAdj.set(name, []);
    }
    for (const [sourceState, state] of Object.entries(states)) {
        const transitions = state.transitions ?? [];
        for (const transitionObj of transitions) {
            for (const [targetState, condition] of Object.entries(transitionObj)) {
                if (!states[targetState]) {
                    errors.push(`State '${sourceState}' transitions to non-existent state '${targetState}'.`);
                    continue;
                }
                const conditionTrimmed = condition.trim();
                const hasDiscreteFlagGuard = conditionTrimmed.includes("variable.state_flag ==") ||
                    conditionTrimmed.includes("v.state_flag ==");
                const hasCyclicImmediateAnimTime = conditionTrimmed.includes("query.anim_time <") ||
                    conditionTrimmed.includes("q.anim_time <");
                if (!hasDiscreteFlagGuard || hasCyclicImmediateAnimTime) {
                    hazardAdj.get(sourceState).push(targetState);
                }
            }
        }
    }
    const visited = new Set();
    const recursionStack = new Set();
    const currentPath = [];
    function dfs(u) {
        visited.add(u);
        recursionStack.add(u);
        currentPath.push(u);
        const neighbors = hazardAdj.get(u) ?? [];
        for (const v of neighbors) {
            if (!visited.has(v)) {
                dfs(v);
            }
            else if (recursionStack.has(v)) {
                const cycleStartIndex = currentPath.indexOf(v);
                const cycle = currentPath.slice(cycleStartIndex).concat(v);
                detectedCycles.push(cycle);
                errors.push(`Cyclic instantaneous dependency detected: ${cycle.join(" -> ")} trips Molang watchdog lockout.`);
            }
        }
        currentPath.pop();
        recursionStack.delete(u);
    }
    for (const name of stateNames) {
        if (!visited.has(name)) {
            dfs(name);
        }
    }
    const isAcyclic = detectedCycles.length === 0;
    const hasOscillationRisk = !isAcyclic || !usesDiscreteFlags || !usesBlendTransitions;
    return {
        isAcyclic,
        hasOscillationRisk,
        detectedCycles,
        maxEvaluationDepth: isAcyclic ? stateNames.length : 100,
        usesDiscreteFlags,
        usesBlendTransitions,
        errors
    };
}
/**
 * Validates an entire animation controllers JSON configuration file.
 *
 * @param file Root JSON object of the animation controllers file.
 * @returns Result object containing validation outcomes and collected diagnostics.
 */
export function validateAnimationControllersFile(file) {
    const errors = [];
    const warnings = [];
    if (!file.format_version) {
        errors.push("Missing 'format_version' attribute.");
    }
    if (!file.animation_controllers || typeof file.animation_controllers !== "object") {
        errors.push("Missing or invalid 'animation_controllers' dictionary.");
        return { valid: false, errors, warnings };
    }
    for (const [controllerName, controller] of Object.entries(file.animation_controllers)) {
        if (!controller.initial_state) {
            errors.push(`Controller '${controllerName}' is missing 'initial_state'.`);
        }
        if (!controller.states || typeof controller.states !== "object") {
            errors.push(`Controller '${controllerName}' is missing 'states' dictionary.`);
            continue;
        }
        for (const [stateName, state] of Object.entries(controller.states)) {
            const onEntry = state.on_entry ?? [];
            for (const stmt of onEntry) {
                const res = validateMolangSyntax(stmt, true);
                errors.push(...res.errors);
                warnings.push(...res.warnings);
            }
            const onExit = state.on_exit ?? [];
            for (const stmt of onExit) {
                const res = validateMolangSyntax(stmt, true);
                errors.push(...res.errors);
                warnings.push(...res.warnings);
            }
            const transitions = state.transitions ?? [];
            for (const t of transitions) {
                for (const [target, expr] of Object.entries(t)) {
                    const res = validateMolangSyntax(expr, false);
                    errors.push(...res.errors);
                    warnings.push(...res.warnings);
                    if (!controller.states[target]) {
                        errors.push(`Controller '${controllerName}' state '${stateName}' targets non-existent state '${target}'.`);
                    }
                }
            }
        }
        const cycleRes = analyzeControllerTransitions(controller);
        if (!cycleRes.isAcyclic) {
            errors.push(...cycleRes.errors);
        }
    }
    return {
        valid: errors.length === 0,
        errors,
        warnings
    };
}
/**
 * Validates that an entity definition file properly binds the target animation controller.
 *
 * @param file Entity behavior pack definition object.
 * @param expectedControllerId The expected animation controller identifier.
 * @returns Result object detailing validation pass or failure conditions.
 */
export function validateBossGolemEntity(file, expectedControllerId = "controller.animation.boss_golem.state_machine") {
    const errors = [];
    const warnings = [];
    const entity = file["minecraft:entity"];
    if (!entity) {
        errors.push("Missing 'minecraft:entity' top-level node.");
        return { valid: false, errors, warnings };
    }
    const desc = entity.description;
    if (!desc) {
        errors.push("Missing 'description' block inside 'minecraft:entity'.");
        return { valid: false, errors, warnings };
    }
    if (desc.identifier !== "custom:boss_golem") {
        errors.push(`Expected identifier 'custom:boss_golem', found '${desc.identifier}'.`);
    }
    const animations = desc.animations ?? {};
    let boundAnimationKey = null;
    for (const [shortKey, id] of Object.entries(animations)) {
        if (id === expectedControllerId) {
            boundAnimationKey = shortKey;
            break;
        }
    }
    if (!boundAnimationKey) {
        errors.push(`Entity does not bind animation controller '${expectedControllerId}'.`);
    }
    else {
        const scriptAnimate = desc.scripts?.animate ?? [];
        const isAnimatedInScripts = scriptAnimate.some((entry) => {
            if (typeof entry === "string") {
                return entry === boundAnimationKey;
            }
            return Object.keys(entry).includes(boundAnimationKey);
        });
        if (!isAnimatedInScripts) {
            errors.push(`Bound animation controller '${boundAnimationKey}' is not declared in scripts.animate.`);
        }
    }
    return {
        valid: errors.length === 0,
        errors,
        warnings
    };
}
/**
 * Simulates discrete state machine evaluation across engine ticks.
 *
 * @param definition Animation controller definition.
 * @param initialContext Initial variable states and query values.
 * @param ticks Number of game ticks to step through.
 * @returns Object with visited state history, final state flag, and total transitions executed.
 */
export function simulateStateMachine(definition, initialContext, ticks) {
    const states = definition.states;
    let currentStateName = definition.initial_state;
    let context = { ...initialContext };
    const history = [currentStateName];
    let transitionsExecuted = 0;
    function runStatements(statements) {
        if (!statements)
            return;
        for (const stmt of statements) {
            if (stmt.includes("variable.state_flag =") || stmt.includes("variable.state_flag=")) {
                const parts = stmt.split("=");
                const valStr = parts[1].replace(";", "").trim();
                const parsed = parseInt(valStr, 10);
                if (!isNaN(parsed)) {
                    context.stateFlag = parsed;
                }
            }
            else if (stmt.includes("variable.is_charging =") || stmt.includes("variable.is_charging=")) {
                const parts = stmt.split("=");
                const valStr = parts[1].replace(";", "").trim();
                context.isCharging = valStr === "1" || valStr === "true";
            }
        }
    }
    runStatements(states[currentStateName]?.on_entry);
    for (let tick = 0; tick < ticks; tick++) {
        context.animTime += 0.05;
        let transitionOccurred = true;
        let depth = 0;
        const maxTickDepth = 25;
        while (transitionOccurred && depth < maxTickDepth) {
            transitionOccurred = false;
            depth++;
            const stateObj = states[currentStateName];
            if (!stateObj || !stateObj.transitions)
                break;
            for (const t of stateObj.transitions) {
                for (const [targetState, condition] of Object.entries(t)) {
                    let matches = false;
                    if (condition.includes("variable.state_flag == 0")) {
                        if (context.stateFlag === 0 && (context.isCharging || context.isDelayedAttacking)) {
                            matches = true;
                        }
                    }
                    else if (condition.includes("variable.state_flag == 1")) {
                        if (context.stateFlag === 1 && context.animTime >= 1.5) {
                            matches = true;
                        }
                    }
                    else if (condition.includes("variable.state_flag == 2")) {
                        if (context.stateFlag === 2) {
                            if (condition.includes("query.anim_time >= 0.25") && context.animTime >= 0.25) {
                                matches = true;
                            }
                            else if (condition.includes("!query.is_alive") && !context.isAlive) {
                                matches = true;
                            }
                        }
                    }
                    else if (condition.includes("variable.state_flag == 3")) {
                        if (context.stateFlag === 3 && context.animTime >= 1.2) {
                            matches = true;
                        }
                    }
                    else if (condition.includes("variable.state_flag == 4")) {
                        if (context.stateFlag === 4 && context.animTime >= 0.8) {
                            matches = true;
                        }
                    }
                    else if (condition.includes("query.anim_time < 0.5") || condition.includes("q.anim_time < 0.5")) {
                        if (context.animTime < 0.5) {
                            matches = true;
                        }
                    }
                    else if (condition.includes("query.anim_time > 0.0") || condition.includes("query.anim_time >= 0.0") || condition.includes("query.anim_time > 1.0")) {
                        matches = true;
                    }
                    if (matches) {
                        runStatements(stateObj.on_exit);
                        currentStateName = targetState;
                        context.animTime = 0.0;
                        runStatements(states[currentStateName]?.on_entry);
                        history.push(currentStateName);
                        transitionsExecuted++;
                        transitionOccurred = true;
                        break;
                    }
                }
                if (transitionOccurred)
                    break;
            }
        }
        if (depth >= maxTickDepth) {
            throw new Error(`Watchdog lockout: Maximum execution depth exceeded in controller at state '${currentStateName}'. Cyclic dependency detected: query.anim_time -> state.transition -> query.anim_time.`);
        }
    }
    return {
        history,
        finalFlag: context.stateFlag,
        transitionsExecuted
    };
}
