import { AnimationControllersFile, AnimationControllerDefinition, EntityBehaviorFile, MolangValidationResult, CycleAnalysisResult, SimulationContext } from "./types.js";
/**
 * Validates Molang expression syntax against Bedrock strict parsing standards.
 *
 * @param expression Raw Molang string.
 * @param isStatement Whether the string is expected to be a statement with side-effects.
 * @returns Result object containing validity status and diagnostic error messages.
 */
export declare function validateMolangSyntax(expression: string, isStatement?: boolean): MolangValidationResult;
/**
 * Performs static cycle analysis and watchdog evaluation on state machine transitions.
 *
 * @param definition Animation controller definition object.
 * @returns CycleAnalysisResult containing graph topology and oscillation hazard flags.
 */
export declare function analyzeControllerTransitions(definition: AnimationControllerDefinition): CycleAnalysisResult;
/**
 * Validates an entire animation controllers JSON configuration file.
 *
 * @param file Root JSON object of the animation controllers file.
 * @returns Result object containing validation outcomes and collected diagnostics.
 */
export declare function validateAnimationControllersFile(file: AnimationControllersFile): MolangValidationResult;
/**
 * Validates that an entity definition file properly binds the target animation controller.
 *
 * @param file Entity behavior pack definition object.
 * @param expectedControllerId The expected animation controller identifier.
 * @returns Result object detailing validation pass or failure conditions.
 */
export declare function validateBossGolemEntity(file: EntityBehaviorFile, expectedControllerId?: string): MolangValidationResult;
/**
 * Simulates discrete state machine evaluation across engine ticks.
 *
 * @param definition Animation controller definition.
 * @param initialContext Initial variable states and query values.
 * @param ticks Number of game ticks to step through.
 * @returns Object with visited state history, final state flag, and total transitions executed.
 */
export declare function simulateStateMachine(definition: AnimationControllerDefinition, initialContext: SimulationContext, ticks: number): {
    history: string[];
    finalFlag: number;
    transitionsExecuted: number;
};
