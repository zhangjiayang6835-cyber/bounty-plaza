/**
 * Continuous Collision Detection (CCD) engine implementing swept AABB
 * and sub-tick raycast synchronization.
 */

import { BedrockFaceName, CollisionResultDef, RaycastResultDef, RayDef, RayHitDef, StepResultDef, Vector3D } from "./types.js";
import { BoundingBox, Vector3 } from "./BedrockAABB.js";

const EMPTY_VEC = new Vector3(0, 0, 0);

interface AxisTimeResult {
  disjoint: boolean;
  entryTime: number;
  exitTime: number;
  entryDist: number;
}

export class SweptAABBEngine {
  static readonly EPSILON = 1e-6;
  static readonly TUNNELING_THRESHOLD = 1.5;

  /**
   * Evaluates continuous swept collision between moving volume and obstacle.
   */
  static testSweptAABB(
    moving: BoundingBox,
    velocity: Vector3D,
    obstacle: BoundingBox,
  ): CollisionResultDef {
    const noHit: CollisionResultDef = {
      hasCollision: false,
      timeOfImpact: 1.0,
      normal: EMPTY_VEC,
      contactPoint: EMPTY_VEC,
      cardinalDirection: "",
    };

    const broadphase = moving.expand(velocity);
    if (!broadphase.intersects(obstacle)) {
      return noHit;
    }

    if (moving.intersects(obstacle)) {
      return {
        hasCollision: true,
        timeOfImpact: 0.0,
        normal: EMPTY_VEC,
        contactPoint: moving.center,
        cardinalDirection: "",
      };
    }

    const { disjoint, entryTimes, exitTimes, entryDists } = this.computeAxisTimes(
      moving,
      obstacle,
      velocity,
    );
    if (disjoint) {
      return noHit;
    }

    const entryTime = Math.max(entryTimes.x, entryTimes.y, entryTimes.z);
    const exitTime = Math.min(exitTimes.x, exitTimes.y, exitTimes.z);

    if (entryTime > exitTime || entryTime < 0.0 || entryTime > 1.0) {
      return noHit;
    }

    if (entryTimes.x < 0.0 && entryTimes.y < 0.0 && entryTimes.z < 0.0) {
      return noHit;
    }

    const { normal, cardinal } = this.determineSurfaceNormal(
      entryTime,
      entryTimes,
      entryDists,
    );
    const hitCenter = moving.center.add(new Vector3(velocity.x, velocity.y, velocity.z).scale(entryTime));
    const contactPoint = this.clampContactPoint(hitCenter, obstacle);

    return {
      hasCollision: true,
      timeOfImpact: entryTime,
      normal,
      contactPoint,
      cardinalDirection: cardinal,
    };
  }

  /**
   * Tests dynamic entity collision against another moving entity via relative velocity.
   */
  static testDynamicVsDynamic(
    boxA: BoundingBox,
    velA: Vector3D,
    boxB: BoundingBox,
    velB: Vector3D,
  ): CollisionResultDef {
    const relVel = new Vector3(velA.x - velB.x, velA.y - velB.y, velA.z - velB.z);
    return this.testSweptAABB(boxA, relVel, boxB);
  }

  /**
   * Resolves multi-obstacle sliding deflection along collision surface normals.
   */
  static resolveKinematicStep(
    entityBox: BoundingBox,
    velocity: Vector3D,
    obstacles: BoundingBox[],
  ): StepResultDef {
    let currentBox = entityBox;
    let remainingVel = new Vector3(velocity.x, velocity.y, velocity.z);
    let finalPosition = entityBox.center;
    const collectedCollisions: CollisionResultDef[] = [];

    const velocityMag = remainingVel.magnitude();
    const tunnelingRisk = velocityMag >= this.TUNNELING_THRESHOLD;

    for (let i = 0; i < 3; i++) {
      if (remainingVel.magnitude() < this.EPSILON) {
        break;
      }

      let earliestHit: CollisionResultDef | null = null;
      for (const obs of obstacles) {
        const hit = this.testSweptAABB(currentBox, remainingVel, obs);
        if (hit.hasCollision) {
          if (!earliestHit || hit.timeOfImpact < earliestHit.timeOfImpact) {
            earliestHit = hit;
          }
        }
      }

      if (!earliestHit) {
        finalPosition = currentBox.center.add(remainingVel);
        break;
      }

      collectedCollisions.push(earliestHit);
      const safeToi = Math.max(0, earliestHit.timeOfImpact - this.EPSILON);
      finalPosition = currentBox.center.add(remainingVel.scale(safeToi));
      currentBox = new BoundingBox(finalPosition, currentBox.extent);

      const remainingTime = 1.0 - earliestHit.timeOfImpact;
      const normalDot = remainingVel.dot(earliestHit.normal);
      const deflectedX = (remainingVel.x - normalDot * earliestHit.normal.x) * remainingTime;
      const deflectedY = (remainingVel.y - normalDot * earliestHit.normal.y) * remainingTime;
      const deflectedZ = (remainingVel.z - normalDot * earliestHit.normal.z) * remainingTime;
      remainingVel = new Vector3(deflectedX, deflectedY, deflectedZ);
    }

    return {
      finalPosition,
      finalVelocity: remainingVel,
      collisions: collectedCollisions,
      tunnelingPrevented: tunnelingRisk && collectedCollisions.length > 0,
    };
  }

