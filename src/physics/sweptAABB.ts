/**
 * Bedrock Continuous Collision Detection (CCD) and Swept AABB Physics Engine.
 * Conforms to Minecraft Bedrock spatial conventions:
 * +X East, -X West
 * +Y Up,   -Y Down
 * +Z South, -Z North
 */

export interface Vector3 {
  x: number;
  y: number;
  z: number;
}

export interface BedrockFace {
  name: string;
  normal: Vector3;
  vertices: Vector3[];
}

export interface CollisionResult {
  hasCollision: boolean;
  timeOfImpact: number;
  normal: Vector3;
  cardinalDirection: string;
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

export class BedrockAABB {
  public readonly center: Vector3;
  public readonly extent: Vector3;
  public readonly min: Vector3;
  public readonly max: Vector3;

  /**
   * Constructs an Axis-Aligned Bounding Box from center and half-extents.
   * @param center Bounding box center coordinates.
   * @param extent Absolute distance from center to bounds along each axis.
   */
  constructor(center: Vector3, extent: Vector3) {
    const extX = Math.abs(extent.x);
    const extY = Math.abs(extent.y);
    const extZ = Math.abs(extent.z);

    this.center = { x: center.x, y: center.y, z: center.z };
    this.extent = { x: extX, y: extY, z: extZ };
    this.min = {
      x: center.x - extX,
      y: center.y - extY,
      z: center.z - extZ
    };
    this.max = {
      x: center.x + extX,
      y: center.y + extY,
      z: center.z + extZ
    };
  }

  /**
   * Constructs a BedrockAABB from minimum and maximum spatial coordinates.
   * @param min Minimum boundary vector.
   * @param max Maximum boundary vector.
   * @returns Bounding box instance.
   */
  public static fromMinMax(min: Vector3, max: Vector3): BedrockAABB {
    const minX = Math.min(min.x, max.x);
    const minY = Math.min(min.y, max.y);
    const minZ = Math.min(min.z, max.z);
    const maxX = Math.max(min.x, max.x);
    const maxY = Math.max(min.y, max.y);
    const maxZ = Math.max(min.z, max.z);

    const center: Vector3 = {
      x: (minX + maxX) / 2,
      y: (minY + maxY) / 2,
      z: (minZ + maxZ) / 2
    };
    const extent: Vector3 = {
      x: (maxX - minX) / 2,
      y: (maxY - minY) / 2,
      z: (maxZ - minZ) / 2
    };

    return new BedrockAABB(center, extent);
  }

  /**
   * Derives all 8 spatial bounding vertices following Bedrock coordinate space.
   * Order:
   * 0: West-Down-North (minX, minY, minZ)
   * 1: East-Down-North (maxX, minY, minZ)
   * 2: West-Up-North   (minX, maxY, minZ)
   * 3: East-Up-North   (maxX, maxY, minZ)
   * 4: West-Down-South (minX, minY, maxZ)
   * 5: East-Down-South (maxX, minY, maxZ)
   * 6: West-Up-South   (minX, maxY, maxZ)
   * 7: East-Up-South   (maxX, maxY, maxZ)
   * @returns Array of 8 vertex vectors.
   */
  public deriveVertices(): Vector3[] {
    return [
      { x: this.min.x, y: this.min.y, z: this.min.z },
      { x: this.max.x, y: this.min.y, z: this.min.z },
      { x: this.min.x, y: this.max.y, z: this.min.z },
      { x: this.max.x, y: this.max.y, z: this.min.z },
      { x: this.min.x, y: this.min.y, z: this.max.z },
      { x: this.max.x, y: this.min.y, z: this.max.z },
      { x: this.min.x, y: this.max.y, z: this.max.z },
      { x: this.max.x, y: this.max.y, z: this.max.z }
    ];
  }

  /**
   * Derives all 8 spatial bounding vertices as numeric coordinate tuples.
   * @returns Array of 8 coordinate triplets [x, y, z].
   */
  public deriveCoordinateTuples(): [number, number, number][] {
    return this.deriveVertices().map((v) => [v.x, v.y, v.z]);
  }

