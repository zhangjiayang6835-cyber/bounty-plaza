import { BedrockAABB } from "./BedrockAABB.js";
import { SweptAABB } from "./SweptAABB.js";
import {
  CollisionResult,
  Ray,
  RaycastResult,
  StepResolutionResult,
  Vector3
} from "./types.js";

/**
 * Resolves kinematic entity motion, prevents tunneling, and synchronizes sub-tick raycasts.
 */
export class KinematicCollisionEngine {
  private static readonly EPSILON = 1e-8;

  /**
   * Resolves a kinematic displacement step against multiple obstacles.
   * @param entity Moving entity bounding box.
   * @param velocity Desired translation displacement for current tick.
   * @param obstacles Collection of solid obstacle bounding boxes.
   * @param maxIterations Maximum collision sliding iterations.
   * @returns Resolved position and collision history.
   */
  public static resolveKinematicStep(
    entity: BedrockAABB,
    velocity: Vector3,
    obstacles: BedrockAABB[],
    maxIterations = 4
  ): StepResolutionResult {
    let currentBox = entity;
    let remainingVel: Vector3 = { ...velocity };
    const collisions: CollisionResult[] = [];
    const speed = Math.hypot(velocity.x, velocity.y, velocity.z);
    const rapidMotion = speed > 1.5;
    let tunnelingPrevented = false;

    for (let iter = 0; iter < maxIterations; iter++) {
      const remSpeed = Math.hypot(remainingVel.x, remainingVel.y, remainingVel.z);
      if (remSpeed < this.EPSILON) {
        break;
      }

      let earliestHit: CollisionResult | null = null;
      for (const obstacle of obstacles) {
        const hit = SweptAABB.testSweptAABB(currentBox, remainingVel, obstacle);
        if (hit.hasCollision) {
          if (!earliestHit || hit.timeOfImpact < earliestHit.timeOfImpact) {
            earliestHit = hit;
          }
        }
      }

      if (!earliestHit) {
        currentBox = currentBox.translate(remainingVel);
        remainingVel = { x: 0, y: 0, z: 0 };
        break;
      }

      collisions.push(earliestHit);
      if (rapidMotion) {
        tunnelingPrevented = true;
      }

      const advanceFraction = Math.max(0, earliestHit.timeOfImpact - 0.001);
      const advanceVec: Vector3 = {
        x: remainingVel.x * advanceFraction,
        y: remainingVel.y * advanceFraction,
        z: remainingVel.z * advanceFraction
      };
      currentBox = currentBox.translate(advanceVec);

      const remainingTime = 1.0 - earliestHit.timeOfImpact;
      const normalDot =
        remainingVel.x * earliestHit.normal.x +
        remainingVel.y * earliestHit.normal.y +
        remainingVel.z * earliestHit.normal.z;

      remainingVel = {
        x: (remainingVel.x - normalDot * earliestHit.normal.x) * remainingTime,
        y: (remainingVel.y - normalDot * earliestHit.normal.y) * remainingTime,
        z: (remainingVel.z - normalDot * earliestHit.normal.z) * remainingTime
      };
    }

    return {
      finalPosition: { ...currentBox.center },
      collisions,
      tunnelingPrevented,
      remainingVelocity: remainingVel
    };
  }

  /**
   * Synchronizes sub-tick raycasts against interpolated bounding boxes.
   * @param entity Entity bounding box at tick boundary.
   * @param velocity Entity displacement velocity during tick.
   * @param ray Target raycast definition.
   * @param subTickDelta Sub-tick interpolation fraction [0, 1].
   * @returns Sub-tick synchronized raycast result.
   */
  public static synchronizeSubTickRaycast(
    entity: BedrockAABB,
    velocity: Vector3,
    ray: Ray,
    subTickDelta = 0.5
  ): RaycastResult {
    const clampedDelta = Math.max(0.0, Math.min(1.0, subTickDelta));
    const interpolatedCenter: Vector3 = {
      x: entity.center.x + velocity.x * clampedDelta,
      y: entity.center.y + velocity.y * clampedDelta,
      z: entity.center.z + velocity.z * clampedDelta
    };
    const interpolatedBox = new BedrockAABB(interpolatedCenter, entity.extent);

    const directHit = this.intersectRayAABB(ray, interpolatedBox);
    if (directHit.hit) {
      return {
        hit: true,
        distance: directHit.distance,
        subTickFraction: clampedDelta,
        point: directHit.point,
        normal: directHit.normal,
        warningDropped: false
      };
    }

    const sweptBox = entity.expand(velocity);
    const sweptHit = this.intersectRayAABB(ray, sweptBox);
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
   * Computes intersection between ray and stationary Bedrock bounding box.
   * @param ray Target ray.
   * @param box Target bounding box.
   * @returns Ray intersection outcome.
   */
  public static intersectRayAABB(
    ray: Ray,
    box: BedrockAABB
  ): { hit: boolean; distance: number; point: Vector3; normal: Vector3 } {
    let tmin = 0.0;
    let tmax = ray.maxDistance;
    let hitNormal: Vector3 = { x: 0, y: 0, z: 0 };

    const slabs = [
      { origin: ray.origin.x, dir: ray.direction.x, min: box.min.x, max: box.max.x, normPos: { x: 1, y: 0, z: 0 } },
      { origin: ray.origin.y, dir: ray.direction.y, min: box.min.y, max: box.max.y, normPos: { x: 0, y: 1, z: 0 } },
      { origin: ray.origin.z, dir: ray.direction.z, min: box.min.z, max: box.max.z, normPos: { x: 0, y: 0, z: 1 } }
    ];

    for (const slab of slabs) {
      const normNeg: Vector3 = { x: -slab.normPos.x, y: -slab.normPos.y, z: -slab.normPos.z };
      if (Math.abs(slab.dir) < this.EPSILON) {
        if (slab.origin < slab.min || slab.origin > slab.max) {
          return { hit: false, distance: Infinity, point: { x: 0, y: 0, z: 0 }, normal: { x: 0, y: 0, z: 0 } };
        }
      } else {
        let t1 = (slab.min - slab.origin) / slab.dir;
        let t2 = (slab.max - slab.origin) / slab.dir;
        let nearNormal = normNeg;

        if (t1 > t2) {
          const temp = t1;
          t1 = t2;
          t2 = temp;
          nearNormal = slab.normPos;
        }

        if (t1 > tmin) {
          tmin = t1;
          hitNormal = nearNormal;
        }
        tmax = Math.min(tmax, t2);

        if (tmin > tmax) {
          return { hit: false, distance: Infinity, point: { x: 0, y: 0, z: 0 }, normal: { x: 0, y: 0, z: 0 } };
        }
      }
    }

    if (tmin > ray.maxDistance || tmax < 0.0) {
      return { hit: false, distance: Infinity, point: { x: 0, y: 0, z: 0 }, normal: { x: 0, y: 0, z: 0 } };
    }

    const dist = Math.max(0.0, tmin);
    const point: Vector3 = {
      x: ray.origin.x + ray.direction.x * dist,
      y: ray.origin.y + ray.direction.y * dist,
      z: ray.origin.z + ray.direction.z * dist
    };

    return { hit: true, distance: dist, point, normal: hitNormal };
  }
}
