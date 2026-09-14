/**
 * Vector in 3-dimensional Cartesian space.
 */
export interface Vector3 {
    x: number;
    y: number;
    z: number;
}
/**
 * Axis-Aligned Bounding Box conforming to Minecraft Bedrock Script API.
 */
export interface AABB {
    center: Vector3;
    extent: Vector3;
}
/**
 * Bedrock cardinal directions reflecting Minecraft axis alignment:
 * +X = East, -X = West, +Y = Up, -Y = Down, +Z = South, -Z = North.
 */
export type BedrockFaceName = "East" | "West" | "Up" | "Down" | "South" | "North";
/**
 * Cardinal face definition on a Bedrock bounding box.
 */
export interface BedrockFace {
    name: BedrockFaceName;
    normal: Vector3;
    vertices: Vector3[];
}
/**
 * Continuous collision detection hit result.
 */
export interface CollisionHit {
    hasCollision: boolean;
    timeOfImpact: number;
    normal: Vector3;
    contactPoint: Vector3;
    cardinalDirection: BedrockFaceName | null;
}
/**
 * Geometric ray definition for raycast testing.
 */
export interface Ray {
    origin: Vector3;
    direction: Vector3;
    maxDistance: number;
}
/**
 * Result of a continuous raycast across sub-tick intervals.
 */
export interface RaycastSubTickHit {
    hit: boolean;
    distance: number;
    subTickFraction: number;
    point: Vector3;
    normal: Vector3;
    warningDropped: boolean;
}
/**
 * Outcome of resolving kinematic entity translation across an obstacle field.
 */
export interface StepResolutionResult {
    finalPosition: Vector3;
    finalVelocity: Vector3;
    collisions: CollisionHit[];
    tunnelingPrevented: boolean;
}
