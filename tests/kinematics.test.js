/**
 * Automated test suite verifying kinematics solver and collision guard in Node.js.
 */

import test from "node:test";
import assert from "node:assert/strict";
import {
  VectorMath,
  RungeKutta4Integrator,
  KinematicKalmanFilter,
  CollisionDropoutGuard,
} from "../src/physics/KinematicsSolver.js";
import {
  updateColliderKinematics,
  diagnoseKinematicPipeline,
} from "../src/physics/ContraptionKinematics.js";

test("VectorMath operations", () => {
  const v1 = { x: 1, y: 2, z: 3 };
  const v2 = { x: 4, y: 5, z: 6 };

  const sum = VectorMath.add(v1, v2);
  assert.deepEqual(sum, { x: 5, y: 7, z: 9 });

  const diff = VectorMath.sub(v2, v1);
  assert.deepEqual(diff, { x: 3, y: 3, z: 3 });

  const scaled = VectorMath.scale(v1, 2);
  assert.deepEqual(scaled, { x: 2, y: 4, z: 6 });

  const dist = VectorMath.distance({ x: 0, y: 0, z: 0 }, { x: 3, y: 4, z: 0 });
  assert.equal(dist, 5);
});

test("RungeKutta4Integrator numerical convergence", () => {
  const metrics = RungeKutta4Integrator.verifyConvergence(0.05, 1.0);
  assert.equal(metrics.converged, true);
  assert.ok(metrics.maxAbsoluteError < 1e-6);
  assert.ok(metrics.estimatedOrder >= 3.8);
});

test("KinematicKalmanFilter estimation and extrapolation", () => {
  const kf = new KinematicKalmanFilter(
    { x: 0, y: 0, z: 0 },
    { x: 0, y: 10, z: 0 }
  );

  kf.predict(0.05);
  const pos = kf.getPosition();
  assert.ok(Math.abs(pos.y - 0.5) < 0.01);

  const extrapolated = kf.extrapolate(0.05);
  assert.ok(Math.abs(extrapolated.y - 1.0) < 0.02);

  kf.update({ x: 0, y: 0.52, z: 0 });
  const updatedPos = kf.getPosition();
  assert.ok(Math.abs(updatedPos.y - 0.51) < 0.05);
});

test("CollisionDropoutGuard support evaluation", () => {
  const guard = new CollisionDropoutGuard();
  const playerFeet = { x: 0, y: 11, z: 0 };
  const shulkerBase = { x: 0, y: 10, z: 0 };

  const isSupported = guard.evaluateSupport(playerFeet, shulkerBase);
  assert.equal(isSupported, true);

  const lowPlayerFeet = { x: 0, y: 10.98, z: 0 };
  const resolved = guard.resolveSupport(lowPlayerFeet, shulkerBase);
  assert.equal(resolved.y, 11);
});

test("updateColliderKinematics prevents effect spam and floor truncation", () => {
  let addEffectCalls = 0;
  let activeEffect = undefined;
  let teleportedLocations = [];

  const mockEntity = {
    addEffect(type, duration, options) {
      addEffectCalls++;
      activeEffect = { typeId: type, duration };
    },
    getEffect(type) {
      return activeEffect;
    },
    teleport(loc) {
      teleportedLocations.push(loc);
    },
  };

  const targetCoords = [
    { x: 10.5, y: 64.1234, z: -20.5 },
    { x: 10.5, y: 64.6234, z: -20.5 },
    { x: 10.5, y: 65.1234, z: -20.5 },
    { x: 10.5, y: 65.6234, z: -20.5 },
  ];

  for (const pos of targetCoords) {
    updateColliderKinematics(mockEntity, pos);
  }

  assert.equal(addEffectCalls, 1);
  assert.equal(teleportedLocations.length, 4);

  for (let i = 0; i < targetCoords.length; i++) {
    assert.equal(teleportedLocations[i].y, targetCoords[i].y);
    assert.notEqual(teleportedLocations[i].y, Math.floor(targetCoords[i].y * 100) / 100);
  }
});

test("diagnoseKinematicPipeline demonstrates 100% dropout elimination", () => {
  const diag = diagnoseKinematicPipeline(100, 20.0);
  assert.ok(diag.flawedDropouts > 0);
  assert.equal(diag.fixedDropouts, 0);
  assert.equal(diag.packetsAvoided, 99);
});
