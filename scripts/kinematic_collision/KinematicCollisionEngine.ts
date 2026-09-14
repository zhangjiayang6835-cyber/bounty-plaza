import { BedrockAABB } from "./BedrockAABB.js";
import { SweptAABBCalculator } from "./SweptAABB.js";
import {
  CollisionHit,
  Ray,
  RaycastSubTickHit,
  StepResolutionResult,
  Vector3
} from "./types.js";

/**
 * High-speed kinematic trajectory and continuous collision detection engine.
 * Resolves AABB desynchronization, projectile tunneling, and sub-tick collision dropouts.
 */
export class KinematicCollisionEngine {
  private static readonly EPSILON = 1e-4;
  private static readonly TUNNELING_VELOCITY_THRESHOLD = 1.5;

  /**
   * Continuous resolution of rapid kinematic entity motion across static obstacles.
   * @param entityBox Bounding box of moving entity at start of step.
   * @param velocity Desired velocity vector in blocks per tick.
   * @param obstacles Collection of solid obstacle bounding boxes.
   * @returns StepResolutionResult containing final clamped coordinates and collision hits.
   */
  public static resolveKinematicStep(
    entityBox: BedrockAABB,
    velocity: Vector3,
    obstacles: BedrockAABB[]
  ): StepResolutionResult {
    let currentBox = entityBox;
    let remainingVel: Vector3 = { ...velocity };
    let finalPos: Vector3 = { ...entityBox.center };
    const recordedHits: CollisionHit[] = [];

    const speed = Math.hypot(velocity.x, velocity.y, velocity.z);
    const tunnelingRisk = speed >= KinematicCollisionEngine.TUNNELING_VELOCITY_THRESHOLD;

    for (let iteration = 0; iteration < 3; iteration++) {
      const remainingSpeed = Math.hypot(remainingVel.x, remainingVel.y, remainingVel.z);
      if (remainingSpeed < KinematicCollisionEngine.EPSILON) {
        break;
      }

      let earliestHit: CollisionHit | null = null;
      for (const obstacle of obstacles) {
        const hit = SweptAABBCalculator.testSweptAABB(currentBox, remainingVel, obstacle);
        if (hit.hasCollision) {
          if (earliestHit === null || hit.timeOfImpact < earliestHit.timeOfImpact) {
            earliestHit = hit;
          }
        }
      }

      if (earliestHit === null || !earliestHit.hasCollision) {
        finalPos = {
          x: currentBox.center.x + remainingVel.x,
          y: currentBox.center.y + remainingVel.y,
          z: currentBox.center.z + remainingVel.z
        };
        break;
      }

      recordedHits.push(earliestHit);

      const safeToi = Math.max(0, earliestHit.timeOfImpact - KinematicCollisionEngine.EPSILON);
      finalPos = {
        x: currentBox.center.x + remainingVel.x * safeToi,
        y: currentBox.center.y + remainingVel.y * safeToi,
        z: currentBox.center.z + remainingVel.z * safeToi
      };
      currentBox = new BedrockAABB(finalPos, currentBox.extent);

      const remainingTime = 1.0 - earliestHit.timeOfImpact;
      const dot =
        remainingVel.x * earliestHit.normal.x +
        remainingVel.y * earliestHit.normal.y +
        remainingVel.z * earliestHit.normal.z;

      remainingVel = {
        x: (remainingVel.x - dot * earliestHit.normal.x) * remainingTime,
        y: (remainingVel.y - dot * earliestHit.normal.y) * remainingTime,
        z: (remainingVel.z - dot * earliestHit.normal.z) * remainingTime
      };
    }

    return {
      finalPosition: finalPos,
      finalVelocity: remainingVel,
      collisions: recordedHits,
      tunnelingPrevented: tunnelingRisk && recordedHits.length > 0
    };
  }

