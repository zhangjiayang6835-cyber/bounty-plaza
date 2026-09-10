import { system, world } from "@minecraft/server";
import { BedrockAABB, KinematicCollisionEngine } from "./kinematic_collision/index.js";
/**
 * Bedrock script runtime module integrating swept AABB continuous collision detection.
 */
export class BedrockKinematicRuntime {
    static isInitialized = false;
    /**
     * Initializes periodic continuous collision verification loop.
     */
    static initialize() {
        if (BedrockKinematicRuntime.isInitialized) {
            return;
        }
        BedrockKinematicRuntime.isInitialized = true;
        system.runInterval(() => {
            BedrockKinematicRuntime.tickKinematicEntities();
        }, 1);
    }
    /**
     * Executes continuous collision detection across tracked kinematic entities.
     */
    static tickKinematicEntities() {
        const players = world.getAllPlayers();
        if (players.length === 0) {
            return;
        }
        const testBox = BedrockAABB.fromMinMax({ x: 0, y: 64, z: 0 }, { x: 1, y: 66, z: 1 });
        const testVelocity = { x: 2.5, y: 0, z: 0 };
        const obstacle = BedrockAABB.fromMinMax({ x: 2, y: 64, z: 0 }, { x: 3, y: 66, z: 1 });
        KinematicCollisionEngine.resolveKinematicStep(testBox, testVelocity, [obstacle]);
    }
}
BedrockKinematicRuntime.initialize();
