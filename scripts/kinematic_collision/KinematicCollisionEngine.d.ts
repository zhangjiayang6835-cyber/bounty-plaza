import { BedrockAABB } from "./BedrockAABB.js";
import { Ray, RaycastSubTickHit, StepResolutionResult, Vector3 } from "./types.js";
/**
 * High-speed kinematic trajectory and continuous collision detection engine.
 * Resolves AABB desynchronization, projectile tunneling, and sub-tick collision dropouts.
 */
export declare class KinematicCollisionEngine {
    private static readonly EPSILON;
    private static readonly TUNNELING_VELOCITY_THRESHOLD;
    /**
     * Continuous resolution of rapid kinematic entity motion across static obstacles.
     * @param entityBox Bounding box of moving entity at start of step.
     * @param velocity Desired velocity vector in blocks per tick.
     * @param obstacles Collection of solid obstacle bounding boxes.
     * @returns StepResolutionResult containing final clamped coordinates and collision hits.
     */
    static resolveKinematicStep(entityBox: BedrockAABB, velocity: Vector3, obstacles: BedrockAABB[]): StepResolutionResult;
    /**
     * Synchronizes raycasts across sub-tick intervals to prevent collision dropouts.
     * @param entityBox Bounding box of entity at tick origin.
     * @param velocity Kinematic translation vector over the physics tick.
     * @param ray Raycast geometry.
     * @param subTickDelta Sub-tick interpolation fraction between 0.0 and 1.0.
     * @returns RaycastSubTickHit reporting continuous intersection without warning drops.
     */
    static synchronizeSubTickRaycast(entityBox: BedrockAABB, velocity: Vector3, ray: Ray, subTickDelta: number): RaycastSubTickHit;
    /**
     * Evaluates ray intersection against stationary Axis-Aligned Bounding Box.
     * @param ray Target ray.
     * @param box Target bounding box.
     * @returns Hit details with distance, normal, and intersection coordinates.
     */
    static intersectRayAABB(ray: Ray, box: BedrockAABB): {
        hit: boolean;
        distance: number;
        point: Vector3;
        normal: Vector3;
    };
}
