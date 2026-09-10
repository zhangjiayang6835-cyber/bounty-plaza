/**
 * Three-dimensional Cartesian coordinate vector.
 */
export interface Vector3 {
    x: number;
    y: number;
    z: number;
}
/**
 * Metadata definition for a voxel block registered in the system.
 */
export interface BlockMetadata {
    blockId: string;
    texturePath: string;
    atlasIndex: number;
    uMin: number;
    vMin: number;
    uMax: number;
    vMax: number;
}
/**
 * Interface representing a Minecraft dimension instance.
 */
export interface Dimension {
    id: string;
    spawnEntity(identifier: string, location: Vector3): Entity;
}
/**
 * Interface representing a Minecraft entity instance.
 */
export interface Entity {
    id: string;
    typeId: string;
    location: Vector3;
    setProperty(identifier: string, value: string | number | boolean): void;
    getProperty(identifier: string): string | number | boolean | undefined;
    triggerEvent(eventName: string): void;
    remove(): void;
}
/**
 * Voxel rendering cluster metrics comparing naive vs unified architectures.
 */
export interface RenderMetrics {
    totalBlocks: number;
    uniqueBlockTypes: number;
    naiveDrawCalls: number;
    unifiedDrawCalls: number;
    drawCallReductionPercent: number;
    naiveFps: number;
    unifiedFps: number;
    fpsImprovementFactor: number;
}