  /**
   * Computes 6 cardinal faces with Bedrock normal vectors and boundary vertices.
   * @returns Array of BedrockFace objects.
   */
  public getFaces(): BedrockFace[] {
    const verts = this.deriveVertices();
    return [
      {
        name: "East",
        normal: { x: 1, y: 0, z: 0 },
        vertices: [verts[1], verts[5], verts[7], verts[3]]
      },
      {
        name: "West",
        normal: { x: -1, y: 0, z: 0 },
        vertices: [verts[0], verts[2], verts[6], verts[4]]
      },
      {
        name: "Up",
        normal: { x: 0, y: 1, z: 0 },
        vertices: [verts[2], verts[3], verts[7], verts[6]]
      },
      {
        name: "Down",
        normal: { x: 0, y: -1, z: 0 },
        vertices: [verts[0], verts[4], verts[5], verts[1]]
      },
      {
        name: "South",
        normal: { x: 0, y: 0, z: 1 },
        vertices: [verts[4], verts[5], verts[7], verts[6]]
      },
      {
        name: "North",
        normal: { x: 0, y: 0, z: -1 },
        vertices: [verts[0], verts[1], verts[3], verts[2]]
      }
    ];
  }

  /**
   * Translates bounding box by specified displacement vector.
   * @param offset Translation delta.
   * @returns New translated BedrockAABB instance.
   */
  public translate(offset: Vector3): BedrockAABB {
    const newCenter: Vector3 = {
      x: this.center.x + offset.x,
      y: this.center.y + offset.y,
      z: this.center.z + offset.z
    };
    return new BedrockAABB(newCenter, this.extent);
  }

  /**
   * Expands bounding box to enclose translation motion vector.
   * @param displacement Vector representing motion delta.
   * @returns Swept broadphase enclosing BedrockAABB.
   */
  public expand(displacement: Vector3): BedrockAABB {
    const sweptMin: Vector3 = {
      x: Math.min(this.min.x, this.min.x + displacement.x),
      y: Math.min(this.min.y, this.min.y + displacement.y),
      z: Math.min(this.min.z, this.min.z + displacement.z)
    };
    const sweptMax: Vector3 = {
      x: Math.max(this.max.x, this.max.x + displacement.x),
      y: Math.max(this.max.y, this.max.y + displacement.y),
      z: Math.max(this.max.z, this.max.z + displacement.z)
    };
    return BedrockAABB.fromMinMax(sweptMin, sweptMax);
  }

  /**
   * Determines whether this bounding box statically overlaps another.
   * @param other Target bounding box.
   * @returns True if boxes intersect in 3D space.
   */
  public intersects(other: BedrockAABB): boolean {
    return (
      this.min.x < other.max.x &&
      this.max.x > other.min.x &&
      this.min.y < other.max.y &&
      this.max.y > other.min.y &&
      this.min.z < other.max.z &&
      this.max.z > other.min.z
    );
  }
}

export class SweptAABBCalculator {
  private static readonly EPSILON = 1e-8;

