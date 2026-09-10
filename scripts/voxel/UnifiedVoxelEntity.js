/**
 * Unified representation for dynamic voxel display entities in Minecraft Script API.
 */
export class UnifiedVoxelEntity {
    static ENTITY_IDENTIFIER = 'contraption:unified_voxel_display';
    underlyingEntity;
    atlasManager;
    blockId;
    atlasIndex;
    clusterId;
    /**
     * Constructs a UnifiedVoxelEntity wrapping a native Script API Entity.
     *
     * @param underlyingEntity The native Minecraft Script API entity instance.
     * @param blockId Initial namespaced block identifier.
     * @param atlasManager Shared texture atlas manager instance.
     * @param clusterId Unique cluster identifier.
     */
    constructor(underlyingEntity, blockId, atlasManager, clusterId = 'default') {
        this.underlyingEntity = underlyingEntity;
        this.atlasManager = atlasManager;
        this.blockId = blockId;
        this.clusterId = clusterId;
        this.atlasIndex = this.atlasManager.getAtlasIndex(blockId);
        this.synchronizeProperties();
    }
    /**
     * Synchronizes dynamic entity properties with the native Bedrock entity.
     */
    synchronizeProperties() {
        this.underlyingEntity.setProperty('contraption:block_id', this.blockId);
        this.underlyingEntity.setProperty('contraption:atlas_index', this.atlasIndex);
        this.underlyingEntity.setProperty('contraption:cluster_id', this.clusterId);
    }
    /**
     * Updates the block type at runtime in O(1) time without despawning the entity.
     *
     * @param newBlockId Target namespaced block identifier.
     */
    setBlockType(newBlockId) {
        if (this.blockId === newBlockId) {
            return;
        }
        this.blockId = newBlockId;
        this.atlasIndex = this.atlasManager.getAtlasIndex(newBlockId);
        this.synchronizeProperties();
    }
    /**
     * Retrieves the current namespaced block identifier.
     *
     * @returns Active block identifier.
     */
    getBlockId() {
        return this.blockId;
    }
    /**
     * Retrieves the current texture atlas index.
     *
     * @returns Current atlas index.
     */
    getAtlasIndex() {
        return this.atlasIndex;
    }
    /**
     * Retrieves the cluster identifier this voxel belongs to.
     *
     * @returns Cluster identifier.
     */
    getClusterId() {
        return this.clusterId;
    }
    /**
     * Retrieves the entity spatial location vector.
     *
     * @returns Vector3 location.
     */
    getLocation() {
        return this.underlyingEntity.location;
    }
    /**
     * Removes and cleans up the underlying entity.
     */
    destroy() {
        this.underlyingEntity.remove();
    }
}
