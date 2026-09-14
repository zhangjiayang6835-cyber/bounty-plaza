/**
 * Core type interfaces for Minecraft Bedrock continuous collision detection.
 */

export type BedrockFaceName = "East" | "West" | "Up" | "Down" | "South" | "North";

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface AABB {
  center: Vector3;
  extent: Vector3;
}

export interface BedrockFace {
  name: BedrockFaceName;
  normal: Vector3;
  vertices: Vector3[];
}

export interface CollisionResult {
  hasCollision: boolean;
  timeOfImpact: number;
  normal: Vector3;
  cardinalDirection: BedrockFaceName | "None";
  contactPoint: Vector3;
}

export interface Ray {
  origin: Vector3;
  direction: Vector3;
  maxDistance: number;
}

export interface RaycastResult {
  hit: boolean;
  distance: number;
  subTickFraction: number;
  point: Vector3;
  normal: Vector3;
  warningDropped: boolean;
}

export interface StepResolutionResult {
  finalPosition: Vector3;
  collisions: CollisionResult[];
  tunnelingPrevented: boolean;
  remainingVelocity: Vector3;
}
