import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  BedrockAABB,
  SweptAABBCalculator,
  KinematicCollisionEngine
} from "../scripts/kinematic_collision/index.js";

const currentDirectory = path.dirname(fileURLToPath(import.meta.url));
const rootDirectory = path.resolve(currentDirectory, "..");

test("Derives 8 bounding box vertices following Bedrock coordinate conventions (+X East, +Y Up, +Z South)", () => {
  const box = BedrockAABB.fromMinMax(
    { x: 10, y: 64, z: -5 },
    { x: 12, y: 66, z: -3 }
  );

  assert.equal(box.min.x, 10);
  assert.equal(box.min.y, 64);
  assert.equal(box.min.z, -5);
  assert.equal(box.max.x, 12);
  assert.equal(box.max.y, 66);
  assert.equal(box.max.z, -3);

  assert.equal(box.center.x, 11);
  assert.equal(box.center.y, 65);
  assert.equal(box.center.z, -4);

  assert.equal(box.extent.x, 1);
  assert.equal(box.extent.y, 1);
  assert.equal(box.extent.z, 1);

  const vertices = box.deriveVertices();
  assert.equal(vertices.length, 8);

  assert.deepEqual(vertices[0], { x: 10, y: 64, z: -5 });
  assert.deepEqual(vertices[1], { x: 12, y: 64, z: -5 });
  assert.deepEqual(vertices[2], { x: 10, y: 66, z: -5 });
  assert.deepEqual(vertices[3], { x: 12, y: 66, z: -5 });
  assert.deepEqual(vertices[4], { x: 10, y: 64, z: -3 });
  assert.deepEqual(vertices[5], { x: 12, y: 64, z: -3 });
  assert.deepEqual(vertices[6], { x: 10, y: 66, z: -3 });
  assert.deepEqual(vertices[7], { x: 12, y: 66, z: -3 });
});

test("Generates 6 cardinal faces with Bedrock normal vectors", () => {
  const box = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 0 },
    { x: 2, y: 2, z: 2 }
  );

  const faces = box.getFaces();
  assert.equal(faces.length, 6);

  const eastFace = faces.find((f) => f.name === "East");
  assert.ok(eastFace);
  assert.deepEqual(eastFace.normal, { x: 1, y: 0, z: 0 });

  const westFace = faces.find((f) => f.name === "West");
  assert.ok(westFace);
  assert.deepEqual(westFace.normal, { x: -1, y: 0, z: 0 });

  const upFace = faces.find((f) => f.name === "Up");
  assert.ok(upFace);
  assert.deepEqual(upFace.normal, { x: 0, y: 1, z: 0 });

  const downFace = faces.find((f) => f.name === "Down");
  assert.ok(downFace);
  assert.deepEqual(downFace.normal, { x: 0, y: -1, z: 0 });

  const southFace = faces.find((f) => f.name === "South");
  assert.ok(southFace);
  assert.deepEqual(southFace.normal, { x: 0, y: 0, z: 1 });

  const northFace = faces.find((f) => f.name === "North");
  assert.ok(northFace);
  assert.deepEqual(northFace.normal, { x: 0, y: 0, z: -1 });
});

test("Swept AABB detects collision and computes exact TOI across cardinal axes", () => {
  const moving = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 0 },
    { x: 1, y: 1, z: 1 }
  );
  const obstacle = BedrockAABB.fromMinMax(
    { x: 3, y: 0, z: 0 },
    { x: 4, y: 1, z: 1 }
  );

  const hitEast = SweptAABBCalculator.testSweptAABB(moving, { x: 4, y: 0, z: 0 }, obstacle);
  assert.equal(hitEast.hasCollision, true);
  assert.equal(hitEast.timeOfImpact, 0.5);
  assert.deepEqual(hitEast.normal, { x: -1, y: 0, z: 0 });
  assert.equal(hitEast.cardinalDirection, "West");

  const movingUp = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 0 },
    { x: 1, y: 1, z: 1 }
  );
  const obstacleUp = BedrockAABB.fromMinMax(
    { x: 0, y: 4, z: 0 },
    { x: 1, y: 5, z: 1 }
  );
  const hitUp = SweptAABBCalculator.testSweptAABB(movingUp, { x: 0, y: 6, z: 0 }, obstacleUp);
  assert.equal(hitUp.hasCollision, true);
  assert.equal(hitUp.timeOfImpact, 0.5);
  assert.deepEqual(hitUp.normal, { x: 0, y: -1, z: 0 });
  assert.equal(hitUp.cardinalDirection, "Down");

  const movingSouth = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 0 },
    { x: 1, y: 1, z: 1 }
  );
  const obstacleSouth = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 5 },
    { x: 1, y: 1, z: 6 }
  );
  const hitSouth = SweptAABBCalculator.testSweptAABB(movingSouth, { x: 0, y: 0, z: 8 }, obstacleSouth);
  assert.equal(hitSouth.hasCollision, true);
  assert.equal(hitSouth.timeOfImpact, 0.5);
  assert.deepEqual(hitSouth.normal, { x: 0, y: 0, z: -1 });
  assert.equal(hitSouth.cardinalDirection, "North");
});

