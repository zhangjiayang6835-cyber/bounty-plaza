import { BedrockAABB } from "./BedrockAABB.js";
import { BedrockFaceName, CollisionResult, Vector3 } from "./types.js";

/**
 * Continuous collision detection engine executing Swept AABB tests.
 */
export class SweptAABB {
  private static readonly EPSILON = 1e-8;

  /**
   * Tests continuous collision between a moving BedrockAABB and stationary obstacle BedrockAABB.
   * @param moving Moving entity bounding box.
   * @param velocity Displacement vector across discrete interval.
   * @param obstacle Stationary obstacle bounding box.
   * @returns Detailed collision detection result.
   */
  public static testSweptAABB(
    moving: BedrockAABB,
    velocity: Vector3,
    obstacle: BedrockAABB
  ): CollisionResult {
    const emptyResult: CollisionResult = {
      hasCollision: false,
      timeOfImpact: 1.0,
      normal: { x: 0, y: 0, z: 0 },
      cardinalDirection: "None",
      contactPoint: { x: 0, y: 0, z: 0 }
    };

    const entryDist: Vector3 = {
      x: velocity.x > 0 ? obstacle.min.x - moving.max.x : obstacle.max.x - moving.min.x,
      y: velocity.y > 0 ? obstacle.min.y - moving.max.y : obstacle.max.y - moving.min.y,
      z: velocity.z > 0 ? obstacle.min.z - moving.max.z : obstacle.max.z - moving.min.z
    };

    const exitDist: Vector3 = {
      x: velocity.x > 0 ? obstacle.max.x - moving.min.x : obstacle.min.x - moving.max.x,
      y: velocity.y > 0 ? obstacle.max.y - moving.min.y : obstacle.min.y - moving.max.y,
      z: velocity.z > 0 ? obstacle.max.z - moving.min.z : obstacle.min.z - moving.max.z
    };

    const entryTime: Vector3 = {
      x: Math.abs(velocity.x) < this.EPSILON
        ? (moving.max.x <= obstacle.min.x || moving.min.x >= obstacle.max.x ? Infinity : -Infinity)
        : entryDist.x / velocity.x,
      y: Math.abs(velocity.y) < this.EPSILON
        ? (moving.max.y <= obstacle.min.y || moving.min.y >= obstacle.max.y ? Infinity : -Infinity)
        : entryDist.y / velocity.y,
      z: Math.abs(velocity.z) < this.EPSILON
        ? (moving.max.z <= obstacle.min.z || moving.min.z >= obstacle.max.z ? Infinity : -Infinity)
        : entryDist.z / velocity.z
    };

    const exitTime: Vector3 = {
      x: Math.abs(velocity.x) < this.EPSILON
        ? (moving.max.x <= obstacle.min.x || moving.min.x >= obstacle.max.x ? -Infinity : Infinity)
        : exitDist.x / velocity.x,
      y: Math.abs(velocity.y) < this.EPSILON
        ? (moving.max.y <= obstacle.min.y || moving.min.y >= obstacle.max.y ? -Infinity : Infinity)
        : exitDist.y / velocity.y,
      z: Math.abs(velocity.z) < this.EPSILON
        ? (moving.max.z <= obstacle.min.z || moving.min.z >= obstacle.max.z ? -Infinity : Infinity)
        : exitDist.z / velocity.z
    };

    if (
      entryTime.x === Infinity ||
      entryTime.y === Infinity ||
      entryTime.z === Infinity
    ) {
      return emptyResult;
    }

    const earliestEntry = Math.max(entryTime.x, entryTime.y, entryTime.z);
    const latestExit = Math.min(exitTime.x, exitTime.y, exitTime.z);

    if (earliestEntry > latestExit || earliestEntry < 0.0 || earliestEntry > 1.0) {
      return emptyResult;
    }

    let normal: Vector3 = { x: 0, y: 0, z: 0 };
    let cardinalDirection: BedrockFaceName = "East";

    if (earliestEntry === entryTime.x) {
      if (entryDist.x < 0) {
        normal = { x: 1, y: 0, z: 0 };
        cardinalDirection = "East";
      } else {
        normal = { x: -1, y: 0, z: 0 };
        cardinalDirection = "West";
      }
    } else if (earliestEntry === entryTime.y) {
      if (entryDist.y < 0) {
        normal = { x: 0, y: 1, z: 0 };
        cardinalDirection = "Up";
      } else {
        normal = { x: 0, y: -1, z: 0 };
        cardinalDirection = "Down";
      }
    } else {
      if (entryDist.z < 0) {
        normal = { x: 0, y: 0, z: 1 };
        cardinalDirection = "South";
      } else {
        normal = { x: 0, y: 0, z: -1 };
        cardinalDirection = "North";
      }
    }

    const hitCenter: Vector3 = {
      x: moving.center.x + velocity.x * earliestEntry,
      y: moving.center.y + velocity.y * earliestEntry,
      z: moving.center.z + velocity.z * earliestEntry
    };

    const contactPoint: Vector3 = {
      x: Math.max(obstacle.min.x, Math.min(obstacle.max.x, hitCenter.x)),
      y: Math.max(obstacle.min.y, Math.min(obstacle.max.y, hitCenter.y)),
      z: Math.max(obstacle.min.z, Math.min(obstacle.max.z, hitCenter.z))
    };

    return {
      hasCollision: true,
      timeOfImpact: earliestEntry,
      normal,
      cardinalDirection,
      contactPoint
    };
  }

  /**
   * Evaluates dynamic vs dynamic swept collision by subtracting velocity vectors.
   * @param movingA First moving bounding box.
   * @param velA Velocity of first entity.
   * @param movingB Second moving bounding box.
   * @param velB Velocity of second entity.
   * @returns Swept collision result relative to movingB.
   */
  public static testDynamicVsDynamic(
    movingA: BedrockAABB,
    velA: Vector3,
    movingB: BedrockAABB,
    velB: Vector3
  ): CollisionResult {
    const relVelocity: Vector3 = {
      x: velA.x - velB.x,
      y: velA.y - velB.y,
      z: velA.z - velB.z
    };
    return this.testSweptAABB(movingA, relVelocity, movingB);
  }
}
