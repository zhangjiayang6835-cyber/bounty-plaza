/**
 * Player physics state maintaining kinematic vectors and shield buffers.
 */

import { BedrockPhysicsConstants, KinematicVector3 } from "./types.js";

export const DEFAULT_BEDROCK_CONSTANTS: BedrockPhysicsConstants = {
  gravity: 0.08,
  airDrag: 0.98,
  baseSafeThreshold: 3.0,
  baseMaxHealth: 20.0,
  absorptionBonusPerAmplifier: 4.0,
  amplifierScaleFactor: 256.0,
};

/**
 * Encapsulates the kinematic state and custom buffers of a Bedrock entity.
 */
export class PlayerPhysicsState {
  public position: KinematicVector3;
  public velocity: KinematicVector3;
  public health: number;
  public maxHealth: number;
  public shieldBuffer: number;
  public customShieldBuffer: number;
  public pendingJumpBoost: number;
  public fallDistance: number;
  public velocityHistory: number[];
  public anomalyWarnings: string[];
  public constants: BedrockPhysicsConstants;

  /**
   * Constructs an instance of PlayerPhysicsState with default or custom initial values.
   */
  constructor(
    initialPosition: KinematicVector3 = { x: 0, y: 100, z: 0 },
    initialVelocity: KinematicVector3 = { x: 0, y: 0, z: 0 },
    customShield: number = 100.0,
    constants: BedrockPhysicsConstants = DEFAULT_BEDROCK_CONSTANTS,
  ) {
    this.position = { ...initialPosition };
    this.velocity = { ...initialVelocity };
    this.health = constants.baseMaxHealth;
    this.maxHealth = constants.baseMaxHealth;
    this.shieldBuffer = 0.0;
    this.customShieldBuffer = customShield;
    this.pendingJumpBoost = 0;
    this.fallDistance = 0.0;
    this.velocityHistory = [];
    this.anomalyWarnings = [];
    this.constants = constants;
  }

  /**
   * Advances the kinematic simulation by one physics tick.
   */
  public integrateTick(verticalImpulse: number = 0.0): void {
    const netAcceleration = verticalImpulse - this.constants.gravity;
    this.velocity.y = (this.velocity.y + netAcceleration) * this.constants.airDrag;
    this.position.y += this.velocity.y;
    this.velocityHistory.push(this.velocity.y);

    if (this.velocity.y < 0.0) {
      this.fallDistance += Math.abs(this.velocity.y);
    }
  }

  /**
   * Clears transient jump boost after impact resolution.
   */
  public resetPendingJumpBoost(): void {
    this.pendingJumpBoost = 0;
  }
}
