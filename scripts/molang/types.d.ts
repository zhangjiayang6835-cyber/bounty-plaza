/**
 * Representation of an individual state transition mapping.
 */
export type StateTransition = Record<string, string>;
/**
 * Bedrock animation controller state definition.
 */
export interface AnimationControllerState {
    animations?: string[];
    blend_transition?: number;
    on_entry?: string[];
    on_exit?: string[];
    transitions?: StateTransition[];
}
/**
 * Bedrock animation controller definition.
 */
export interface AnimationControllerDefinition {
    initial_state: string;
    states: Record<string, AnimationControllerState>;
}
/**
 * Top-level file format for Bedrock animation controllers.
 */
export interface AnimationControllersFile {
    format_version: string;
    animation_controllers: Record<string, AnimationControllerDefinition>;
}
/**
 * Description block of a Bedrock entity behavior pack.
 */
export interface EntityDescription {
    identifier: string;
    is_spawnable?: boolean;
    is_summonable?: boolean;
    is_experimental?: boolean;
    animations?: Record<string, string>;
    scripts?: {
        animate?: Array<string | Record<string, string>>;
    };
}
/**
 * Bedrock entity behavior pack JSON schema.
 */
export interface EntityBehaviorFile {
    format_version: string;
    "minecraft:entity": {
        description: EntityDescription;
        component_groups?: Record<string, Record<string, unknown>>;
        components?: Record<string, unknown>;
    };
}
/**
 * Diagnostics and errors reported during Molang validation.
 */
export interface MolangValidationResult {
    valid: boolean;
    errors: string[];
    warnings: string[];
}
/**
 * Diagnostic analysis of state machine cycles and transition safety.
 */
export interface CycleAnalysisResult {
    isAcyclic: boolean;
    hasOscillationRisk: boolean;
    detectedCycles: string[][];
    maxEvaluationDepth: number;
    usesDiscreteFlags: boolean;
    usesBlendTransitions: boolean;
    errors: string[];
}
/**
 * Evaluation context for simulating state transitions across ticks.
 */
export interface SimulationContext {
    animTime: number;
    stateFlag: number;
    isAlive: boolean;
    isCharging: boolean;
    isDelayedAttacking: boolean;
}
