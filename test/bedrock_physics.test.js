/**
 * Node.js native test runner test suite for Bedrock physics and 1-tick potion effect math.
 */

import { describe, it } from "node:test";
import assert from "node:assert/strict";
import {
  PlayerPhysicsState,
  PotionEffectManager,
  FallDamageEngine,
} from "../dist/scripts/bedrock_physics/index.js";

describe("Bedrock Physics 1-Tick Potion Effect Math", () => {
  it("computes dynamic dampening multiplier with double precision for amplifier > 128", () => {
    const mult0 = PotionEffectManager.calculateDampeningMultiplier(0);
    assert.strictEqual(mult0, 1.0);

    const mult128 = PotionEffectManager.calculateDampeningMultiplier(128);
    assert.strictEqual(mult128, 1.5);

    const mult130 = PotionEffectManager.calculateDampeningMultiplier(130);
    assert.strictEqual(mult130, 1.0 + 130 / 256);
    assert.ok(mult130 > 1.5);

    const mult255 = PotionEffectManager.calculateDampeningMultiplier(255);
    assert.strictEqual(mult255, 1.0 + 255 / 256);
  });

  it("preserves internal velocity vectors across 1-tick effect applications", () => {
    const state = new PlayerPhysicsState(
      { x: 0, y: 50, z: 0 },
      { x: 1.2, y: -2.3, z: 0.8 },
      100.0,
    );
    const initialVy = state.velocity.y;

    PotionEffectManager.applyPotionEffects(state, [
      { type: "minecraft:jump_boost", amplifier: 130, duration: 1 },
      { type: "minecraft:absorption", amplifier: 130, duration: 1 },
    ]);

    assert.strictEqual(state.velocity.x, 1.2);
    assert.strictEqual(state.velocity.y, initialVy);
    assert.strictEqual(state.velocity.z, 0.8);
  });

  it("calculates dynamic safe velocity threshold against Bedrock gravity constant 0.08", () => {
    const state = new PlayerPhysicsState();
    state.pendingJumpBoost = 0;
    assert.strictEqual(FallDamageEngine.calculateSafeVelocityThreshold(state), 3.0);

    state.pendingJumpBoost = 130;
    const expectedSafe = 3.0 * (1.0 + 130 / 256);
    assert.strictEqual(
      FallDamageEngine.calculateSafeVelocityThreshold(state),
      expectedSafe,
    );

    const safeResult = FallDamageEngine.resolveFallDamage(state, 2.0, -3.2);
    assert.strictEqual(safeResult.rawDamage, 0.0);
    assert.strictEqual(safeResult.finalHealthDamage, 0.0);
  });

  it("accumulates absorption shield buffer and prevents health damage", () => {
    const state = new PlayerPhysicsState({ x: 0, y: 0, z: 0 }, { x: 0, y: 0, z: 0 }, 0.0);
    PotionEffectManager.applyPotionEffects(state, [
      { type: "minecraft:absorption", amplifier: 130, duration: 1 },
    ]);

    const expectedAbsorption = 4.0 * (130 + 1);
    assert.strictEqual(state.shieldBuffer, expectedAbsorption);

    const damageResult = FallDamageEngine.resolveFallDamage(state, 20.0, -5.0);
    assert.ok(damageResult.absorptionDamageAbsorbed > 0.0);
    assert.strictEqual(damageResult.finalHealthDamage, 0.0);
    assert.strictEqual(damageResult.remainingHealth, 20.0);
  });

  it("resolves the fall distance 0.00 and vy -1.84 anomaly without lethal damage", () => {
    const state = new PlayerPhysicsState(
      { x: 0, y: 0, z: 0 },
      { x: 0, y: -1.84, z: 0 },
      100.0,
    );
    state.shieldBuffer = 20.0;
    state.pendingJumpBoost = 130;

    const result = FallDamageEngine.resolveFallDamage(state, 0.0, -1.84);
    assert.strictEqual(result.finalHealthDamage, 0.0);
    assert.strictEqual(result.remainingHealth, 20.0);
    assert.strictEqual(result.lethalPrevented, true);
    assert.strictEqual(state.anomalyWarnings.length, 1);
  });

  it("satisfies the integration test requirement (fall_y:42, amp:130, duration:1)", () => {
    const state = new PlayerPhysicsState(
      { x: 0, y: 42, z: 0 },
      { x: 0, y: 0, z: 0 },
      100.0,
    );
    const result = FallDamageEngine.simulateFall(state, 42.0, 130, 1);

    assert.ok(result.finalHealthDamage < 5.0);
    assert.strictEqual(result.lethalPrevented, true);
    assert.ok(result.remainingHealth > 15.0);
    assert.ok(state.velocityHistory.length > 0);
  });
});
