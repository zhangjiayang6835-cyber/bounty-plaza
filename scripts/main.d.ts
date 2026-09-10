/**
 * Main script entrypoint for Bedrock Behavior Pack Kinematic Hitbox Manager.
 */
import { KinematicHitboxEngine } from "./hitbox_math/index.js";
export declare const hitboxEngine: KinematicHitboxEngine;
/**
 * Handles per-tick kinematic hitbox updates and continuous collision detection.
 */
export declare function onKinematicTick(): void;
/**
 * Initializes Script API hooks when running in Minecraft Bedrock environment.
 */
export declare function initializeScriptHooks(): Promise<void>;