  /**
   * Synchronizes raycasts across sub-tick intervals to prevent collision dropouts.
   * @param entityBox Bounding box of entity at tick origin.
   * @param velocity Kinematic translation vector over the physics tick.
   * @param ray Raycast geometry.
   * @param subTickDelta Sub-tick interpolation fraction between 0.0 and 1.0.
   * @returns RaycastSubTickHit reporting continuous intersection without warning drops.
   */
  public static synchronizeSubTickRaycast(
    entityBox: BedrockAABB,
    velocity: Vector3,
    ray: Ray,
    subTickDelta: number
  ): RaycastSubTickHit {
    const clampedDelta = Math.max(0, Math.min(1, subTickDelta));
    const interpolatedCenter: Vector3 = {
      x: entityBox.center.x + velocity.x * clampedDelta,
      y: entityBox.center.y + velocity.y * clampedDelta,
      z: entityBox.center.z + velocity.z * clampedDelta
    };
    const interpolatedBox = new BedrockAABB(interpolatedCenter, entityBox.extent);

    const hit = KinematicCollisionEngine.intersectRayAABB(ray, interpolatedBox);
    if (hit.hit) {
      return {
        hit: true,
        distance: hit.distance,
        subTickFraction: clampedDelta,
        point: hit.point,
        normal: hit.normal,
        warningDropped: false
      };
    }

    const sweptBox = entityBox.expand(velocity);
    const sweptHit = KinematicCollisionEngine.intersectRayAABB(ray, sweptBox);
    if (sweptHit.hit) {
      return {
        hit: true,
        distance: sweptHit.distance,
        subTickFraction: clampedDelta,
        point: sweptHit.point,
        normal: sweptHit.normal,
        warningDropped: false
      };
    }

    return {
      hit: false,
      distance: Infinity,
      subTickFraction: clampedDelta,
      point: { x: 0, y: 0, z: 0 },
      normal: { x: 0, y: 0, z: 0 },
      warningDropped: false
    };
  }

  /**
   * Evaluates ray intersection against stationary Axis-Aligned Bounding Box.
   * @param ray Target ray.
   * @param box Target bounding box.
   * @returns Hit details with distance, normal, and intersection coordinates.
   */
  public static intersectRayAABB(
    ray: Ray,
    box: BedrockAABB
  ): { hit: boolean; distance: number; point: Vector3; normal: Vector3 } {
    const noHit = {
      hit: false,
      distance: Infinity,
      point: { x: 0, y: 0, z: 0 },
      normal: { x: 0, y: 0, z: 0 }
    };

    let tMin = 0.0;
    let tMax = ray.maxDistance;
    let hitNormal: Vector3 = { x: 0, y: 0, z: 0 };

    const checkAxis = (
      origin: number,
      direction: number,
      boxMin: number,
      boxMax: number,
      normNeg: Vector3,
      normPos: Vector3
    ): boolean => {
      if (Math.abs(direction) < KinematicCollisionEngine.EPSILON) {
        return origin >= boxMin && origin <= boxMax;
      }

      let t1 = (boxMin - origin) / direction;
      let t2 = (boxMax - origin) / direction;
      let axisNormal = normNeg;

      if (t1 > t2) {
        const temp = t1;
        t1 = t2;
        t2 = temp;
        axisNormal = normPos;
      }

      if (t1 > tMin) {
        tMin = t1;
        hitNormal = axisNormal;
      }
      tMax = Math.min(tMax, t2);

      return tMin <= tMax;
    };

    if (
      !checkAxis(
        ray.origin.x,
        ray.direction.x,
        box.min.x,
        box.max.x,
        { x: -1, y: 0, z: 0 },
        { x: 1, y: 0, z: 0 }
      )
    ) {
      return noHit;
    }

    if (
      !checkAxis(
        ray.origin.y,
        ray.direction.y,
        box.min.y,
        box.max.y,
        { x: 0, y: -1, z: 0 },
        { x: 0, y: 1, z: 0 }
      )
    ) {
      return noHit;
    }

    if (
      !checkAxis(
        ray.origin.z,
        ray.direction.z,
        box.min.z,
        box.max.z,
        { x: 0, y: 0, z: -1 },
        { x: 0, y: 0, z: 1 }
      )
    ) {
      return noHit;
    }

    if (tMin > ray.maxDistance || tMax < 0.0) {
      return noHit;
    }

    const hitDist = Math.max(0.0, tMin);
    const hitPoint: Vector3 = {
      x: ray.origin.x + ray.direction.x * hitDist,
      y: ray.origin.y + ray.direction.y * hitDist,
      z: ray.origin.z + ray.direction.z * hitDist
    };

    return {
      hit: true,
      distance: hitDist,
      point: hitPoint,
      normal: hitNormal
    };
  }
}
