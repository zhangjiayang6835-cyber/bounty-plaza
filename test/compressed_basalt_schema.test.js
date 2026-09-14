import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';
import {
  validateBlockDefinition,
  validateCompressedBasaltDefinition,
} from '../scripts/blocks/index.js';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(currentDir, '..');

test('compressed_basalt block definition file exists and conforms to Bedrock schema', () => {
  const filePath = path.join(rootDir, 'blocks', 'compressed_basalt.json');
  assert.equal(fs.existsSync(filePath), true);

  const raw = fs.readFileSync(filePath, 'utf-8');
  const json = JSON.parse(raw);

  assert.equal(json.format_version, '1.21.50');
  assert.equal(
    json['minecraft:block']?.description?.identifier,
    'custom:compressed_basalt'
  );
  assert.equal('isotropic' in (json['minecraft:block']?.description || {}), false);

  const components = json['minecraft:block']?.components;
  assert.ok(components);
  assert.equal(
    components['minecraft:destroy_time'] ??
      components['minecraft:destructible_by_mining']?.seconds_to_destroy,
    2.5
  );
  assert.equal(components['minecraft:friction'], 0.6);
  assert.equal(components['minecraft:map_color'], '#474F52');

  const validationResult = validateCompressedBasaltDefinition(json);
  assert.equal(validationResult.valid, true);
  assert.equal(validationResult.errors.length, 0);
});

test('minecraft:material_instances correctly configures directional faces and isotropic rendering', () => {
  const filePath = path.join(rootDir, 'blocks', 'compressed_basalt.json');
  const json = JSON.parse(fs.readFileSync(filePath, 'utf-8'));
  const matInstances =
    json['minecraft:block']?.components?.['minecraft:material_instances'];

  assert.ok(matInstances);

  const directionalFaces = ['up', 'down', 'north', 'south', 'east', 'west'];
  for (const face of directionalFaces) {
    assert.ok(matInstances[face], `Missing directional face '${face}'`);
    assert.equal(matInstances[face].render_method, 'opaque');
    assert.equal(matInstances[face].ambient_occlusion, 1.0);
    assert.equal(matInstances[face].face_dimming, true);
  }

  assert.equal(matInstances['up'].isotropic, true);
  assert.equal(matInstances['down'].isotropic, true);
  assert.equal(matInstances['north'].isotropic, undefined);
  assert.equal(matInstances['*'].render_method, 'opaque');
});

test('validator rejects invalid wildcard with alpha_test and misplaced isotropic', () => {
  const invalidWildcardDoc = {
    format_version: '1.21.40',
    'minecraft:block': {
      description: {
        identifier: 'custom:compressed_basalt',
      },
      components: {
        'minecraft:material_instances': {
          '*': {
            texture: 'compressed_basalt',
            render_method: 'alpha_test',
          },
        },
      },
    },
  };

  const result1 = validateBlockDefinition(invalidWildcardDoc);
  assert.equal(result1.valid, false);
  assert.ok(
    result1.errors.some((err) =>
      err.includes("contains invalid face specifier '*' with render method 'alpha_test'")
    )
  );

  const invalidDescriptionIsotropicDoc = {
    format_version: '1.21.50',
    'minecraft:block': {
      description: {
        identifier: 'custom:compressed_basalt',
        isotropic: true,
      },
      components: {
        'minecraft:material_instances': {
          up: { texture: 'top', render_method: 'opaque' },
          down: { texture: 'bottom', render_method: 'opaque' },
          north: { texture: 'side', render_method: 'opaque' },
          south: { texture: 'side', render_method: 'opaque' },
          east: { texture: 'side', render_method: 'opaque' },
          west: { texture: 'side', render_method: 'opaque' },
        },
      },
    },
  };

  const result2 = validateBlockDefinition(invalidDescriptionIsotropicDoc);
  assert.equal(result2.valid, false);
  assert.ok(
    result2.errors.some((err) =>
      err.includes("Property 'isotropic' is not allowed in 'description'")
    )
  );
});

test('supporting resource definitions exist and cross-reference block identifiers', () => {
  const cullingPath = path.join(rootDir, 'block_culling', 'compressed_basalt.culling.json');
  assert.equal(fs.existsSync(cullingPath), true);
  const cullingJson = JSON.parse(fs.readFileSync(cullingPath, 'utf-8'));
  assert.equal(
    cullingJson['minecraft:block_culling_rules']?.description?.identifier,
    'custom:compressed_basalt_culling'
  );

  const geoPath = path.join(rootDir, 'models', 'blocks', 'compressed_basalt.geo.json');
  assert.equal(fs.existsSync(geoPath), true);
  const geoJson = JSON.parse(fs.readFileSync(geoPath, 'utf-8'));
  assert.equal(
    geoJson['minecraft:geometry']?.[0]?.description?.identifier,
    'geometry.compressed_basalt'
  );

  const texturePath = path.join(rootDir, 'textures', 'terrain_texture.json');
  assert.equal(fs.existsSync(texturePath), true);
  const textureJson = JSON.parse(fs.readFileSync(texturePath, 'utf-8'));
  assert.ok(textureJson.texture_data?.compressed_basalt_top);
  assert.ok(textureJson.texture_data?.compressed_basalt_bottom);
  assert.ok(textureJson.texture_data?.compressed_basalt_side);

  const manifestPath = path.join(rootDir, 'manifest.json');
  assert.equal(fs.existsSync(manifestPath), true);
  const manifestJson = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
  assert.deepEqual(manifestJson.header?.min_engine_version, [1, 21, 50]);
});
