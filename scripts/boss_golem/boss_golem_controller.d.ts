import type { Entity } from "@minecraft/server";
/**
 * Discrete enumeration of boss golem operational states.
 */
export declare enum BossGolemState {
    Idle = 0,
    Charging = 1,
    EvalCharge = 2,
    SlamAttack = 3,
    Recovery = 4
}
/**
 * Structural interface matching Bedrock entity dynamic property operations.
 */
export interface EntityDynamicPropertyHolder {
    setDynamicProperty(identifier: string, value: string | number | boolean): void;
    getDynamicProperty(identifier: string): string | number | boolean | undefined;
}
/**
 * Controller class interfacing Bedrock Script API with Boss Golem behavior.
 */
export declare class BossGolemController {
    private readonly entity;
    private currentState;
    /**
     * Initializes a new controller instance for the target entity.
     *
     * @param entity Target boss golem entity or dynamic property holder.
     */
    constructor(entity: EntityDynamicPropertyHolder | Entity);
    /**
     * Returns current internal state enum value.
     */
    getState(): BossGolemState;
    /**
     * Transitions entity to the charging phase and updates discrete state flags.
     */
    triggerCharge(): void;
    /**
     * Advances state from charging to evaluation phase.
     */
    advanceToEval(): void;
    /**
     * Advances state from evaluation to slam attack.
     */
    executeSlam(): void;
    /**
     * Completes attack and enters recovery state.
     */
    enterRecovery(): void;
    /**
     * Resets boss state back to idle upon recovery completion.
     */
    resetToIdle(): void;
    /**
     * Internal helper to persist state flag to entity dynamic properties.
     */
    private setState;
    /**
     * Initializes initial property values on the entity.
     */
    private initializeDynamicProperties;
}
