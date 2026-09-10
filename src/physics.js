/**
 * Bedrock-space swept AABB physics.
 *
 * Coordinate space follows Minecraft Bedrock conventions:
 *   +X East, -X West, +Y Up, -Y Down, +Z South, -Z North.
 *
 * A kinematic entity projected faster than ~1.5 blocks/tick can tunnel
 * through a thin static obstacle when only the discrete (endpoint) AABB
 * overlap is tested. This module implements swept AABB continuous collision
 * detection (CCD) using the slab method so the time of impact is resolved
 * along the swept volume instead of the frame-end position.
 */

export const EPSILON = 1e-9;

const AXIS_NAMES = [
  { d: 0, lo: 'west', hi: 'east' },
  { d: 1, lo: 'down', hi: 'up' },
  { d: 2, lo: 'north', hi: 'south' },
];

/**
 * Derive all 8 spatial bounding vertices of an AABB in Bedrock space.
 * Each vertex is labelled with its cardinal direction triple, e.g.
 * "east-up-south" for the (+X, +Y, +Z) corner.
 *
 * @param {{min:number[], max:number[]}} box AABB as [x0,y0,z0] / [x1,y1,z1].
 * @returns {{name:string, point:number[]}[]} 8 corner vertices.
 */
export function aabbVertices(box) {
  const [x0, y0, z0] = box.min;
  const [x1, y1, z1] = box.max;
  const axes = [
    [['west', x0], ['east', x1]],
    [['down', y0], ['up', y1]],
    [['north', z0], ['south', z1]],
  ];
  const vertices = [];
  for (const [xName, x] of axes[0]) {
    for (const [yName, y] of axes[1]) {
      for (const [zName, z] of axes[2]) {
        vertices.push({ name: `${xName}-${yName}-${zName}`, point: [x, y, z] });
      }
    }
  }
  return vertices;
}

/**
 * Axis direction names for the Bedrock coordinate space.
 * @returns {{axis: string, low: string, high: string}[]}
 */
export function axisNames() {
  return AXIS_NAMES.map(({ d, lo, hi }) => ({
    axis: ['x', 'y', 'z'][d],
    low: lo,
    high: hi,
  }));
}

/**
 * Swept (Minkowski) volume of a moving AABB over a full tick.
 * This is the union of every AABB position swept between t=0 and t=1.
 *
 * @param {{min:number[], max:number[]}} box AABB.
 * @param {number[]} velocity Blocks per tick, [vx, vy, vz].
 * @returns {{min:number[], max:number[]}} Swept union AABB.
 */
export function sweptVolume(box, velocity) {
  const min = box.min.map((v, d) => Math.min(v, v + velocity[d]));
  const max = box.max.map((v, d) => Math.max(v, v + velocity[d]));
  return { min, max };
}

/**
 * Discrete frame-end AABB overlap test. Returns true when the boxes overlap
 * at the end of the tick. This is the naive check that drops thin obstacles
 * for high-speed kinematics.
 */
export function discreteOverlap(a, b) {
  for (let d = 0; d < 3; d++) {
    if (a.max[d] <= b.min[d] || a.min[d] >= b.max[d]) return false;
  }
  return true;
}

/**
 * Swept AABB continuous collision detection (slab method).
 * Finds the first time in [0, 1] at which `box`, projected along `velocity`,
 * touches `staticBox`, together with the impact axis and surface normal.
 *
 * @param {{min:number[], max:number[]}} box Moving AABB.
 * @param {number[]} velocity Blocks per tick, [vx, vy, vz].
 * @param {{min:number[], max:number[]}} staticBox Static AABB obstacle.
 * @returns {{t:number, axis:number, normal:number, position:number[]} | null}
 *   Earliest hit within the tick, or null when no impact occurs.
 */
export function sweepAabb(box, velocity, staticBox) {
  let tEntry = -Infinity;
  let tExit = Infinity;
  let hitAxis = -1;
  let hitNormal = 0;

  for (let d = 0; d < 3; d++) {
    const v = velocity[d];
    const boxMin = box.min[d];
    const boxMax = box.max[d];
    const sMin = staticBox.min[d];
    const sMax = staticBox.max[d];

    if (Math.abs(v) < EPSILON) {
      if (boxMax <= sMin || boxMin >= sMax) return null;
      continue;
    }

    let t1 = (sMin - boxMax) / v;
    let t2 = (sMax - boxMin) / v;
    if (t1 > t2) {
      const tmp = t1;
      t1 = t2;
      t2 = tmp;
    }
    if (t1 > tEntry) {
      tEntry = t1;
      hitAxis = d;
      hitNormal = v > 0 ? -1 : 1;
    }
    tExit = Math.min(tExit, t2);
    if (tEntry > tExit) return null;
  }

  if (tEntry > 1 || tExit < 0) return null;

  const t = Math.max(0, tEntry);
  const position = box.min.map((m, d) => m + velocity[d] * t);
  return { t, axis: hitAxis, normal: hitNormal, position };
}

/**
 * High-speed kinematic projection with CCD. Moves `box` along `velocity`
 * for one tick against `obstacles`, stopping at the earliest impact so the
 * entity never ghosts through a wall.
 *
 * @param {{min:number[], max:number[]}} box Moving AABB.
 * @param {number[]} velocity Blocks per tick, [vx, vy, vz].
 * @param {{min:number[], max:number[]}[]} obstacles Static AABBs.
 * @returns {{position:number[], t:number, hit:{...}|null}}
 */
export function projectKinematic(box, velocity, obstacles) {
  let best = null;
  for (const obstacle of obstacles) {
    const hit = sweepAabb(box, velocity, obstacle);
    if (hit && (!best || hit.t < best.t)) best = hit;
  }
  if (!best) {
    return {
      position: box.min.map((m, d) => m + velocity[d]),
      t: 1,
      hit: null,
    };
  }
  return { position: best.position, t: best.t, hit: best };
}