test("Prevents projectile and contraption tunneling during rapid kinematic translation (> 1.5 blocks/tick)", () => {
  const fastContraption = BedrockAABB.fromMinMax(
    { x: 0, y: 64, z: 0 },
    { x: 1, y: 65, z: 1 }
  );
  const thinWall = BedrockAABB.fromMinMax(
    { x: 2.0, y: 64, z: 0 },
    { x: 2.3, y: 65, z: 1 }
  );

  const rapidVelocity = { x: 5.0, y: 0, z: 0 };
  assert.ok(Math.hypot(rapidVelocity.x, rapidVelocity.y, rapidVelocity.z) > 1.5);

  const discreteNextPosition = {
    x: fastContraption.center.x + rapidVelocity.x,
    y: fastContraption.center.y,
    z: fastContraption.center.z
  };
  const discreteBox = new BedrockAABB(discreteNextPosition, fastContraption.extent);
  assert.equal(
    discreteBox.intersects(thinWall),
    false,
    "Discrete collision must fail and tunnel through thin wall"
  );

  const resolution = KinematicCollisionEngine.resolveKinematicStep(
    fastContraption,
    rapidVelocity,
    [thinWall]
  );

  assert.equal(resolution.tunnelingPrevented, true);
  assert.equal(resolution.collisions.length > 0, true);
  assert.ok(resolution.finalPosition.x <= 1.5);
});

test("Synchronizes sub-tick raycasts and eliminates tick 5812 collision dropout warning", () => {
  const entityOrigin = BedrockAABB.fromMinMax(
    { x: 0, y: 64, z: 0 },
    { x: 1, y: 66, z: 1 }
  );
  const translationVelocity = { x: 4.0, y: 0, z: 0 };

  const ray = {
    origin: { x: 2.5, y: 65, z: -5 },
    direction: { x: 0, y: 0, z: 1 },
    maxDistance: 10
  };

  const hit = KinematicCollisionEngine.synchronizeSubTickRaycast(
    entityOrigin,
    translationVelocity,
    ray,
    0.5
  );

  assert.equal(hit.hit, true);
  assert.equal(hit.warningDropped, false);
  assert.ok(hit.distance > 0);
  assert.equal(hit.subTickFraction, 0.5);
  assert.deepEqual(hit.normal, { x: 0, y: 0, z: -1 });
});

test("Handles dynamic entity versus dynamic obstacle relative velocities", () => {
  const entityA = BedrockAABB.fromMinMax(
    { x: 0, y: 0, z: 0 },
    { x: 1, y: 1, z: 1 }
  );
  const entityB = BedrockAABB.fromMinMax(
    { x: 10, y: 0, z: 0 },
    { x: 11, y: 1, z: 1 }
  );

  const velA = { x: 5, y: 0, z: 0 };
  const velB = { x: -5, y: 0, z: 0 };

  const hit = SweptAABBCalculator.testDynamicVsDynamic(entityA, velA, entityB, velB);
  assert.equal(hit.hasCollision, true);
  assert.equal(hit.timeOfImpact, 0.9);
  assert.deepEqual(hit.normal, { x: -1, y: 0, z: 0 });
});

test("Validates manifest.json format version and module definitions", () => {
  const manifestPath = path.join(rootDirectory, "manifest.json");
  assert.ok(fs.existsSync(manifestPath), "manifest.json must exist");

  const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf-8"));
  assert.equal(manifest.format_version, 2);
  assert.ok(Array.isArray(manifest.modules));
  assert.ok(manifest.modules.some((m) => m.type === "script" && m.entry === "scripts/main.js"));
  assert.ok(manifest.dependencies.some((d) => d.module_name === "@minecraft/server"));
});

test("Ensures scripts/main.ts and compiled scripts/main.js enforce runtime safety", () => {
  const mainTs = path.join(rootDirectory, "scripts", "main.ts");
  const mainJs = path.join(rootDirectory, "scripts", "main.js");

  assert.ok(fs.existsSync(mainTs), "scripts/main.ts must exist");
  assert.ok(fs.existsSync(mainJs), "scripts/main.js must exist");

  const tsContent = fs.readFileSync(mainTs, "utf-8");
  const jsContent = fs.readFileSync(mainJs, "utf-8");

  assert.ok(tsContent.includes("@minecraft/server"));
  assert.ok(jsContent.includes("@minecraft/server"));
  assert.ok(tsContent.includes("system.runInterval"));
  assert.ok(!tsContent.includes("world.sendMessage("));
});
