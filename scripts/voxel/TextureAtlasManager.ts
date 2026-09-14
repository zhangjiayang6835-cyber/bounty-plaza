import { BlockMetadata } from './types.js';

/**
 * Manages unified texture atlas coordinate mapping and index resolution for voxel blocks.
 */
export class TextureAtlasManager {
  private readonly gridSize: number;
  private readonly registry: Map<string, BlockMetadata>;
  private nextIndex: number;

  /**
   * Initializes texture atlas manager with specific grid dimensions.
   *
   * @param gridSize Number of texture cells per row and column in the atlas texture.
   */
  constructor(gridSize: number = 64) {
    this.gridSize = gridSize;
    this.registry = new Map<string, BlockMetadata>();
    this.nextIndex = 0;
    this.registerDefaultBlocks();
  }

  /**
   * Pre-populates common block types into the atlas registry.
   */
  private registerDefaultBlocks(): void {
    const defaults = [
      'minecraft:stone',
      'minecraft:dirt',
      'minecraft:grass_block',
      'minecraft:cobblestone',
      'minecraft:oak_planks',
      'minecraft:iron_block',
      'minecraft:gold_block',
      'minecraft:diamond_block',
      'minecraft:obsidian',
      'minecraft:glass',
      'minecraft:sand',
      'minecraft:gravel',
      'minecraft:bricks',
      'minecraft:mossy_cobblestone',
      'minecraft:netherrack',
      'minecraft:soul_sand'
    ];

    for (const blockId of defaults) {
      this.registerBlock(blockId);
    }
  }

  /**
   * Registers a block type and assigns deterministic UV atlas coordinates.
   *
   * @param blockId Unique namespaced block identifier.
   * @param customTexture Optional custom texture path.
   * @returns Metadata entry for the registered block.
   */
  public registerBlock(blockId: string, customTexture?: string): BlockMetadata {
    const existing = this.registry.get(blockId);
    if (existing) {
      return existing;
    }

    const index = this.nextIndex++;
    const maxCapacity = this.gridSize * this.gridSize;
    if (index >= maxCapacity) {
      throw new Error(`Texture atlas capacity exceeded: maximum ${maxCapacity} entries.`);
    }

    const col = index % this.gridSize;
    const row = Math.floor(index / this.gridSize);
    const cellSize = 1.0 / this.gridSize;

    const uMin = col * cellSize;
    const vMin = row * cellSize;
    const uMax = (col + 1) * cellSize;
    const vMax = (row + 1) * cellSize;

    const cleanName = blockId.replace(':', '_');
    const texturePath = customTexture || `textures/blocks/${cleanName}`;

    const metadata: BlockMetadata = {
      blockId,
      texturePath,
      atlasIndex: index,
      uMin,
      vMin,
      uMax,
      vMax
    };

    this.registry.set(blockId, metadata);
    return metadata;
  }

  /**
   * Resolves the atlas index for a block identifier, automatically registering it if novel.
   *
   * @param blockId Namespaced block identifier.
   * @returns Integer atlas index.
   */
  public getAtlasIndex(blockId: string): number {
    const entry = this.registry.get(blockId);
    if (entry) {
      return entry.atlasIndex;
    }
    return this.registerBlock(blockId).atlasIndex;
  }

  /**
   * Retrieves complete UV coordinate metadata for a block identifier.
   *
   * @param blockId Namespaced block identifier.
   * @returns BlockMetadata entry or undefined if not found.
   */
  public getMetadata(blockId: string): BlockMetadata | undefined {
    return this.registry.get(blockId);
  }

  /**
   * Returns the count of registered blocks in the atlas.
   *
   * @returns Total number of registered block entries.
   */
  public getRegisteredCount(): number {
    return this.registry.size;
  }
}
