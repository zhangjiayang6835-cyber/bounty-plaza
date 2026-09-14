/**
 * Continuous Collision Detection (CCD) engine implementing swept AABB
 * and sub-tick raycast synchronization.
 */
import { CollisionResultDef, RaycastResultDef, RayDef, RayHitDef, StepResultDef, Vector3D } from "./types.js";
import { BoundingBox } from "./BedrockAABB.js";
export declare class SweptAABBEngine {
    static readonly EPSILON = 0.000001;
    static readonly TUNNELING_THRESHOLD = 1.5;
    /**
     * Evaluates continuous swept collision between moving volume and obstacle.
     */
    static testSweptAABB(moving: BoundingBox, velocity: Vector3D, obstacle: BoundingBox): CollisionResultDef;
    /**
     * Tests dynamic entity collision against another moving entity via relative velocity.
     */
    static testDynamicVsDynamic(boxA: BoundingBox, velA: Vector3D, boxB: BoundingBox, velB: Vector3D): CollisionResultDef;
    /**
     * Resolves multi-obstacle sliding deflection along collision surface normals.
     */
    static resolveKinematicStep(entityBox: BoundingBox, velocity: Vector3D, obstacles: BoundingBox[]): StepResultDef;
    /**
     * Validates parametric raycast against tick-interpolated and swept bounding volumes.
     */
    static synchronizeSubTickRaycast(entityBox: BoundingBox, velocity: Vector3D, ray: RayDef, subTickDelta?: number, tick?: number): RaycastResultDef;
    /**
     * Tests parametric ray intersection against stationary bounding volume.
     */
    static intersectRayAABB(ray: RayDef, box: BoundingBox): RayHitDef;
    private static testSlab;
    private static computeSingleAxis;
    private static computeAxisTimes;
    private static determineSurfaceNormal;
    private static clampContactPoint;
}
