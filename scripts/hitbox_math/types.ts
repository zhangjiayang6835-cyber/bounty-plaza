/**
 * Type definitions for Bedrock Hitbox Math and Swept Continuous Collision Detection.
 * Coordinates adhere to Minecraft Bedrock conventions:
 * +X = East,  -X = West
 * +Y = Up,    -Y = Down
 * +Z = South, -Z = North
 */

export interface Vector3D {
  x: number;
  y: number;
  z: number;
}

export type BedrockFaceName = "East" | "West" | "Up" | "Down" | "South" | "North";

export interface BedrockFaceDef {
  name: BedrockFaceName;
  normal: Vector3D;
}

export interface CollisionResultDef {
  hasCollision: boolean;
  timeOfImpact: number;
  normal: Vector3D;
  contactPoint: Vector3D;
  cardinalDirection: BedrockFaceName | "";
}

export interface RayDef {
  origin: Vector3D;
  direction: Vector3D;
  maxDistance: number;
}

export interface RayHitDef {
  hit: boolean;
  distance: number;
  point: Vector3D;
  normal: Vector3D;
}

export interface RaycastResultDef {
  hit: boolean;
  distance: number;
  subTickFraction: number;
  point: Vector3D;
  normal: Vector3D;
  warningMissResolved: boolean;
  tick: number;
}

export interface StepResultDef {
  finalPosition: Vector3D;
  finalVelocity: Vector3D;
  collisions: CollisionResultDef[];
  tunnelingPrevented: boolean;
}
