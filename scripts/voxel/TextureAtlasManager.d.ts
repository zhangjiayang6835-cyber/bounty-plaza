import { BlockMetadata } from './types.js';
/**
 * Manages unified texture atlas coordinate mapping and index resolution for voxel blocks.
 */
export declare class TextureAtlasManager {
    private readonly gridSize;
    private readonly registry;
    private nextIndex;
    /**
     * Initializes texture atlas manager with specific grid dimensions.
     *
     * @param gridSize Number of texture cells per row and column in the atlas texture.
     */
    constructor(gridSize?: number);
    /**
     * Pre-populates common block types into the atlas registry.
     */
    private registerDefaultBlocks;
    /**
     * Registers a block type and assigns deterministic UV atlas coordinates.
     *
     * @param blockId Unique namespaced block identifier.
     * @param customTexture Optional custom texture path.
     * @returns Metadata entry for the registered block.
     */
    registerBlock(blockId: string, customTexture?: string): BlockMetadata;
    /**
     * Resolves the atlas index for a block identifier, automatically registering it if novel.
     *
     * @param blockId Namespaced block identifier.
     * @returns Integer atlas index.
     */
    getAtlasIndex(blockId: string): number;
    /**
     * Retrieves complete UV coordinate metadata for a block identifier.
     *
     * @param blockId Namespaced block identifier.
     * @returns BlockMetadata entry or undefined if not found.
     */
    getMetadata(blockId: string): BlockMetadata | undefined;
    /**
     * Returns the count of registered blocks in the atlas.
     *
     * @returns Total number of registered block entries.
     */
    getRegisteredCount(): number;
}
