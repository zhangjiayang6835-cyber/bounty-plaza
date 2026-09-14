/**
 * Calculates draw call batching, state switch reduction, and FPS performance metrics.
 */
class DrawCallOptimizer {
  /**
   * Initializes the draw call optimizer with hardware characteristics.
   *
   * @param {number} [maxEntitiesPerBatch] Maximum instanced entity count per GPU draw call.
   * @param {number} [baseFrameTimeMs] Baseline frame time overhead in milliseconds.
   * @param {number} [drawCallCostMs] GPU driver overhead per distinct draw call in milliseconds.
   * @param {number} [geometryOverheadMs] Vertex processing overhead per block in milliseconds.
   */
  constructor(
    maxEntitiesPerBatch = 2048,
    baseFrameTimeMs = 4.0,
    drawCallCostMs = 0.75,
    geometryOverheadMs = 0.01
  ) {
    this.maxEntitiesPerBatch = maxEntitiesPerBatch;
    this.baseFrameTimeMs = baseFrameTimeMs;
    this.drawCallCostMs = drawCallCostMs;
    this.geometryOverheadMs = geometryOverheadMs;
  }

  /**
   * Computes comprehensive rendering metrics comparing naive vs unified architectures.
   *
   * @param {Array<object>} entities Array of unified voxel entities currently rendered.
   * @returns {object} RenderMetrics object.
   */
  evaluateMetrics(entities) {
    const totalBlocks = entities.length;
    const uniqueTypes = new Set();

    for (const entity of entities) {
      uniqueTypes.add(entity.getBlockId());
    }
    const uniqueBlockTypes = Math.max(1, uniqueTypes.size);

    const naiveDrawCalls = uniqueBlockTypes;
    const unifiedDrawCalls = Math.max(1, Math.ceil(totalBlocks / this.maxEntitiesPerBatch));

    const drawCallReductionPercent =
      naiveDrawCalls > 0
        ? Math.max(0, ((naiveDrawCalls - unifiedDrawCalls) / naiveDrawCalls) * 100)
        : 0;

    const naiveFrameTime =
      this.baseFrameTimeMs +
      naiveDrawCalls * this.drawCallCostMs +
      totalBlocks * this.geometryOverheadMs * 2.0;

    const unifiedFrameTime =
      this.baseFrameTimeMs +
      unifiedDrawCalls * this.drawCallCostMs +
      totalBlocks * this.geometryOverheadMs * 0.2;

    const naiveFps = Math.max(1, Math.min(120, Math.round(1000.0 / naiveFrameTime)));
    const unifiedFps = Math.max(1, Math.min(120, Math.round(1000.0 / unifiedFrameTime)));
    const fpsImprovementFactor = naiveFps > 0 ? unifiedFps / naiveFps : 1.0;

    return {
      totalBlocks,
      uniqueBlockTypes,
      naiveDrawCalls,
      unifiedDrawCalls,
      drawCallReductionPercent: Number(drawCallReductionPercent.toFixed(2)),
      naiveFps,
      unifiedFps,
      fpsImprovementFactor: Number(fpsImprovementFactor.toFixed(2))
    };
  }

  /**
   * Partitions an array of entities into unified draw call batches.
   *
   * @param {Array<object>} entities Array of unified voxel entities.
   * @returns {Array<Array<object>>} Array of entity batches for GPU submission.
   */
  batchEntities(entities) {
    const batches = [];
    for (let i = 0; i < entities.length; i += this.maxEntitiesPerBatch) {
      batches.push(entities.slice(i, i + this.maxEntitiesPerBatch));
    }
    return batches;
  }
}

module.exports = { DrawCallOptimizer };
