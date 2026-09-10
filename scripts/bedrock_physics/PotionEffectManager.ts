/**
 * Potion effect application and amplifier scaling calculations.
 */

import { PlayerPhysicsState } from "./PlayerPhysicsState.js";
import { BedrockPotionEffect } from "./types.js";

/**
 * Manages status effect calculations and velocity vector preservation.
 */
export class PotionEffectManager {
  /**
   * Derives dynamic fall damage dampening multiplier with double precision.
   */
  public static calculateDampeningMultiplier(
    amplifier: number,
    scaleFactor: number = 256.0,
  ): number {
    const safeAmplifier = Math.max(0, amplifier);
    return 1.0 + safeAmplifier / scaleFactor;
  }

  /**
   * Applies 1-tick cycled potion effects without resetting kinematic velocity vectors.
   */
  public static applyPotionEffects(
    state: PlayerPhysicsState,
    effects: BedrockPotionEffect[],
  ): void {
    const pendingEffects = [...effects];

    for (const effect of pendingEffects) {
      if (effect.type === "minecraft:jump_boost" && effect.duration <= 1) {
        const dampeningMultiplier = this.calculateDampeningMultiplier(
          effect.amplifier,
          state.constants.amplifierScaleFactor,
        );
        state.customShieldBuffer *= dampeningMultiplier;
        state.pendingJumpBoost = effect.amplifier;
      }

      if (effect.type === "minecraft:absorption" && effect.duration <= 1) {
        const bonusHp =
          state.constants.absorptionBonusPerAmplifier * (effect.amplifier + 1);
        state.shieldBuffer += bonusHp;
      }
    }
  }
}