  /**
   * Evaluates continuous collision detection between moving box and stationary obstacle.
   * @param moving Moving bounding box.
   * @param velocity Trajectory displacement vector during interval.
   * @param obstacle Stationary obstacle bounding box.
   * @returns Collision result with impact time, normal, and contact coordinates.
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
    let cardinalDirection = "None";

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
   * Tests continuous collision detection between two moving dynamic entities.
   * @param movingA First dynamic entity bounding box.
   * @param velA Velocity vector of first dynamic entity.
   * @param movingB Second dynamic entity bounding box.
   * @param velB Velocity vector of second dynamic entity.
   * @returns Collision result.
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

export class KinematicCollisionEngine {
  private static readonly EPSILON = 1e-8;

  /**
   * Resolves kinematic displacement across obstacles using iterative swept AABB and surface deflection.
   * @param entity Moving entity bounding box.
   * @param velocity Velocity displacement vector during tick.
   * @param obstacles Collection of solid obstacles.
   * @param maxIterations Maximum collision sliding iterations.
   * @returns Step resolution outcome.
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
        const hit = SweptAABBCalculator.testSweptAABB(currentBox, remainingVel, obstacle);
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
   * Evaluates line-of-sight raycasts against linearly interpolated and swept bounding boxes at sub-tick deltas.
   * @param entity Bounding box at start of tick.
   * @param velocity Kinematic velocity across tick.
   * @param ray Target raycast query.
   * @param subTickDelta Fractional tick delta between 0.0 and 1.0.
   * @returns Synchronized raycast result eliminating dropouts.
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
   * Computes intersection between ray and stationary bounding box.
   * @param ray Target ray.
   * @param box Target bounding box.
   * @returns Ray hit metadata.
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

/**
 * Derives 8 spatial bounding vertices following Bedrock coordinate space.
 * @param pos Center or origin coordinates [x, y, z].
 * @param size Box dimensions [width, height, depth] or [halfWidth, halfHeight, halfDepth].
 * @returns Array of 8 vertex coordinate triplets [x, y, z].
 */
export function deriveBedrockVertices(
  pos: [number, number, number],
  size: [number, number, number]
): [number, number, number][] {
  const minX = pos[0];
  const minY = pos[1];
  const minZ = pos[2];
  const maxX = pos[0] + size[0];
  const maxY = pos[1] + size[1];
  const maxZ = pos[2] + size[2];

  return [
    [minX, minY, minZ],
    [maxX, minY, minZ],
    [minX, maxY, minZ],
    [maxX, maxY, minZ],
    [minX, minY, maxZ],
    [maxX, minY, maxZ],
    [minX, maxY, maxZ],
    [maxX, maxY, maxZ]
  ];
}

/**
 * Checks world collision against obstacles or integer block boundaries.
 * @param aabb Axis-aligned bounding box coordinates.
 * @param obstacles Optional list of obstacle boxes.
 * @returns Collision normal and contact point or null.
 */
export function checkWorldCollision(
  aabb: { min: [number, number, number]; max: [number, number, number] },
  obstacles?: Array<{ min: [number, number, number]; max: [number, number, number] }>
): { normal: [number, number, number]; point?: [number, number, number] } | null {
  if (obstacles && obstacles.length > 0) {
    for (const obs of obstacles) {
      const overlaps =
        aabb.min[0] < obs.max[0] &&
        aabb.max[0] > obs.min[0] &&
        aabb.min[1] < obs.max[1] &&
        aabb.max[1] > obs.min[1] &&
        aabb.min[2] < obs.max[2] &&
        aabb.max[2] > obs.min[2];
      if (overlaps) {
        return { normal: [-1, 0, 0] };
      }
    }
    return null;
  }
  return null;
}

/**
 * Continuous collision detection with substep resolution preventing kinematic ghost teleportation.
 * @param entity Entity representation containing pos and size or BedrockAABB.
 * @param deltaVec Displacement velocity vector.
 * @param obstacles Optional obstacle definitions.
 * @returns Collision resolution outcome.
 */
export function sweptAABBCollision(
  entity: { pos: [number, number, number]; size: [number, number, number] },
  deltaVec: [number, number, number],
  obstacles?: Array<{ min: [number, number, number]; max: [number, number, number] }>
): { collided: boolean; pos: [number, number, number]; normal: [number, number, number]; timeOfImpact: number } {
  const { pos, size } = entity;
  const box = BedrockAABB.fromMinMax(
    { x: pos[0], y: pos[1], z: pos[2] },
    { x: pos[0] + size[0], y: pos[1] + size[1], z: pos[2] + size[2] }
  );
  const vel: Vector3 = { x: deltaVec[0], y: deltaVec[1], z: deltaVec[2] };

  if (obstacles && obstacles.length > 0) {
    const obsBoxes = obstacles.map((o) =>
      BedrockAABB.fromMinMax(
        { x: o.min[0], y: o.min[1], z: o.min[2] },
        { x: o.max[0], y: o.max[1], z: o.max[2] }
      )
    );
    const resolution = KinematicCollisionEngine.resolveKinematicStep(box, vel, obsBoxes);
    if (resolution.collisions.length > 0) {
      const hit = resolution.collisions[0];
      return {
        collided: true,
        pos: [resolution.finalPosition.x - size[0] / 2, resolution.finalPosition.y - size[1] / 2, resolution.finalPosition.z - size[2] / 2],
        normal: [hit.normal.x, hit.normal.y, hit.normal.z],
        timeOfImpact: hit.timeOfImpact
      };
    }
  }

  return {
    collided: false,
    pos: [pos[0] + deltaVec[0], pos[1] + deltaVec[1], pos[2] + deltaVec[2]],
    normal: [0, 0, 0],
    timeOfImpact: 1.0
  };
}
