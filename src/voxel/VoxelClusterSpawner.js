const { TextureAtlasManager } = require('./TextureAtlasManager');
const { UnifiedVoxelEntity } = require('./UnifiedVoxelEntity');

/**
 * Manages spawning and runtime updates for voxel clusters using the unified entity architecture.
 */
class VoxelClusterSpawner {
  /**
   * Initializes the cluster spawner.
   *
   * @param {TextureAtlasManager} [atlasManager] Optional shared texture atlas manager instance.
   */
  constructor(atlasManager) {
    this.atlasManager = atlasManager || new TextureAtlasManager();
    this.clusters = new Map();
  }

  /**
   * Spawns a single dynamic voxel block using the unified entity representation.
   *
   * @param {object} dimension Target Minecraft dimension.
   * @param {object} loc 3D location in the dimension.
   * @param {string} blockId Namespaced block identifier.
   * @param {string} [clusterId] Optional cluster group identifier.
   * @returns {UnifiedVoxelEntity} UnifiedVoxelEntity instance.
   */
  spawnClusterBlock(dimension, loc, blockId, clusterId = 'default') {
    const rawEntity = dimension.spawnEntity(UnifiedVoxelEntity.ENTITY_IDENTIFIER, loc);
    const voxelEntity = new UnifiedVoxelEntity(rawEntity, blockId, this.atlasManager, clusterId);

    let clusterList = this.clusters.get(clusterId);
    if (!clusterList) {
      clusterList = [];
      this.clusters.set(clusterId, clusterList);
    }
    clusterList.push(voxelEntity);

    return voxelEntity;
  }

  /**
   * Updates an existing voxel entity to a new block type at runtime in O(1) time.
   *
   * @param {UnifiedVoxelEntity} voxelEntity Target unified voxel entity.
   * @param {string} newBlockId New namespaced block identifier.
   */
  updateClusterBlockType(voxelEntity, newBlockId) {
    voxelEntity.setBlockType(newBlockId);
  }

  /**
   * Retrieves all active voxel entities in a specific cluster.
   *
   * @param {string} clusterId Identifier of the cluster.
   * @returns {Array<UnifiedVoxelEntity>} Array of UnifiedVoxelEntity instances.
   */
  getClusterEntities(clusterId) {
    return this.clusters.get(clusterId) || [];
  }

  /**
   * Removes and cleans up all voxel entities within a cluster.
   *
   * @param {string} clusterId Identifier of the cluster to remove.
   */
  removeCluster(clusterId) {
    const entities = this.clusters.get(clusterId);
    if (entities) {
      for (const entity of entities) {
        entity.destroy();
      }
      this.clusters.delete(clusterId);
    }
  }

  /**
   * Retrieves the shared TextureAtlasManager instance.
   *
   * @returns {TextureAtlasManager} Active TextureAtlasManager.
   */
  getAtlasManager() {
    return this.atlasManager;
  }
}

/**
 * Public refactored export conforming directly to the issue specification.
 *
 * @param {object} dimension Target Minecraft dimension.
 * @param {object} loc 3D location vector.
 * @param {string} blockId Namespaced block identifier.
 * @param {VoxelClusterSpawner} [spawner] Optional shared spawner instance.
 * @returns {UnifiedVoxelEntity} UnifiedVoxelEntity instance.
 */
function spawnClusterBlock(dimension, loc, blockId, spawner) {
  const activeSpawner = spawner || new VoxelClusterSpawner();
  return activeSpawner.spawnClusterBlock(dimension, loc, blockId);
}

module.exports = { VoxelClusterSpawner, spawnClusterBlock };
