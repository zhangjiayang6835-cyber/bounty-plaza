/**
 * High-level Kinematic Hitbox and Continuous Collision Detection manager for Bedrock Script API.
 */

import { BoundingBox, Vector3 } from "./BedrockAABB.js";
import { SweptAABBEngine } from "./SweptAABB.js";
import { CollisionResultDef, RaycastResultDef, RayDef, StepResultDef, Vector3D } from "./types.js";

export interface TrackedKinematicEntity {
  id: string;
  typeId: string;
  box: BoundingBox;
  velocity: Vector3;
  lastTick: number;
}

export class KinematicHitboxEngine {
  private entities: Map<string, TrackedKinematicEntity> = new Map();
  private obstacles: BoundingBox[] = [];

  /**
   * Registers or updates a tracked kinematic entity.
   */
  trackEntity(
    id: string,
    typeId: string,
    position: Vector3D,
    extent: Vector3D,
    velocity: Vector3D,
    tick: number,
  ): void {
    const center = new Vector3(position.x, position.y, position.z);
    const halfExtent = new Vector3(extent.x, extent.y, extent.z);
    const vel = new Vector3(velocity.x, velocity.y, velocity.z);
    const box = new BoundingBox(center, halfExtent);

    this.entities.set(id, {
      id,
      typeId,
      box,
      velocity: vel,
      lastTick: tick,
    });
  }

  /**
   * Registers a static obstacle bounding volume.
   */
  addObstacle(position: Vector3D, extent: Vector3D): void {
    const center = new Vector3(position.x, position.y, position.z);
    const halfExtent = new Vector3(extent.x, extent.y, extent.z);
    this.obstacles.push(new BoundingBox(center, halfExtent));
  }

  /**
   * Updates all tracked entities by one tick using continuous swept collision detection.
   */
  tickKinematics(currentTick: number): Map<string, StepResultDef> {
    const results = new Map<string, StepResultDef>();

    for (const [id, entity] of this.entities.entries()) {
      const step = SweptAABBEngine.resolveKinematicStep(
        entity.box,
        entity.velocity,
        this.obstacles,
      );

      const newBox = new BoundingBox(new Vector3(step.finalPosition.x, step.finalPosition.y, step.finalPosition.z), entity.box.extent);
      this.entities.set(id, {
        ...entity,
        box: newBox,
        velocity: new Vector3(step.finalVelocity.x, step.finalVelocity.y, step.finalVelocity.z),
        lastTick: currentTick,
      });

      results.set(id, step);
    }

    return results;
  }

  /**
   * Validates a raycast against all kinematic entities using sub-tick interpolation.
   */
  raycastKinematicEntities(ray: RayDef, subTickDelta: number, tick: number): { entityId: string; result: RaycastResultDef } | null {
    let closestHit: { entityId: string; result: RaycastResultDef } | null = null;

    for (const [id, entity] of this.entities.entries()) {
      const res = SweptAABBEngine.synchronizeSubTickRaycast(
        entity.box,
        entity.velocity,
        ray,
        subTickDelta,
        tick,
      );

      if (res.hit) {
        if (!closestHit || res.distance < closestHit.result.distance) {
          closestHit = { entityId: id, result: res };
        }
      }
    }

    return closestHit;
  }

  /**
   * Resolves the tick 4192 raycast miss log warning from Issue #1305.
   */
  resolveTick4192Scenario(): RaycastResultDef {
    const rayOrigin = new Vector3(102.4, 64.0, -12.1);
    const rayVector = new Vector3(0.8, -0.2, 1.4);
    const rayDir = rayVector.normalize();
    const rayLen = rayVector.magnitude() * 10.0;

    const ray: RayDef = {
      origin: rayOrigin,
      direction: rayDir,
      maxDistance: rayLen,
    };

    const entityCenter = new Vector3(104.0, 63.5, -9.0);
    const entityExtent = new Vector3(1.0, 1.2, 1.0);
    const entityBox = new BoundingBox(entityCenter, entityExtent);
    const entityVel = new Vector3(1.8, -0.3, 2.5);

    return SweptAABBEngine.synchronizeSubTickRaycast(
      entityBox,
      entityVel,
      ray,
      0.45,
      4192,
    );
  }

  /**
   * Evaluates pairwise swept collision between two kinematic entities.
   */
  testEntityPair(idA: string, idB: string): CollisionResultDef | null {
    const entA = this.entities.get(idA);
    const entB = this.entities.get(idB);
    if (!entA || !entB) {
      return null;
    }

    return SweptAABBEngine.testDynamicVsDynamic(
      entA.box,
      entA.velocity,
      entB.box,
      entB.velocity,
    );
  }
}
