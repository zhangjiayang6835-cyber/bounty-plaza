import { Entity, Vector3 } from './types.js';
import { TextureAtlasManager } from './TextureAtlasManager.js';

/**
 * Unified representation for dynamic voxel display entities in Minecraft Script API.
 */
export class UnifiedVoxelEntity {
  public static readonly ENTITY_IDENTIFIER: string = 'contraption:unified_voxel_display';

  private readonly underlyingEntity: Entity;
  private readonly atlasManager: TextureAtlasManager;
  private blockId: string;
  private atlasIndex: number;
  private clusterId: string;

  /**
   * Constructs a UnifiedVoxelEntity wrapping a native Script API Entity.
   *
   * @param underlyingEntity The native Minecraft Script API entity instance.
   * @param blockId Initial namespaced block identifier.
   * @param atlasManager Shared texture atlas manager instance.
   * @param clusterId Unique cluster identifier.
   */
  constructor(
    underlyingEntity: Entity,
    blockId: string,
    atlasManager: TextureAtlasManager,
    clusterId: string = 'default'
  ) {
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
  private synchronizeProperties(): void {
    this.underlyingEntity.setProperty('contraption:block_id', this.blockId);
    this.underlyingEntity.setProperty('contraption:atlas_index', this.atlasIndex);
    this.underlyingEntity.setProperty('contraption:cluster_id', this.clusterId);
  }

  /**
   * Updates the block type at runtime in O(1) time without despawning the entity.
   *
   * @param newBlockId Target namespaced block identifier.
   */
  public setBlockType(newBlockId: string): void {
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
  public getBlockId(): string {
    return this.blockId;
  }

  /**
   * Retrieves the current texture atlas index.
   *
   * @returns Current atlas index.
   */
  public getAtlasIndex(): number {
    return this.atlasIndex;
  }

  /**
   * Retrieves the cluster identifier this voxel belongs to.
   *
   * @returns Cluster identifier.
   */
  public getClusterId(): string {
    return this.clusterId;
  }

  /**
   * Retrieves the entity spatial location vector.
   *
   * @returns Vector3 location.
   */
  public getLocation(): Vector3 {
    return this.underlyingEntity.location;
  }

  /**
   * Removes and cleans up the underlying entity.
   */
  public destroy(): void {
    this.underlyingEntity.remove();
  }
}
