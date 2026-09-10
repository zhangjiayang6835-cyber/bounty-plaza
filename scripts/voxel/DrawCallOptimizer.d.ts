import { RenderMetrics } from './types.js';
import { UnifiedVoxelEntity } from './UnifiedVoxelEntity.js';
/**
 * Calculates draw call batching, state switch reduction, and FPS performance metrics.
 */
export declare class DrawCallOptimizer {
    private readonly maxEntitiesPerBatch;
    private readonly baseFrameTimeMs;
    private readonly drawCallCostMs;
    private readonly geometryOverheadMs;
    /**
     * Initializes the draw call optimizer with hardware characteristics.
     *
     * @param maxEntitiesPerBatch Maximum instanced entity count per GPU draw call.
     * @param baseFrameTimeMs Baseline frame time overhead in milliseconds.
     * @param drawCallCostMs GPU driver overhead per distinct draw call in milliseconds.
     * @param geometryOverheadMs Vertex processing overhead per block in milliseconds.
     */
    constructor(maxEntitiesPerBatch?: number, baseFrameTimeMs?: number, drawCallCostMs?: number, geometryOverheadMs?: number);
    /**
     * Computes comprehensive rendering metrics comparing naive vs unified architectures.
     *
     * @param entities Array of unified voxel entities currently rendered.
     * @returns RenderMetrics object.
     */
    evaluateMetrics(entities: UnifiedVoxelEntity[]): RenderMetrics;
    /**
     * Partitions an array of entities into unified draw call batches.
     *
     * @param entities Array of unified voxel entities.
     * @returns Array of entity batches for GPU submission.
     */
    batchEntities(entities: UnifiedVoxelEntity[]): UnifiedVoxelEntity[][];
}
