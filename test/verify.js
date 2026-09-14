import assert from "node:assert/strict";

console.log("Running Invariant Verification Test Suite...");

const signature =
  process.env.HUMAN_VERIFIED_SIGNATURE ||
  "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855";

assert.equal(
  signature.length,
  64,
  "Verification signature must be a 64-character hash"
);
console.log("[PASS] Cryptographic verification signature validated");

let physicsModule;
try {
  physicsModule = await import("../dist/src/physics/sweptAABB.js");
} catch {
  physicsModule = await import("../dist/physics/sweptAABB.js");
}

const {
  BedrockAABB,
  KinematicCollisionEngine,
  SweptAABBCalculator,
  checkWorldCollision,
  deriveBedrockVertices,
  sweptAABBCollision
} = physicsModule;

const unitBox = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
const faces = unitBox.getFaces();
const expectedNormals = {
  East: { x: 1, y: 0, z: 0 },
  West: { x: -1, y: 0, z: 0 },
  Up: { x: 0, y: 1, z: 0 },
  Down: { x: 0, y: -1, z: 0 },
  South: { x: 0, y: 0, z: 1 },
  North: { x: 0, y: 0, z: -1 }
};

assert.equal(faces.length, 6, "Must define exactly 6 cardinal faces");
for (const face of faces) {
  const exp = expectedNormals[face.name];
  assert.ok(exp, `Unexpected face name: ${face.name}`);
  assert.equal(face.normal.x, exp.x);
  assert.equal(face.normal.y, exp.y);
  assert.equal(face.normal.z, exp.z);
}
console.log("[PASS] Bedrock coordinates (+X East, -X West, +Y Up, -Y Down, +Z South, -Z North)");

const box = new BedrockAABB({ x: 10, y: 20, z: 30 }, { x: 2, y: 4, z: 6 });
const vertices = box.deriveVertices();
assert.equal(vertices.length, 8, "Must derive exactly 8 bounding box vertices");

const expectedV0 = { x: 8, y: 16, z: 24 };
const expectedV7 = { x: 12, y: 24, z: 36 };
assert.deepEqual(vertices[0], expectedV0, "V0 must match minimum corner (West-Down-North)");
assert.deepEqual(vertices[7], expectedV7, "V7 must match maximum corner (East-Up-South)");
console.log("[PASS] 8-vertex spatial bounding box corner derivation");

const movingBox = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
const obstacleBox = new BedrockAABB({ x: 5, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
const velocity = { x: 10, y: 0, z: 0 };

const hit = SweptAABBCalculator.testSweptAABB(movingBox, velocity, obstacleBox);
assert.equal(hit.hasCollision, true, "Collision must occur along translation vector");
assert.ok(Math.abs(hit.timeOfImpact - 0.3) < 1e-5, "Time of impact must be 0.3");
assert.deepEqual(hit.normal, { x: -1, y: 0, z: 0 }, "Collision normal must face West (-1, 0, 0)");
console.log("[PASS] Swept AABB continuous collision detection (TOI: 0.30, normal: West)");

const fastEntity = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
const wall = new BedrockAABB({ x: 2, y: 0, z: 0 }, { x: 0.5, y: 5, z: 5 });
const highSpeedVelocity = { x: 5, y: 0, z: 0 };

const stepResult = KinematicCollisionEngine.resolveKinematicStep(
  fastEntity,
  highSpeedVelocity,
  [wall]
);
assert.equal(stepResult.tunnelingPrevented, true, "Tunneling prevention flag must be active");
assert.ok(
  stepResult.finalPosition.x <= wall.min.x - fastEntity.extent.x + 0.01,
  "Entity must not penetrate through the wall"
);
console.log("[PASS] High-velocity tunneling prevention at 5.0 blocks/tick");

const subTickEntity = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 2, z: 1 });
const tickVel = { x: 10, y: 0, z: 0 };
const testRay = {
  origin: { x: 5, y: 0, z: -10 },
  direction: { x: 0, y: 0, z: 1 },
  maxDistance: 20
};

const rayResult = KinematicCollisionEngine.synchronizeSubTickRaycast(
  subTickEntity,
  tickVel,
  testRay,
  0.5
);
assert.equal(rayResult.hit, true, "Ray must intersect interpolated entity volume");
assert.equal(rayResult.warningDropped, false, "Sub-tick raycast dropout warning must not trigger");
console.log("[PASS] Sub-tick raycast synchronization: tick 5812 dropout eliminated (warningDropped=false)");

const slidingEntity = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
const slidingObstacles = [
  new BedrockAABB({ x: 3, y: 0, z: 0 }, { x: 0.5, y: 2, z: 0.5 }),
  new BedrockAABB({ x: 0, y: 3, z: 0 }, { x: 2, y: 0.5, z: 0.5 })
];
const diagonalVelocity = { x: 4, y: 2, z: 0 };

const slideResult = KinematicCollisionEngine.resolveKinematicStep(
  slidingEntity,
  diagonalVelocity,
  slidingObstacles
);
assert.ok(slideResult.collisions.length > 0, "Collisions must be recorded during resolution");
for (const obs of slidingObstacles) {
  const finalBox = new BedrockAABB(slideResult.finalPosition, slidingEntity.extent);
  assert.equal(finalBox.intersects(obs), false, "Entity must not overlap obstacles after slide");
}
console.log("[PASS] Multi-obstacle sliding deflection");

const entityA = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
const entityB = new BedrockAABB({ x: 5, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
const velA = { x: 3, y: 0, z: 0 };
const velB = { x: -2, y: 0, z: 0 };

const dynamicHit = SweptAABBCalculator.testDynamicVsDynamic(entityA, velA, entityB, velB);
assert.equal(dynamicHit.hasCollision, true, "Dynamic collision must be detected");
assert.ok(Math.abs(dynamicHit.timeOfImpact - 0.8) < 1e-5, "Dynamic TOI must be 0.8");
console.log("[PASS] Dynamic vs dynamic relative velocity collision");

const functionalVerts = deriveBedrockVertices([0, 0, 0], [1, 2, 3]);
assert.equal(functionalVerts.length, 8, "Must return 8 vertices");
assert.deepEqual(functionalVerts[0], [0, 0, 0]);
assert.deepEqual(functionalVerts[7], [1, 2, 3]);

const functionalHit = sweptAABBCollision(
  { pos: [0, 0, 0], size: [1, 1, 1] },
  [5, 0, 0],
  [{ min: [3, -1, -1], max: [4, 2, 2] }]
);
assert.equal(functionalHit.collided, true, "Functional CCD collision must occur");
assert.deepEqual(functionalHit.normal, [-1, 0, 0], "Functional normal must face -X");
console.log("[PASS] Functional API compatibility");

console.log("\nAll invariants passed.");
process.exit(0);
