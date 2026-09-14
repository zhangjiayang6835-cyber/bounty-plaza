import { BedrockAABB } from "./BedrockAABB.js";
import { CollisionHit, Vector3 } from "./types.js";
/**
 * Continuous collision detection calculator using swept AABB algorithms.
 */
export declare class SweptAABBCalculator {
    private static readonly EPSILON;
    /**
     * Evaluates continuous swept collision between moving entity box and static obstacle.
     * @param moving Initial bounding box of the translating entity.
     * @param velocity Translation vector across the evaluated interval.
     * @param obstacle Static obstacle bounding box.
     * @returns CollisionHit containing time of impact, normal, and contact coordinates.
     */
    static testSweptAABB(moving: BedrockAABB, velocity: Vector3, obstacle: BedrockAABB): CollisionHit;
    /**
     * Tests dynamic entity versus dynamic obstacle using relative motion vector.
     * @param boxA Primary moving entity bounds.
     * @param velA Velocity vector of primary entity.
     * @param boxB Secondary moving entity bounds.
     * @param velB Velocity vector of secondary entity.
     * @returns CollisionHit based on relative kinematics.
     */
    static testDynamicVsDynamic(boxA: BedrockAABB, velA: Vector3, boxB: BedrockAABB, velB: Vector3): CollisionHit;
}
