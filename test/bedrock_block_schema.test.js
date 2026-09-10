/**
 * Bedrock Block Schema and Pack Asset Invariant Test Suite (Issue #1306)
 */

const fs = require('fs');
const path = require('path');

describe('Bedrock Block Schema 1.21.40+ (Issue #1306)', () => {
  const bpBlockPath = path.resolve(__dirname, '../packs/BP/blocks/void_crystal_ore.json');
  const geoPath = path.resolve(__dirname, '../packs/RP/models/blocks/void_crystal_ore.geo.json');
  const terrainPath = path.resolve(__dirname, '../packs/RP/textures/terrain_texture.json');

  test('BP block definition exists and has format_version 1.21.40', () => {
    expect(fs.existsSync(bpBlockPath)).toBe(true);
    const blockData = JSON.parse(fs.readFileSync(bpBlockPath, 'utf8'));
    expect(blockData.format_version).toBe('1.21.40');
    expect(blockData['minecraft:block']).toBeDefined();
    expect(blockData['minecraft:block'].description.identifier).toBe('custom:void_crystal_ore');
  });

  test('material_instances defines explicit directional faces with alpha_test and isotropic:false', () => {
    const blockData = JSON.parse(fs.readFileSync(bpBlockPath, 'utf8'));
    const instances = blockData['minecraft:block'].components['minecraft:material_instances'];
    expect(instances).toBeDefined();
    expect(instances['*']).toBeUndefined();

    const expectedFaces = ['up', 'down', 'north', 'south', 'east', 'west'];
    expectedFaces.forEach((face) => {
      expect(instances[face]).toBeDefined();
      expect(instances[face].render_method).toBe('alpha_test');
      expect(instances[face].isotropic).toBe(false);
      expect(typeof instances[face].texture).toBe('string');
    });
  });

  test('selection_box and collision_box match standard unit cube bounds for seamless outlines', () => {
    const blockData = JSON.parse(fs.readFileSync(bpBlockPath, 'utf8'));
    const components = blockData['minecraft:block'].components;

    expect(components['minecraft:selection_box']).toEqual({
      origin: [-8.0, 0.0, -8.0],
      size: [16.0, 16.0, 16.0],
    });
    expect(components['minecraft:collision_box']).toEqual({
      origin: [-8.0, 0.0, -8.0],
      size: [16.0, 16.0, 16.0],
    });
  });

  test('RP terrain_texture.json maps all face texture identifiers', () => {
    expect(fs.existsSync(terrainPath)).toBe(true);
    const terrain = JSON.parse(fs.readFileSync(terrainPath, 'utf8'));
    expect(terrain.texture_data).toBeDefined();
    expect(terrain.texture_data.void_crystal_ore_top).toBeDefined();
    expect(terrain.texture_data.void_crystal_ore_bottom).toBeDefined();
    expect(terrain.texture_data.void_crystal_ore_side).toBeDefined();
  });

  test('RP geometry defines unit cube bounds with per-face UV bindings', () => {
    expect(fs.existsSync(geoPath)).toBe(true);
    const geo = JSON.parse(fs.readFileSync(geoPath, 'utf8'));
    const primary = geo['minecraft:geometry'][0];
    expect(primary.description.identifier).toBe('geometry.void_crystal_ore');

    const rootCube = primary.bones[0].cubes[0];
    expect(rootCube.origin).toEqual([-8.0, 0.0, -8.0]);
    expect(rootCube.size).toEqual([16.0, 16.0, 16.0]);
    expect(Object.keys(rootCube.uv)).toEqual(
      expect.arrayContaining(['north', 'east', 'south', 'west', 'up', 'down'])
    );
  });
});
