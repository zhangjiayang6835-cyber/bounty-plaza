import { BedrockAABB } from "./BedrockAABB.js";
import { BedrockFaceName, CollisionHit, Vector3 } from "./types.js";

/**
 * Continuous collision detection calculator using swept AABB algorithms.
 */
export class SweptAABBCalculator {
  private static readonly EPSILON = 1e-6;

  /**
   * Evaluates continuous swept collision between moving entity box and static obstacle.
   * @param moving Initial bounding box of the translating entity.
   * @param velocity Translation vector across the evaluated interval.
   * @param obstacle Static obstacle bounding box.
   * @returns CollisionHit containing time of impact, normal, and contact coordinates.
   */
  public static testSweptAABB(
    moving: BedrockAABB,
    velocity: Vector3,
    obstacle: BedrockAABB
  ): CollisionHit {
    const noHit: CollisionHit = {
      hasCollision: false,
      timeOfImpact: 1.0,
      normal: { x: 0, y: 0, z: 0 },
      contactPoint: { x: 0, y: 0, z: 0 },
      cardinalDirection: null
    };

    const broadphase = moving.expand(velocity);
    if (!broadphase.intersects(obstacle)) {
      return noHit;
    }

    if (moving.intersects(obstacle)) {
      return {
        hasCollision: true,
        timeOfImpact: 0.0,
        normal: { x: 0, y: 0, z: 0 },
        contactPoint: { ...moving.center },
        cardinalDirection: null
      };
    }

    let xEntryDist: number;
    let xExitDist: number;
    if (velocity.x > 0) {
      xEntryDist = obstacle.min.x - moving.max.x;
      xExitDist = obstacle.max.x - moving.min.x;
    } else {
      xEntryDist = obstacle.max.x - moving.min.x;
      xExitDist = obstacle.min.x - moving.max.x;
    }

    let yEntryDist: number;
    let yExitDist: number;
    if (velocity.y > 0) {
      yEntryDist = obstacle.min.y - moving.max.y;
      yExitDist = obstacle.max.y - moving.min.y;
    } else {
      yEntryDist = obstacle.max.y - moving.min.y;
      yExitDist = obstacle.min.y - moving.max.y;
    }

    let zEntryDist: number;
    let zExitDist: number;
    if (velocity.z > 0) {
      zEntryDist = obstacle.min.z - moving.max.z;
      zExitDist = obstacle.max.z - moving.min.z;
    } else {
      zEntryDist = obstacle.max.z - moving.min.z;
      zExitDist = obstacle.min.z - moving.max.z;
    }

    let xEntryTime: number;
    let xExitTime: number;
    if (Math.abs(velocity.x) < SweptAABBCalculator.EPSILON) {
      if (moving.max.x <= obstacle.min.x || moving.min.x >= obstacle.max.x) {
        return noHit;
      }
      xEntryTime = -Infinity;
      xExitTime = Infinity;
    } else {
      xEntryTime = xEntryDist / velocity.x;
      xExitTime = xExitDist / velocity.x;
    }

    let yEntryTime: number;
    let yExitTime: number;
    if (Math.abs(velocity.y) < SweptAABBCalculator.EPSILON) {
      if (moving.max.y <= obstacle.min.y || moving.min.y >= obstacle.max.y) {
        return noHit;
      }
      yEntryTime = -Infinity;
      yExitTime = Infinity;
    } else {
      yEntryTime = yEntryDist / velocity.y;
      yExitTime = yExitDist / velocity.y;
    }

    let zEntryTime: number;
    let zExitTime: number;
    if (Math.abs(velocity.z) < SweptAABBCalculator.EPSILON) {
      if (moving.max.z <= obstacle.min.z || moving.min.z >= obstacle.max.z) {
        return noHit;
      }
      zEntryTime = -Infinity;
      zExitTime = Infinity;
    } else {
      zEntryTime = zEntryDist / velocity.z;
      zExitTime = zExitDist / velocity.z;
    }

    const entryTime = Math.max(xEntryTime, yEntryTime, zEntryTime);
    const exitTime = Math.min(xExitTime, yExitTime, zExitTime);

    if (
      entryTime > exitTime ||
      entryTime < 0.0 ||
      entryTime > 1.0 ||
      (xEntryTime < 0.0 && yEntryTime < 0.0 && zEntryTime < 0.0)
    ) {
      return noHit;
    }

    let normal: Vector3;
    let cardinal: BedrockFaceName;
    if (entryTime === xEntryTime) {
      if (xEntryDist < 0.0) {
        normal = { x: 1, y: 0, z: 0 };
        cardinal = "East";
      } else {
        normal = { x: -1, y: 0, z: 0 };
        cardinal = "West";
      }
    } else if (entryTime === yEntryTime) {
      if (yEntryDist < 0.0) {
        normal = { x: 0, y: 1, z: 0 };
        cardinal = "Up";
      } else {
        normal = { x: 0, y: -1, z: 0 };
        cardinal = "Down";
      }
    } else {
      if (zEntryDist < 0.0) {
        normal = { x: 0, y: 0, z: 1 };
        cardinal = "South";
      } else {
        normal = { x: 0, y: 0, z: -1 };
        cardinal = "North";
      }
    }

    const hitCenter: Vector3 = {
      x: moving.center.x + velocity.x * entryTime,
      y: moving.center.y + velocity.y * entryTime,
      z: moving.center.z + velocity.z * entryTime
    };

    const contactPoint: Vector3 = {
      x: Math.max(obstacle.min.x, Math.min(obstacle.max.x, hitCenter.x)),
      y: Math.max(obstacle.min.y, Math.min(obstacle.max.y, hitCenter.y)),
      z: Math.max(obstacle.min.z, Math.min(obstacle.max.z, hitCenter.z))
    };

    return {
      hasCollision: true,
      timeOfImpact: entryTime,
      normal,
      contactPoint,
      cardinalDirection: cardinal
    };
  }

  /**
   * Tests dynamic entity versus dynamic obstacle using relative motion vector.
   * @param boxA Primary moving entity bounds.
   * @param velA Velocity vector of primary entity.
   * @param boxB Secondary moving entity bounds.
   * @param velB Velocity vector of secondary entity.
   * @returns CollisionHit based on relative kinematics.
   */
  public static testDynamicVsDynamic(
    boxA: BedrockAABB,
    velA: Vector3,
    boxB: BedrockAABB,
    velB: Vector3
  ): CollisionHit {
    const relVel: Vector3 = {
      x: velA.x - velB.x,
      y: velA.y - velB.y,
      z: velA.z - velB.z
    };
    return SweptAABBCalculator.testSweptAABB(boxA, relVel, boxB);
  }
}
