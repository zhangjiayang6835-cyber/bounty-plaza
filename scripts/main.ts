/**
 * Behavior pack entrypoint for Minecraft Bedrock 1-tick potion effect physics.
 */

import { system } from "@minecraft/server";
import {
  FallDamageEngine,
  PlayerPhysicsState,
  PotionEffectManager,
} from "./bedrock_physics/index.js";

/**
 * Initializes continuous physics loop and 1-tick effect cycling.
 */
export function initializeBedrockPhysicsMonitor(): void {
  const state = new PlayerPhysicsState();

  system.runInterval(() => {
    PotionEffectManager.applyPotionEffects(state, [
      { type: "minecraft:jump_boost", amplifier: 130, duration: 1 },
      { type: "minecraft:absorption", amplifier: 130, duration: 1 },
    ]);
    state.integrateTick();
    if (state.position.y <= 0) {
      FallDamageEngine.resolveFallDamage(state, state.fallDistance, state.velocity.y);
    }
  }, 1);
}
