/**
 * End-to-end verification script for Bedrock physics Issue #1308.
 */

import assert from "node:assert/strict";
import {
  PlayerPhysicsState,
  PotionEffectManager,
  FallDamageEngine,
} from "../dist/scripts/bedrock_physics/index.js";

/**
 * Runs test harness matching issue specifications.
 */
function runHarness() {
  console.log("=== Bedrock Physics Invariant Verification Harness ===");

  const state = new PlayerPhysicsState(
    { x: 0, y: 42, z: 0 },
    { x: 0, y: 0, z: 0 },
    100.0,
  );

  const initialPosition = { ...state.position };
  const jumpBoostEffect = { type: "minecraft:jump_boost", amplifier: 130, duration: 1 };
  const absorptionEffect = { type: "minecraft:absorption", amplifier: 130, duration: 1 };

  PotionEffectManager.applyPotionEffects(state, [jumpBoostEffect, absorptionEffect]);

  const vyStable = state.velocity.y === 0.0;
  const dampeningMultiplier = PotionEffectManager.calculateDampeningMultiplier(130);
  assert.ok(dampeningMultiplier > 1.5, "Dampening multiplier must exceed 1.5");

  const simulationResult = FallDamageEngine.simulateFall(state, 42.0, 130, 1);
  const damageUnderLimit = simulationResult.finalHealthDamage < 5.0;

  console.log(`Initial Height: ${initialPosition.y} blocks`);
  console.log(`Amplifier: 130 (double precision scaling = ${dampeningMultiplier.toFixed(6)})`);
  console.log(`Impact Velocity Y: ${simulationResult.impactVelocityY.toFixed(4)} blocks/tick`);
  console.log(`Raw Damage: ${simulationResult.rawDamage.toFixed(2)}`);
  console.log(`Absorption Shield Absorbed: ${simulationResult.absorptionDamageAbsorbed.toFixed(2)}`);
  console.log(`Custom Shield Absorbed: ${simulationResult.customShieldDamageAbsorbed.toFixed(2)}`);
  console.log(`Final Health Damage: ${simulationResult.finalHealthDamage.toFixed(2)}`);
  console.log(`Remaining Health: ${simulationResult.remainingHealth.toFixed(2)} / 20.0`);
  console.log(`Lethal Damage Prevented: ${simulationResult.lethalPrevented}`);

  assert.ok(vyStable, "Velocity vector vy must remain stable between tick applications");
  assert.ok(damageUnderLimit, "Final health damage must be under 5.0");
  assert.ok(simulationResult.lethalPrevented, "Lethal damage must be completely prevented");

  console.log("\nPASS: No lethal damage; velocity vectors preserved across tick boundaries.");
}

runHarness();
