import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { BedrockUVValidator, GeometryGenerator } from '../scripts/geometry/index.js';

describe('Bedrock Custom NPC Geometry Engine', () => {
  const rootDir = process.cwd();
  const classicGeoPath = path.join(rootDir, 'models', 'entity', 'custom_npc.geo.json');
  const slimGeoPath = path.join(rootDir, 'models', 'entity', 'custom_npc_slim.geo.json');
  const entityDefPath = path.join(rootDir, 'entity', 'custom_npc.entity.json');
  const manifestPath = path.join(rootDir, 'manifest.json');

  it('verifies manifest.json declares Bedrock 1.21.50+ compatibility', () => {
    const raw = fs.readFileSync(manifestPath, 'utf8');
    const manifest = JSON.parse(raw);
    assert.equal(manifest.format_version, 2);
    assert.deepEqual(manifest.header.min_engine_version, [1, 21, 50]);
  });

  it('verifies entity definition binds both classic and slim geometries', () => {
    const raw = fs.readFileSync(entityDefPath, 'utf8');
    const entity = JSON.parse(raw);
    const clientEntity = entity['minecraft:client_entity'];
    assert.ok(clientEntity);
    assert.equal(clientEntity.description.identifier, 'custom:custom_npc');
    assert.equal(clientEntity.description.geometry.default, 'geometry.custom_npc');
    assert.equal(clientEntity.description.geometry.slim, 'geometry.custom_npc.slim');
  });

  it('validates canonical classic NPC geometry file against 1.21.50 rules', () => {
    const raw = fs.readFileSync(classicGeoPath, 'utf8');
    const geoDoc = JSON.parse(raw);
    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(geoDoc, 'classic');

    assert.equal(report.isValid, true);
    assert.equal(report.issues.filter((i) => i.severity === 'error').length, 0);

    const bones = geoDoc['minecraft:geometry'][0].bones;
    const leftArm = bones.find((b) => b.name === 'leftArm');
    assert.ok(leftArm);
    assert.equal(leftArm.mirror, undefined);
    assert.equal(leftArm.cubes[0].mirror, false);
    assert.deepEqual(leftArm.cubes[0].uv, [32, 48]);
    assert.equal(leftArm.cubes[0].size[0], 4);

    const leftLeg = bones.find((b) => b.name === 'leftLeg');
    assert.ok(leftLeg);
    assert.equal(leftLeg.mirror, undefined);
    assert.equal(leftLeg.cubes[0].mirror, false);
    assert.deepEqual(leftLeg.cubes[0].uv, [16, 48]);
  });

  it('validates canonical slim NPC geometry file against 1.21.50 rules', () => {
    const raw = fs.readFileSync(slimGeoPath, 'utf8');
    const geoDoc = JSON.parse(raw);
    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(geoDoc, 'slim');

    assert.equal(report.isValid, true);
    assert.equal(report.issues.filter((i) => i.severity === 'error').length, 0);

    const bones = geoDoc['minecraft:geometry'][0].bones;
    const leftArm = bones.find((b) => b.name === 'leftArm');
    assert.ok(leftArm);
    assert.equal(leftArm.cubes[0].mirror, false);
    assert.deepEqual(leftArm.cubes[0].uv, [32, 48]);
    assert.equal(leftArm.cubes[0].size[0], 3);

    const rightArm = bones.find((b) => b.name === 'rightArm');
    assert.ok(rightArm);
    assert.equal(rightArm.cubes[0].size[0], 3);
  });

  it('catches legacy 64x32 textures as invalid', () => {
    const doc = GeometryGenerator.createHumanoid('geometry.test', 'classic');
    doc['minecraft:geometry'][0].description.texture_height = 32;

    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(doc);
    assert.equal(report.isValid, false);
    assert.ok(report.issues.some((i) => i.code === 'LEGACY_32X64_TEXTURE_DETECTED'));
  });

  it('catches legacy mirror:true on left arm causing texture scrambling', () => {
    const doc = GeometryGenerator.createHumanoid('geometry.test', 'classic');
    const leftArm = doc['minecraft:geometry'][0].bones.find((b) => b.name === 'leftArm');
    leftArm.cubes[0].mirror = true;

    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(doc);
    assert.equal(report.isValid, false);
    assert.ok(report.issues.some((i) => i.code === 'MIRRORED_LEFTARM_DETECTED'));
  });

  it('catches legacy right arm UV reused on left arm', () => {
    const doc = GeometryGenerator.createHumanoid('geometry.test', 'classic');
    const leftArm = doc['minecraft:geometry'][0].bones.find((b) => b.name === 'leftArm');
    leftArm.cubes[0].uv = [40, 16];

    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(doc);
    assert.equal(report.isValid, false);
    assert.ok(report.issues.some((i) => i.code === 'LEGACY_LEFT_ARM_UV_DETECTED'));
  });

  it('catches arm dimension mismatch between classic and slim models', () => {
    const doc = GeometryGenerator.createHumanoid('geometry.test', 'classic');
    const validator = new BedrockUVValidator();
    const report = validator.validateDocument(doc, 'slim');
    assert.equal(report.isValid, false);
    assert.ok(report.issues.some((i) => i.code === 'ARM_DIMENSION_MISMATCH'));
  });
});
