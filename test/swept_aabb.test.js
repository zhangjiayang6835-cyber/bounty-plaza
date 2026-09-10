import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  BedrockAABB,
  KinematicCollisionEngine,
  SweptAABBCalculator,
  deriveBedrockVertices,
  sweptAABBCollision
} from "../dist/src/physics/sweptAABB.js";

describe("Bedrock Swept AABB Continuous Collision Detection", () => {
  it("derives all 8 vertices conforming to Bedrock coordinate space", () => {
    const box = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 2, z: 3 });
    const vertices = box.deriveVertices();
    assert.equal(vertices.length, 8);
    assert.deepEqual(vertices[0], { x: -1, y: -2, z: -3 });
    assert.deepEqual(vertices[1], { x: 1, y: -2, z: -3 });
    assert.deepEqual(vertices[2], { x: -1, y: 2, z: -3 });
    assert.deepEqual(vertices[3], { x: 1, y: 2, z: -3 });
    assert.deepEqual(vertices[4], { x: -1, y: -2, z: 3 });
    assert.deepEqual(vertices[5], { x: 1, y: -2, z: 3 });
    assert.deepEqual(vertices[6], { x: -1, y: 2, z: 3 });
    assert.deepEqual(vertices[7], { x: 1, y: 2, z: 3 });
  });

  it("evaluates 6 cardinal faces with outward normal vectors", () => {
    const box = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
    const faces = box.getFaces();
    assert.equal(faces.length, 6);

    const normalMap = new Map(faces.map((f) => [f.name, f.normal]));
    assert.deepEqual(normalMap.get("East"), { x: 1, y: 0, z: 0 });
    assert.deepEqual(normalMap.get("West"), { x: -1, y: 0, z: 0 });
    assert.deepEqual(normalMap.get("Up"), { x: 0, y: 1, z: 0 });
    assert.deepEqual(normalMap.get("Down"), { x: 0, y: -1, z: 0 });
    assert.deepEqual(normalMap.get("South"), { x: 0, y: 0, z: 1 });
    assert.deepEqual(normalMap.get("North"), { x: 0, y: 0, z: -1 });
  });

  it("calculates exact swept AABB time of impact and collision normal", () => {
    const moving = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
    const obstacle = new BedrockAABB({ x: 5, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
    const velocity = { x: 10, y: 0, z: 0 };

    const hit = SweptAABBCalculator.testSweptAABB(moving, velocity, obstacle);
    assert.equal(hit.hasCollision, true);
    assert.ok(Math.abs(hit.timeOfImpact - 0.3) < 1e-5);
    assert.deepEqual(hit.normal, { x: -1, y: 0, z: 0 });
    assert.equal(hit.cardinalDirection, "West");
  });

  it("prevents projectile and entity tunneling above 1.5 blocks/tick", () => {
    const moving = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 1, z: 1 });
    const barrier = new BedrockAABB({ x: 2, y: 0, z: 0 }, { x: 0.5, y: 10, z: 10 });
    const velocity = { x: 8, y: 0, z: 0 };

    const result = KinematicCollisionEngine.resolveKinematicStep(moving, velocity, [barrier]);
    assert.equal(result.tunnelingPrevented, true);
    assert.ok(result.finalPosition.x < barrier.min.x);
  });

  it("synchronizes sub-tick raycasts and eliminates tick 5812 dropout", () => {
    const entity = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 1, y: 2, z: 1 });
    const velocity = { x: 10, y: 0, z: 0 };
    const ray = {
      origin: { x: 5, y: 0, z: -10 },
      direction: { x: 0, y: 0, z: 1 },
      maxDistance: 20
    };

    const res = KinematicCollisionEngine.synchronizeSubTickRaycast(entity, velocity, ray, 0.5);
    assert.equal(res.hit, true);
    assert.equal(res.warningDropped, false);
  });

  it("evaluates dynamic vs dynamic relative velocities", () => {
    const a = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
    const b = new BedrockAABB({ x: 5, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
    const velA = { x: 3, y: 0, z: 0 };
    const velB = { x: -2, y: 0, z: 0 };

    const hit = SweptAABBCalculator.testDynamicVsDynamic(a, velA, b, velB);
    assert.equal(hit.hasCollision, true);
    assert.ok(Math.abs(hit.timeOfImpact - 0.8) < 1e-5);
  });

  it("resolves multi-obstacle sliding deflection", () => {
    const mover = new BedrockAABB({ x: 0, y: 0, z: 0 }, { x: 0.5, y: 0.5, z: 0.5 });
    const obs = [
      new BedrockAABB({ x: 2, y: 0, z: 0 }, { x: 0.5, y: 2, z: 0.5 }),
      new BedrockAABB({ x: 0, y: 2, z: 0 }, { x: 2, y: 0.5, z: 0.5 })
    ];
    const vel = { x: 3, y: 3, z: 0 };

    const resolved = KinematicCollisionEngine.resolveKinematicStep(mover, vel, obs);
    for (const o of obs) {
      const placed = new BedrockAABB(resolved.finalPosition, mover.extent);
      assert.equal(placed.intersects(o), false);
    }
  });

  it("verifies functional API helpers deriveBedrockVertices and sweptAABBCollision", () => {
    const vertices = deriveBedrockVertices([1, 2, 3], [4, 5, 6]);
    assert.equal(vertices.length, 8);
    assert.deepEqual(vertices[0], [1, 2, 3]);
    assert.deepEqual(vertices[7], [5, 7, 9]);

    const collision = sweptAABBCollision(
      { pos: [0, 0, 0], size: [1, 1, 1] },
      [10, 0, 0],
      [{ min: [4, -2, -2], max: [6, 2, 2] }]
    );
    assert.equal(collision.collided, true);
    assert.deepEqual(collision.normal, [-1, 0, 0]);
  });
});
