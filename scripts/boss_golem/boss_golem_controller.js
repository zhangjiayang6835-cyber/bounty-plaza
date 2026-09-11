/**
 * Discrete enumeration of boss golem operational states.
 */
export var BossGolemState;
(function (BossGolemState) {
    BossGolemState[BossGolemState["Idle"] = 0] = "Idle";
    BossGolemState[BossGolemState["Charging"] = 1] = "Charging";
    BossGolemState[BossGolemState["EvalCharge"] = 2] = "EvalCharge";
    BossGolemState[BossGolemState["SlamAttack"] = 3] = "SlamAttack";
    BossGolemState[BossGolemState["Recovery"] = 4] = "Recovery";
})(BossGolemState || (BossGolemState = {}));
/**
 * Controller class interfacing Bedrock Script API with Boss Golem behavior.
 */
export class BossGolemController {
    entity;
    currentState = BossGolemState.Idle;
    /**
     * Initializes a new controller instance for the target entity.
     *
     * @param entity Target boss golem entity or dynamic property holder.
     */
    constructor(entity) {
        this.entity = entity;
        this.initializeDynamicProperties();
    }
    /**
     * Returns current internal state enum value.
     */
    getState() {
        return this.currentState;
    }
    /**
     * Transitions entity to the charging phase and updates discrete state flags.
     */
    triggerCharge() {
        if (this.currentState !== BossGolemState.Idle) {
            return;
        }
        this.setState(BossGolemState.Charging);
    }
    /**
     * Advances state from charging to evaluation phase.
     */
    advanceToEval() {
        if (this.currentState !== BossGolemState.Charging) {
            return;
        }
        this.setState(BossGolemState.EvalCharge);
    }
    /**
     * Advances state from evaluation to slam attack.
     */
    executeSlam() {
        if (this.currentState !== BossGolemState.EvalCharge) {
            return;
        }
        this.setState(BossGolemState.SlamAttack);
    }
    /**
     * Completes attack and enters recovery state.
     */
    enterRecovery() {
        if (this.currentState !== BossGolemState.SlamAttack) {
            return;
        }
        this.setState(BossGolemState.Recovery);
    }
    /**
     * Resets boss state back to idle upon recovery completion.
     */
    resetToIdle() {
        this.setState(BossGolemState.Idle);
    }
    /**
     * Internal helper to persist state flag to entity dynamic properties.
     */
    setState(nextState) {
        this.currentState = nextState;
        try {
            this.entity.setDynamicProperty("boss_state_flag", nextState);
        }
        catch {
        }
    }
    /**
     * Initializes initial property values on the entity.
     */
    initializeDynamicProperties() {
        try {
            const existing = this.entity.getDynamicProperty("boss_state_flag");
            if (typeof existing === "number") {
                this.currentState = existing;
            }
            else {
                this.entity.setDynamicProperty("boss_state_flag", BossGolemState.Idle);
            }
        }
        catch {
        }
    }
}
