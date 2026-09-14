/**
 * Behavior pack entrypoint for Minecraft Bedrock kinematic continuous collision detection.
 */

import { system } from "@minecraft/server";
import { BedrockAABB, KinematicCollisionEngine } from "./kinematic_collision/index.js";

/**
 * Initializes continuous collision monitoring loop across active ticks.
 */
export function initializeKinematicMonitor(): void {
  system.runInterval(() => {
    const defaultBox = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 0.3, y: 0.9, z: 0.3 });
    const zeroVelocity = { x: 0, y: 0, z: 0 };
    KinematicCollisionEngine.resolveKinematicStep(defaultBox, zeroVelocity, []);
  }, 1);
}
