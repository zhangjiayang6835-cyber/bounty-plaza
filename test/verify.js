import assert from 'node:assert/strict';
import {
  TextureAtlasManager,
  UnifiedVoxelEntity,
  VoxelClusterSpawner,
  DrawCallOptimizer,
  spawnClusterBlock
} from '../scripts/voxel/index.js';

function runVerification() {
  const manager = new TextureAtlasManager(64);
  const idx = manager.getAtlasIndex('minecraft:emerald_block');
  assert.ok(idx >= 0);

  const optimizer = new DrawCallOptimizer(2048);
  const mockEntities = [];
  const dummyEntity = {
    id: 'e1',
    typeId: 'contraption:unified_voxel_display',
    location: { x: 0, y: 0, z: 0 },
    setProperty() {},
    getProperty() {},
    triggerEvent() {},
    remove() {}
  };

  for (let i = 0; i < 256; i++) {
    const v = new UnifiedVoxelEntity(dummyEntity, `block_${i % 16}`, manager);
    mockEntities.push(v);
  }

  const metrics = optimizer.evaluateMetrics(mockEntities);
  assert.equal(metrics.totalBlocks, 256);
  assert.equal(metrics.uniqueBlockTypes, 16);
  assert.equal(metrics.unifiedDrawCalls, 1);
  assert.ok(metrics.unifiedFps >= 60);

  console.log('All Node.js voxel cluster tests passed successfully.');
}

runVerification();
