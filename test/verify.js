/**
 * Invariant verification suite for the Bedrock swept-AABB physics fix.
 *
 * Covers:
 *   - All 8 spatial bounding vertices in Bedrock space (+X East, +Y Up, +Z South).
 *   - Swept AABB continuous collision detection (slab method).
 *   - 1-tick kinematic ghost-teleportation / swept AABB dropout (> 1.5 blocks/tick).
 *
 * Run with: node test/verify.js
 */
import assert from 'node:assert/strict';
import {
  aabbVertices,
  axisNames,
  discreteOverlap,
  projectKinematic,
  sweepAabb,
  sweptVolume,
} from '../src/physics.js';

let passed = 0;

function test(name, fn) {
  try {
    fn();
    passed += 1;
    console.log(`  ✓ ${name}`);
  } catch (err) {
    console.error(`  ✗ ${name}`);
    throw err;
  }
}

const near = (a, b, eps = 1e-9) => Math.abs(a - b) <= eps;
const nearV = (a, b) => a.every((v, i) => near(v, b[i]));

console.log('Running Bedrock swept-AABB invariant verification suite...\n');

test('derives all 8 spatial bounding vertices in Bedrock space', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const vertices = aabbVertices(box);
  assert.equal(vertices.length, 8);

  const names = vertices.map((v) => v.name).sort();
  assert.deepEqual(names, [
    'east-down-north',
    'east-down-south',
    'east-up-north',
    'east-up-south',
    'west-down-north',
    'west-down-south',
    'west-up-north',
    'west-up-south',
  ]);

  for (const { name, point } of vertices) {
    assert.equal(point.length, 3);
    assert.ok(point.every((v) => v === 0 || v === 1), `${name} lies on a corner`);
  }
  const corners = new Set(vertices.map((v) => v.point.join(',')));
  assert.equal(corners.size, 8, 'vertices are the full 2^3 corner set');
  for (const [x, y, z] of [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [1, 1, 0], [1, 0, 1], [0, 1, 1], [1, 1, 1]]) {
    assert.ok(corners.has(`${x},${y},${z}`), `missing corner (${x},${y},${z})`);
  }
});

test('vertices match the Bedrock coordinate axes (+X East, +Y Up, +Z South)', () => {
  assert.deepEqual(axisNames(), [
    { axis: 'x', low: 'west', high: 'east' },
    { axis: 'y', low: 'down', high: 'up' },
    { axis: 'z', low: 'north', high: 'south' },
  ]);

  const box = { min: [2, 3, 4], max: [5, 7, 9] };
  const byName = Object.fromEntries(aabbVertices(box).map((v) => [v.name, v.point]));
  assert.deepEqual(byName['east-up-south'], [5, 7, 9]);
  assert.deepEqual(byName['west-down-north'], [2, 3, 4]);
  assert.deepEqual(byName['east-down-north'], [5, 3, 4]);
  assert.deepEqual(byName['west-up-south'], [2, 7, 9]);
});

test('sweptVolume is the union AABB of the swept motion', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const volume = sweptVolume(box, [2, 1, 1]);
  assert.deepEqual(volume, { min: [0, 0, 0], max: [3, 2, 2] });
});

test('high-speed kinematic (> 1.5 blocks/tick) tunnels a thin wall under discrete test', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [2.5, 0, 0];
  const wall = { min: [1.9, 0, 0], max: [2.0, 1, 1] };

  const end = { min: box.min.map((v, d) => v + velocity[d]), max: box.max.map((v, d) => v + velocity[d]) };
  assert.equal(discreteOverlap(end, wall), false, 'discrete endpoint check misses the wall');

  const hit = sweepAabb(box, velocity, wall);
  assert.ok(hit, 'swept CCD must detect the impact');
});

test('swept CCD catches the ghost-teleportation impact at the true time of contact', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [2.5, 0, 0];
  const wall = { min: [1.9, 0, 0], max: [2.0, 1, 1] };

  const hit = sweepAabb(box, velocity, wall);
  assert.ok(hit);
  assert.ok(near(hit.t, (1.9 - 1.0) / 2.5), `t = ${hit.t}, expected ${(1.9 - 1.0) / 2.5}`);
  assert.equal(hit.axis, 0, 'impact resolved on the +X axis');
  assert.equal(hit.normal, -1, 'surface normal opposes +X motion');
  assert.ok(near(hit.position[0], 0.9), `position x = ${hit.position[0]}, expected 0.9`);
  assert.ok(hit.position.every((v, d) => near(v, box.min[d] + velocity[d] * hit.t)));
});

test('swept CCD prevents penetration past the obstacle (no dropout)', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [4, 0, 0];
  const wall = { min: [1.5, 0, 0], max: [1.6, 1, 1] };

  const hit = sweepAabb(box, velocity, wall);
  assert.ok(hit);
  assert.ok(hit.t > 0 && hit.t < 1);
  assert.ok(hit.position[0] + 1 <= wall.min[0] + 1e-9, 'entity stops at the wall face');
});

test('no collision is reported for a clear path', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [0.5, 0, 0];
  const obstacle = { min: [2, 2, 2], max: [3, 3, 3] };
  assert.equal(sweepAabb(box, velocity, obstacle), null);
});

test('impact axis is the slab entered last', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [2, 1, 0];
  const obstacle = { min: [2.5, 0.2, 0], max: [3.5, 0.8, 1] };

  const hit = sweepAabb(box, velocity, obstacle);
  assert.ok(hit);
  assert.equal(hit.axis, 0, 'x-axis slab is entered last');
  assert.ok(near(hit.t, 0.75));
});

test('resting contact (starting overlap) resolves at t = 0', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [0, 0, 0];
  const obstacle = { min: [0.5, 0.5, 0.5], max: [1.5, 1.5, 1.5] };
  const hit = sweepAabb(box, velocity, obstacle);
  assert.ok(hit);
  assert.equal(hit.t, 0);
});

test('motion that already passed the obstacle does not retroactively collide', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [2, 0, 0];
  const obstacle = { min: [-3, 0, 0], max: [-2, 1, 1] };
  assert.equal(sweepAabb(box, velocity, obstacle), null);
});

test('projectKinematic stops at the earliest obstacle and skips missed ones', () => {
  const box = { min: [0, 0, 0], max: [1, 1, 1] };
  const velocity = [3, 0, 0];
  const far = { min: [5, 0, 0], max: [6, 1, 1] };
  const wall = { min: [1.8, 0, 0], max: [2.0, 1, 1] };

  const result = projectKinematic(box, velocity, [far, wall]);
  assert.ok(result.hit);
  assert.equal(result.hit.axis, 0);
  assert.ok(near(result.t, (1.8 - 1.0) / 3));
  assert.ok(result.position[0] + 1 <= wall.min[0] + 1e-9);

  const clear = projectKinematic(box, velocity, [far]);
  assert.equal(clear.hit, null);
  assert.ok(nearV(clear.position, [3, 0, 0]));
  assert.equal(clear.t, 1);
});

console.log(`\nAll ${passed} invariant checks passed.`);
process.exit(0);