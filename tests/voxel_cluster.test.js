const test = require('node:test');
const assert = require('node:assert/strict');
const {
  TextureAtlasManager,
  UnifiedVoxelEntity,
  DrawCallOptimizer,
  VoxelClusterSpawner,
  spawnClusterBlock
} = require('../src/index');

/**
 * Creates an in-memory mock-free Dimension implementation for Script API verification.
 *
 * @returns {object} Dimension test harness.
 */
function createTestDimension() {
  const spawnedEntities = [];
  return {
    id: 'minecraft:overworld',
    spawnedEntities,
    spawnEntity(identifier, location) {
      const entityId = `entity_${spawnedEntities.length + 1}`;
      const properties = new Map();
      let removed = false;

      const entity = {
        id: entityId,
        typeId: identifier,
        location: { ...location },
        setProperty(name, value) {
          properties.set(name, value);
        },
        getProperty(name) {
          return properties.get(name);
        },
        triggerEvent() {},
        remove() {
          removed = true;
        },
        isRemoved() {
          return removed;
        }
      };
      spawnedEntities.push(entity);
      return entity;
    }
  };
}

test('Unified spawner spawns single unified entity representation for diverse block types', () => {
  const dimension = createTestDimension();
  const spawner = new VoxelClusterSpawner();

  const blocks = [
    'minecraft:stone',
    'minecraft:dirt',
    'minecraft:diamond_block',
    'minecraft:oak_planks',
    'custom_mod:basalt_ruin'
  ];

  for (let i = 0; i < blocks.length; i++) {
    const loc = { x: i, y: 64, z: 0 };
    const entity = spawner.spawnClusterBlock(dimension, loc, blocks[i]);
    assert.equal(entity.getBlockId(), blocks[i]);
  }

  assert.equal(dimension.spawnedEntities.length, blocks.length);
  for (const raw of dimension.spawnedEntities) {
    assert.equal(raw.typeId, 'contraption:unified_voxel_display');
  }
});

test('TextureAtlasManager generates deterministic UV coordinates and dynamic block indexing', () => {
  const manager = new TextureAtlasManager(64);
  const indexStone = manager.getAtlasIndex('minecraft:stone');
  const indexDirt = manager.getAtlasIndex('minecraft:dirt');

  assert.notEqual(indexStone, indexDirt);
  assert.equal(manager.getAtlasIndex('minecraft:stone'), indexStone);

  const customMeta = manager.registerBlock('modded:void_crystal');
  assert.equal(customMeta.blockId, 'modded:void_crystal');
  assert.ok(customMeta.uMax > customMeta.uMin);
  assert.ok(customMeta.vMax > customMeta.vMin);
});

test('Runtime block type mutation updates dynamic properties in place without entity recreation', () => {
  const dimension = createTestDimension();
  const spawner = new VoxelClusterSpawner();
  const entity = spawner.spawnClusterBlock(dimension, { x: 10, y: 70, z: 10 }, 'minecraft:stone');

  const initialSpawnCount = dimension.spawnedEntities.length;
  assert.equal(entity.getBlockId(), 'minecraft:stone');

  spawner.updateClusterBlockType(entity, 'minecraft:gold_block');
  assert.equal(entity.getBlockId(), 'minecraft:gold_block');
  assert.equal(dimension.spawnedEntities.length, initialSpawnCount);

  const rawEntity = dimension.spawnedEntities[0];
  assert.equal(rawEntity.getProperty('contraption:block_id'), 'minecraft:gold_block');
});

test('DrawCallOptimizer achieves over 80% draw call reduction and restores client FPS', () => {
  const dimension = createTestDimension();
  const spawner = new VoxelClusterSpawner();
  const optimizer = new DrawCallOptimizer(2048);

  const blockTypes = [];
  for (let i = 0; i < 64; i++) {
    blockTypes.push(`contraption:modular_block_${i}`);
  }

  const entities = [];
  for (let i = 0; i < 128; i++) {
    const blockId = blockTypes[i % blockTypes.length];
    entities.push(spawner.spawnClusterBlock(dimension, { x: i, y: 64, z: 0 }, blockId));
  }

  const metrics = optimizer.evaluateMetrics(entities);

  assert.equal(metrics.totalBlocks, 128);
  assert.equal(metrics.uniqueBlockTypes, 64);
  assert.equal(metrics.naiveDrawCalls, 64);
  assert.equal(metrics.unifiedDrawCalls, 1);
  assert.ok(metrics.drawCallReductionPercent >= 95.0);
  assert.ok(metrics.unifiedFps >= 100);
  assert.ok(metrics.naiveFps <= 25);
  assert.ok(metrics.fpsImprovementFactor >= 4.0);
});

test('Cluster management tracks and destroys entities cleanly', () => {
  const dimension = createTestDimension();
  const spawner = new VoxelClusterSpawner();

  spawner.spawnClusterBlock(dimension, { x: 0, y: 0, z: 0 }, 'minecraft:stone', 'ruin_alpha');
  spawner.spawnClusterBlock(dimension, { x: 1, y: 0, z: 0 }, 'minecraft:dirt', 'ruin_alpha');

  assert.equal(spawner.getClusterEntities('ruin_alpha').length, 2);

  spawner.removeCluster('ruin_alpha');
  assert.equal(spawner.getClusterEntities('ruin_alpha').length, 0);
  for (const raw of dimension.spawnedEntities) {
    assert.equal(raw.isRemoved(), true);
  }
});

test('Standalone spawnClusterBlock export matches signature requirement', () => {
  const dimension = createTestDimension();
  const entity = spawnClusterBlock(dimension, { x: 5, y: 80, z: -5 }, 'minecraft:obsidian');

  assert.equal(entity.getBlockId(), 'minecraft:obsidian');
  assert.equal(dimension.spawnedEntities[0].typeId, 'contraption:unified_voxel_display');
});
