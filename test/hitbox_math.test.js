/**
 * Node.js test suite for Bedrock Hitbox Math and Continuous Collision Detection.
 */

import test from "node:test";
import assert from "node:assert/strict";

import {
  BoundingBox,
  KinematicHitboxEngine,
  SweptAABBEngine,
  Vector3,
} from "../scripts/hitbox_math/index.js";

test("Vector3 arithmetic and Bedrock coordinate conventions", () => {
  const v1 = new Vector3(1, 2, 3);
  const v2 = new Vector3(4, 5, 6);

  const sum = v1.add(v2);
  assert.equal(sum.x, 5);
  assert.equal(sum.y, 7);
  assert.equal(sum.z, 9);

  const sub = v2.subtract(v1);
  assert.equal(sub.x, 3);
  assert.equal(sub.y, 3);
  assert.equal(sub.z, 3);

  const scaled = v1.scale(2);
  assert.equal(scaled.x, 2);
  assert.equal(scaled.y, 4);
  assert.equal(scaled.z, 6);

  assert.equal(v1.dot(v2), 32);

  const cross = new Vector3(1, 0, 0).cross(new Vector3(0, 1, 0));
  assert.equal(cross.x, 0);
  assert.equal(cross.y, 0);
  assert.equal(cross.z, 1);

  assert.equal(new Vector3(3, 4, 0).magnitude(), 5);
  const norm = new Vector3(0, 10, 0).normalize();
  assert.equal(norm.x, 0);
  assert.equal(norm.y, 1);
  assert.equal(norm.z, 0);
});

test("BoundingBox eight corner vertex derivation and cardinal faces", () => {
  const box = new BoundingBox(new Vector3(10, 20, 30), new Vector3(1, 2, 3));
  const vertices = box.deriveVertices();
  assert.equal(vertices.length, 8);

  const minP = box.minPoint;
  const maxP = box.maxPoint;
  assert.equal(minP.x, 9);
  assert.equal(minP.y, 18);
  assert.equal(minP.z, 27);
  assert.equal(maxP.x, 11);
  assert.equal(maxP.y, 22);
  assert.equal(maxP.z, 33);

  const faces = box.getFaces();
  assert.equal(faces.length, 6);
  const faceMap = new Map(faces.map((f) => [f.name, f.normal]));

  assert.deepEqual(faceMap.get("East"), new Vector3(1, 0, 0));
  assert.deepEqual(faceMap.get("West"), new Vector3(-1, 0, 0));
  assert.deepEqual(faceMap.get("Up"), new Vector3(0, 1, 0));
  assert.deepEqual(faceMap.get("Down"), new Vector3(0, -1, 0));
  assert.deepEqual(faceMap.get("South"), new Vector3(0, 0, 1));
  assert.deepEqual(faceMap.get("North"), new Vector3(0, 0, -1));
});

test("Swept AABB time of impact and collision normal detection", () => {
  const moving = new BoundingBox(new Vector3(0, 0, 0), new Vector3(1, 1, 1));
  const obstacle = new BoundingBox(new Vector3(5, 0, 0), new Vector3(1, 1, 1));
  const velocity = new Vector3(10, 0, 0);

  const hit = SweptAABBEngine.testSweptAABB(moving, velocity, obstacle);
  assert.equal(hit.hasCollision, true);
  assert.ok(Math.abs(hit.timeOfImpact - 0.3) < 1e-5);
  assert.equal(hit.normal.x, -1);
  assert.equal(hit.normal.y, 0);
  assert.equal(hit.normal.z, 0);
  assert.equal(hit.cardinalDirection, "West");
});

test("Dynamic vs dynamic entity collision evaluation", () => {
  const boxA = new BoundingBox(new Vector3(0, 0, 0), new Vector3(1, 1, 1));
  const velA = new Vector3(6, 0, 0);
  const boxB = new BoundingBox(new Vector3(10, 0, 0), new Vector3(1, 1, 1));
  const velB = new Vector3(-4, 0, 0);

  const hit = SweptAABBEngine.testDynamicVsDynamic(boxA, velA, boxB, velB);
  assert.equal(hit.hasCollision, true);
  assert.ok(Math.abs(hit.timeOfImpact - 0.8) < 1e-5);
});

test("High-velocity kinematic tunneling prevention (>1.5 blocks/tick)", () => {
  const moving = new BoundingBox(new Vector3(0, 0, 0), new Vector3(0.5, 1, 0.5));
  const wall = new BoundingBox(new Vector3(2, 0, 0), new Vector3(0.5, 4, 4));
  const velocity = new Vector3(6, 0, 0);

  const step = SweptAABBEngine.resolveKinematicStep(moving, velocity, [wall]);
  assert.equal(step.tunnelingPrevented, true);
  assert.ok(step.collisions.length > 0);
  assert.ok(step.finalPosition.x < wall.minPoint.x);
});

test("Multi-obstacle kinematic sliding deflection", () => {
  const moving = new BoundingBox(new Vector3(0, 0, 0), new Vector3(0.5, 0.5, 0.5));
  const obsA = new BoundingBox(new Vector3(2, 0, 0), new Vector3(0.5, 2, 2));
  const obsB = new BoundingBox(new Vector3(2, 2, 0), new Vector3(2, 0.5, 2));
  const velocity = new Vector3(4, 1, 0);

  const step = SweptAABBEngine.resolveKinematicStep(moving, velocity, [obsA, obsB]);
  assert.ok(step.finalPosition.x < obsA.minPoint.x);
});

test("Resolution of tick 4192 raycast miss log warning", () => {
  const engine = new KinematicHitboxEngine();
  const res = engine.resolveTick4192Scenario();

  assert.equal(res.hit, true);
  assert.equal(res.warningMissResolved, true);
  assert.equal(res.tick, 4192);
  assert.ok(res.subTickFraction > 0);
  assert.ok(Number.isFinite(res.distance));
});

test("KinematicHitboxEngine lifecycle and tick processing", () => {
  const engine = new KinematicHitboxEngine();
  engine.trackEntity("ent_1", "minecraft:zombie", { x: 0, y: 0, z: 0 }, { x: 0.5, y: 1, z: 0.5 }, { x: 3, y: 0, z: 0 }, 100);
  engine.addObstacle({ x: 2, y: 0, z: 0 }, { x: 0.5, y: 2, z: 2 });

  const tickResults = engine.tickKinematics(101);
  assert.ok(tickResults.has("ent_1"));
  const step = tickResults.get("ent_1");
  assert.equal(step.tunnelingPrevented, true);
  assert.ok(step.finalPosition.x < 1.5);
});
