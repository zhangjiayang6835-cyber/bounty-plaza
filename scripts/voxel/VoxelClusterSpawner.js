import { TextureAtlasManager } from './TextureAtlasManager.js';
import { UnifiedVoxelEntity } from './UnifiedVoxelEntity.js';
/**
 * Manages spawning and runtime updates for voxel clusters using the unified entity architecture.
 */
export class VoxelClusterSpawner {
    atlasManager;
    clusters;
    /**
     * Initializes the cluster spawner.
     *
     * @param atlasManager Optional shared texture atlas manager instance.
     */
    constructor(atlasManager) {
        this.atlasManager = atlasManager || new TextureAtlasManager();
        this.clusters = new Map();
    }
    /**
     * Spawns a single dynamic voxel block using the unified entity representation.
     *
     * @param dimension Target Minecraft dimension.
     * @param loc 3D location in the dimension.
     * @param blockId Namespaced block identifier.
     * @param clusterId Optional cluster group identifier.
     * @returns UnifiedVoxelEntity instance.
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
     * @param voxelEntity Target unified voxel entity.
     * @param newBlockId New namespaced block identifier.
     */
    updateClusterBlockType(voxelEntity, newBlockId) {
        voxelEntity.setBlockType(newBlockId);
    }
    /**
     * Retrieves all active voxel entities in a specific cluster.
     *
     * @param clusterId Identifier of the cluster.
     * @returns Array of UnifiedVoxelEntity instances.
     */
    getClusterEntities(clusterId) {
        return this.clusters.get(clusterId) || [];
    }
    /**
     * Removes and cleans up all voxel entities within a cluster.
     *
     * @param clusterId Identifier of the cluster to remove.
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
     * @returns Active TextureAtlasManager.
     */
    getAtlasManager() {
        return this.atlasManager;
    }
}
/**
 * Public refactored export conforming directly to the issue specification.
 *
 * @param dimension Target Minecraft dimension.
 * @param loc 3D location vector.
 * @param blockId Namespaced block identifier.
 * @param spawner Optional shared spawner instance.
 * @returns UnifiedVoxelEntity instance.
 */
export function spawnClusterBlock(dimension, loc, blockId, spawner) {
    const activeSpawner = spawner || new VoxelClusterSpawner();
    return activeSpawner.spawnClusterBlock(dimension, loc, blockId);
}
