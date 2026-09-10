/**
 * High-level Kinematic Hitbox and Continuous Collision Detection manager for Bedrock Script API.
 */
import { BoundingBox, Vector3 } from "./BedrockAABB.js";
import { CollisionResultDef, RaycastResultDef, RayDef, StepResultDef, Vector3D } from "./types.js";
export interface TrackedKinematicEntity {
    id: string;
    typeId: string;
    box: BoundingBox;
    velocity: Vector3;
    lastTick: number;
}
export declare class KinematicHitboxEngine {
    private entities;
    private obstacles;
    /**
     * Registers or updates a tracked kinematic entity.
     */
    trackEntity(id: string, typeId: string, position: Vector3D, extent: Vector3D, velocity: Vector3D, tick: number): void;
    /**
     * Registers a static obstacle bounding volume.
     */
    addObstacle(position: Vector3D, extent: Vector3D): void;
    /**
     * Updates all tracked entities by one tick using continuous swept collision detection.
     */
    tickKinematics(currentTick: number): Map<string, StepResultDef>;
    /**
     * Validates a raycast against all kinematic entities using sub-tick interpolation.
     */
    raycastKinematicEntities(ray: RayDef, subTickDelta: number, tick: number): {
        entityId: string;
        result: RaycastResultDef;
    } | null;
    /**
     * Resolves the tick 4192 raycast miss log warning from Issue #1305.
     */
    resolveTick4192Scenario(): RaycastResultDef;
    /**
     * Evaluates pairwise swept collision between two kinematic entities.
     */
    testEntityPair(idA: string, idB: string): CollisionResultDef | null;
}
