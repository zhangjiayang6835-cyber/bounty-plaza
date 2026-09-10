import { Dimension, Vector3 } from './types.js';
import { TextureAtlasManager } from './TextureAtlasManager.js';
import { UnifiedVoxelEntity } from './UnifiedVoxelEntity.js';
/**
 * Manages spawning and runtime updates for voxel clusters using the unified entity architecture.
 */
export declare class VoxelClusterSpawner {
    private readonly atlasManager;
    private readonly clusters;
    /**
     * Initializes the cluster spawner.
     *
     * @param atlasManager Optional shared texture atlas manager instance.
     */
    constructor(atlasManager?: TextureAtlasManager);
    /**
     * Spawns a single dynamic voxel block using the unified entity representation.
     *
     * @param dimension Target Minecraft dimension.
     * @param loc 3D location in the dimension.
     * @param blockId Namespaced block identifier.
     * @param clusterId Optional cluster group identifier.
     * @returns UnifiedVoxelEntity instance.
     */
    spawnClusterBlock(dimension: Dimension, loc: Vector3, blockId: string, clusterId?: string): UnifiedVoxelEntity;
    /**
     * Updates an existing voxel entity to a new block type at runtime in O(1) time.
     *
     * @param voxelEntity Target unified voxel entity.
     * @param newBlockId New namespaced block identifier.
     */
    updateClusterBlockType(voxelEntity: UnifiedVoxelEntity, newBlockId: string): void;
    /**
     * Retrieves all active voxel entities in a specific cluster.
     *
     * @param clusterId Identifier of the cluster.
     * @returns Array of UnifiedVoxelEntity instances.
     */
    getClusterEntities(clusterId: string): UnifiedVoxelEntity[];
    /**
     * Removes and cleans up all voxel entities within a cluster.
     *
     * @param clusterId Identifier of the cluster to remove.
     */
    removeCluster(clusterId: string): void;
    /**
     * Retrieves the shared TextureAtlasManager instance.
     *
     * @returns Active TextureAtlasManager.
     */
    getAtlasManager(): TextureAtlasManager;
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
export declare function spawnClusterBlock(dimension: Dimension, loc: Vector3, blockId: string, spawner?: VoxelClusterSpawner): UnifiedVoxelEntity;