  /**
   * Validates parametric raycast against tick-interpolated and swept bounding volumes.
   */
  static synchronizeSubTickRaycast(
    entityBox: BoundingBox,
    velocity: Vector3D,
    ray: RayDef,
    subTickDelta: number = 0.5,
    tick: number = 4192,
  ): RaycastResultDef {
    const clampedDelta = Math.max(0, Math.min(1, subTickDelta));
    const velVec = new Vector3(velocity.x, velocity.y, velocity.z);
    const interpolatedCenter = entityBox.center.add(velVec.scale(clampedDelta));
    const interpolatedBox = new BoundingBox(interpolatedCenter, entityBox.extent);

    const interRes = this.intersectRayAABB(ray, interpolatedBox);
    if (interRes.hit) {
      return {
        hit: true,
        distance: interRes.distance,
        subTickFraction: clampedDelta,
        point: interRes.point,
        normal: interRes.normal,
        warningMissResolved: true,
        tick,
      };
    }

    const sweptBox = entityBox.expand(velocity);
    const sweptRes = this.intersectRayAABB(ray, sweptBox);
    if (sweptRes.hit) {
      return {
        hit: true,
        distance: sweptRes.distance,
        subTickFraction: clampedDelta,
        point: sweptRes.point,
        normal: sweptRes.normal,
        warningMissResolved: true,
        tick,
      };
    }

    return {
      hit: false,
      distance: Infinity,
      subTickFraction: clampedDelta,
      point: EMPTY_VEC,
      normal: EMPTY_VEC,
      warningMissResolved: false,
      tick,
    };
  }

  /**
   * Tests parametric ray intersection against stationary bounding volume.
   */
  static intersectRayAABB(ray: RayDef, box: BoundingBox): RayHitDef {
    let tMin = 0.0;
    let tMax = ray.maxDistance;
    let hitNormal = EMPTY_VEC;

    const slabs = [
      { origin: ray.origin.x, dir: ray.direction.x, minB: box.minPoint.x, maxB: box.maxPoint.x, posNorm: new Vector3(1, 0, 0) },
      { origin: ray.origin.y, dir: ray.direction.y, minB: box.minPoint.y, maxB: box.maxPoint.y, posNorm: new Vector3(0, 1, 0) },
      { origin: ray.origin.z, dir: ray.direction.z, minB: box.minPoint.z, maxB: box.maxPoint.z, posNorm: new Vector3(0, 0, 1) },
    ];

    for (const slab of slabs) {
      const slabRes = this.testSlab(slab.origin, slab.dir, slab.minB, slab.maxB, slab.posNorm);
      if (!slabRes.valid) {
        return { hit: false, distance: Infinity, point: EMPTY_VEC, normal: EMPTY_VEC };
      }
      if (slabRes.t1 > tMin) {
        tMin = slabRes.t1;
        hitNormal = slabRes.normal;
      }
      tMax = Math.min(tMax, slabRes.t2);
      if (tMin > tMax) {
        return { hit: false, distance: Infinity, point: EMPTY_VEC, normal: EMPTY_VEC };
      }
    }

    if (tMin > ray.maxDistance || tMax < 0.0) {
      return { hit: false, distance: Infinity, point: EMPTY_VEC, normal: EMPTY_VEC };
    }

    const dist = Math.max(0, tMin);
    const hitPoint = new Vector3(
      ray.origin.x + ray.direction.x * dist,
      ray.origin.y + ray.direction.y * dist,
      ray.origin.z + ray.direction.z * dist,
    );

    return {
      hit: true,
      distance: dist,
      point: hitPoint,
      normal: hitNormal,
    };
  }

