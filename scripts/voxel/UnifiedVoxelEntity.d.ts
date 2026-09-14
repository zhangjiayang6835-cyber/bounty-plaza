import { Entity, Vector3 } from './types.js';
import { TextureAtlasManager } from './TextureAtlasManager.js';
/**
 * Unified representation for dynamic voxel display entities in Minecraft Script API.
 */
export declare class UnifiedVoxelEntity {
    static readonly ENTITY_IDENTIFIER: string;
    private readonly underlyingEntity;
    private readonly atlasManager;
    private blockId;
    private atlasIndex;
    private clusterId;
    /**
     * Constructs a UnifiedVoxelEntity wrapping a native Script API Entity.
     *
     * @param underlyingEntity The native Minecraft Script API entity instance.
     * @param blockId Initial namespaced block identifier.
     * @param atlasManager Shared texture atlas manager instance.
     * @param clusterId Unique cluster identifier.
     */
    constructor(underlyingEntity: Entity, blockId: string, atlasManager: TextureAtlasManager, clusterId?: string);
    /**
     * Synchronizes dynamic entity properties with the native Bedrock entity.
     */
    private synchronizeProperties;
    /**
     * Updates the block type at runtime in O(1) time without despawning the entity.
     *
     * @param newBlockId Target namespaced block identifier.
     */
    setBlockType(newBlockId: string): void;
    /**
     * Retrieves the current namespaced block identifier.
     *
     * @returns Active block identifier.
     */
    getBlockId(): string;
    /**
     * Retrieves the current texture atlas index.
     *
     * @returns Current atlas index.
     */
    getAtlasIndex(): number;
    /**
     * Retrieves the cluster identifier this voxel belongs to.
     *
     * @returns Cluster identifier.
     */
    getClusterId(): string;
    /**
     * Retrieves the entity spatial location vector.
     *
     * @returns Vector3 location.
     */
    getLocation(): Vector3;
    /**
     * Removes and cleans up the underlying entity.
     */
    destroy(): void;
}
