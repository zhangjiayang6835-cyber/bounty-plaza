import type { Entity } from "@minecraft/server";

/**
 * Discrete enumeration of boss golem operational states.
 */
export enum BossGolemState {
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
export class BossGolemController {
  private readonly entity: EntityDynamicPropertyHolder;
  private currentState: BossGolemState = BossGolemState.Idle;

  /**
   * Initializes a new controller instance for the target entity.
   *
   * @param entity Target boss golem entity or dynamic property holder.
   */
  constructor(entity: EntityDynamicPropertyHolder | Entity) {
    this.entity = entity as EntityDynamicPropertyHolder;
    this.initializeDynamicProperties();
  }

  /**
   * Returns current internal state enum value.
   */
  public getState(): BossGolemState {
    return this.currentState;
  }

  /**
   * Transitions entity to the charging phase and updates discrete state flags.
   */
  public triggerCharge(): void {
    if (this.currentState !== BossGolemState.Idle) {
      return;
    }
    this.setState(BossGolemState.Charging);
  }

  /**
   * Advances state from charging to evaluation phase.
   */
  public advanceToEval(): void {
    if (this.currentState !== BossGolemState.Charging) {
      return;
    }
    this.setState(BossGolemState.EvalCharge);
  }

  /**
   * Advances state from evaluation to slam attack.
   */
  public executeSlam(): void {
    if (this.currentState !== BossGolemState.EvalCharge) {
      return;
    }
    this.setState(BossGolemState.SlamAttack);
  }

  /**
   * Completes attack and enters recovery state.
   */
  public enterRecovery(): void {
    if (this.currentState !== BossGolemState.SlamAttack) {
      return;
    }
    this.setState(BossGolemState.Recovery);
  }

  /**
   * Resets boss state back to idle upon recovery completion.
   */
  public resetToIdle(): void {
    this.setState(BossGolemState.Idle);
  }

  /**
   * Internal helper to persist state flag to entity dynamic properties.
   */
  private setState(nextState: BossGolemState): void {
    this.currentState = nextState;
    try {
      this.entity.setDynamicProperty("boss_state_flag", nextState);
    } catch {
    }
  }

  /**
   * Initializes initial property values on the entity.
   */
  private initializeDynamicProperties(): void {
    try {
      const existing = this.entity.getDynamicProperty("boss_state_flag");
      if (typeof existing === "number") {
        this.currentState = existing;
      } else {
        this.entity.setDynamicProperty("boss_state_flag", BossGolemState.Idle);
      }
    } catch {
    }
  }
}