  private static testSlab(
    origin: number,
    dir: number,
    minB: number,
    maxB: number,
    posNorm: Vector3,
  ): { valid: boolean; t1: number; t2: number; normal: Vector3 } {
    const negNorm = posNorm.scale(-1);
    if (Math.abs(dir) < this.EPSILON) {
      if (origin < minB || origin > maxB) {
        return { valid: false, t1: 0, t2: 0, normal: EMPTY_VEC };
      }
      return { valid: true, t1: -Infinity, t2: Infinity, normal: EMPTY_VEC };
    }

    const time1 = (minB - origin) / dir;
    const time2 = (maxB - origin) / dir;
    if (time1 > time2) {
      return { valid: true, t1: time2, t2: time1, normal: posNorm };
    }
    return { valid: true, t1: time1, t2: time2, normal: negNorm };
  }

  private static computeSingleAxis(
    minM: number,
    maxM: number,
    minO: number,
    maxO: number,
    vel: number,
  ): AxisTimeResult {
    const entryD = vel > 0 ? minO - maxM : maxO - minM;
    const exitD = vel > 0 ? maxO - minM : minO - maxM;

    if (Math.abs(vel) < this.EPSILON) {
      if (maxM <= minO || minM >= maxO) {
        return { disjoint: true, entryTime: 0, exitTime: 0, entryDist: 0 };
      }
      return { disjoint: false, entryTime: -Infinity, exitTime: Infinity, entryDist: 0 };
    }

    return {
      disjoint: false,
      entryTime: entryD / vel,
      exitTime: exitD / vel,
      entryDist: entryD,
    };
  }

  private static computeAxisTimes(
    moving: BoundingBox,
    obstacle: BoundingBox,
    velocity: Vector3D,
  ): { disjoint: boolean; entryTimes: Vector3; exitTimes: Vector3; entryDists: Vector3 } {
    const resX = this.computeSingleAxis(moving.minPoint.x, moving.maxPoint.x, obstacle.minPoint.x, obstacle.maxPoint.x, velocity.x);
    if (resX.disjoint) {
      return { disjoint: true, entryTimes: EMPTY_VEC, exitTimes: EMPTY_VEC, entryDists: EMPTY_VEC };
    }

    const resY = this.computeSingleAxis(moving.minPoint.y, moving.maxPoint.y, obstacle.minPoint.y, obstacle.maxPoint.y, velocity.y);
    if (resY.disjoint) {
      return { disjoint: true, entryTimes: EMPTY_VEC, exitTimes: EMPTY_VEC, entryDists: EMPTY_VEC };
    }

    const resZ = this.computeSingleAxis(moving.minPoint.z, moving.maxPoint.z, obstacle.minPoint.z, obstacle.maxPoint.z, velocity.z);
    if (resZ.disjoint) {
      return { disjoint: true, entryTimes: EMPTY_VEC, exitTimes: EMPTY_VEC, entryDists: EMPTY_VEC };
    }

    return {
      disjoint: false,
      entryTimes: new Vector3(resX.entryTime, resY.entryTime, resZ.entryTime),
      exitTimes: new Vector3(resX.exitTime, resY.exitTime, resZ.exitTime),
      entryDists: new Vector3(resX.entryDist, resY.entryDist, resZ.entryDist),
    };
  }

  private static determineSurfaceNormal(
    entryTime: number,
    entryTimes: Vector3,
    entryDists: Vector3,
  ): { normal: Vector3; cardinal: BedrockFaceName } {
    if (entryTime === entryTimes.x) {
      if (entryDists.x < 0) {
        return { normal: new Vector3(1, 0, 0), cardinal: "East" };
      }
      return { normal: new Vector3(-1, 0, 0), cardinal: "West" };
    }
    if (entryTime === entryTimes.y) {
      if (entryDists.y < 0) {
        return { normal: new Vector3(0, 1, 0), cardinal: "Up" };
      }
      return { normal: new Vector3(0, -1, 0), cardinal: "Down" };
    }
    if (entryDists.z < 0) {
      return { normal: new Vector3(0, 0, 1), cardinal: "South" };
    }
    return { normal: new Vector3(0, 0, -1), cardinal: "North" };
  }

  private static clampContactPoint(hitCenter: Vector3, obstacle: BoundingBox): Vector3 {
    const cx = Math.max(obstacle.minPoint.x, Math.min(obstacle.maxPoint.x, hitCenter.x));
    const cy = Math.max(obstacle.minPoint.y, Math.min(obstacle.maxPoint.y, hitCenter.y));
    const cz = Math.max(obstacle.minPoint.z, Math.min(obstacle.maxPoint.z, hitCenter.z));
    return new Vector3(cx, cy, cz);
  }
}
