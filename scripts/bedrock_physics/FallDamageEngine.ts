/**
 * Kinetic fall damage resolution and shield mitigation engine.
 */

import { PlayerPhysicsState } from "./PlayerPhysicsState.js";
import { PotionEffectManager } from "./PotionEffectManager.js";
import { BedrockPotionEffect, FallDamageResult } from "./types.js";

/**
 * Handles fall damage calculations against Bedrock gravity invariants.
 */
export class FallDamageEngine {
  /**
   * Calculates the dynamic safe downward velocity threshold.
   */
  public static calculateSafeVelocityThreshold(state: PlayerPhysicsState): number {
    const boostTerm = state.pendingJumpBoost / state.constants.amplifierScaleFactor;
    return state.constants.baseSafeThreshold * (1.0 + boostTerm);
  }

  /**
   * Resolves impact fall damage with shield and attribute buffers.
   */
  public static resolveFallDamage(
    state: PlayerPhysicsState,
    fallDistance: number,
    impactVelocityY: number,
  ): FallDamageResult {
    const safeThreshold = this.calculateSafeVelocityThreshold(state);
    const dampening = PotionEffectManager.calculateDampeningMultiplier(
      state.pendingJumpBoost,
      state.constants.amplifierScaleFactor,
    );

    if (fallDistance <= 0.001 && impactVelocityY < -0.5) {
      state.anomalyWarnings.push(
        `Anomaly detected: fall_distance=${fallDistance.toFixed(2)}, vy=${impactVelocityY.toFixed(2)}`,
      );
    }

    let rawDamage = 0.0;
    if (impactVelocityY < -safeThreshold) {
      const kineticEquivalent =
        (impactVelocityY * impactVelocityY) / (2.0 * state.constants.gravity);
      rawDamage = Math.max(0.0, kineticEquivalent - state.constants.baseSafeThreshold);
    }

    const absorbedAbsorption = Math.min(state.shieldBuffer, rawDamage);
    state.shieldBuffer -= absorbedAbsorption;
    const damageAfterAbsorption = rawDamage - absorbedAbsorption;

    const absorbedCustom = Math.min(state.customShieldBuffer, damageAfterAbsorption);
    state.customShieldBuffer -= absorbedCustom;
    const finalHealthDamage = Math.max(0.0, damageAfterAbsorption - absorbedCustom);

    state.health = Math.max(0.0, state.health - finalHealthDamage);
    state.resetPendingJumpBoost();

    return {
      fallDistance,
      impactVelocityY,
      safeThreshold,
      rawDamage,
      absorptionDamageAbsorbed: absorbedAbsorption,
      customShieldDamageAbsorbed: absorbedCustom,
      finalHealthDamage,
      remainingHealth: state.health,
      lethalPrevented: state.health > 0.0,
      dampeningMultiplier: dampening,
    };
  }

  /**
   * Executes an end-to-end kinematic fall simulation with 1-tick cycled effects.
   */
  public static simulateFall(
    state: PlayerPhysicsState,
    fallHeight: number,
    amplifier: number = 130,
    duration: number = 1,
  ): FallDamageResult {
    state.position.y = fallHeight;
    state.velocity.y = 0.0;
    state.fallDistance = 0.0;
    state.velocityHistory = [];

    const jumpBoostEffect: BedrockPotionEffect = {
      type: "minecraft:jump_boost",
      amplifier,
      duration,
    };
    const absorptionEffect: BedrockPotionEffect = {
      type: "minecraft:absorption",
      amplifier,
      duration,
    };
    const activeEffects = [jumpBoostEffect, absorptionEffect];

    while (state.position.y > 0.0) {
      PotionEffectManager.applyPotionEffects(state, activeEffects);
      state.integrateTick();
    }

    const impactVelocityY = state.velocity.y;
    return this.resolveFallDamage(state, state.fallDistance, impactVelocityY);
  }
}
