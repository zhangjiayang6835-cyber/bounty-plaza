"""Performance benchmarking and regression simulation for voxel rendering."""

from typing import Dict, List, Any
from packages.voxel_optimizer.models import Vector3D, RenderMetrics
from packages.voxel_optimizer.unified_spawner import UnifiedVoxelSpawner
from packages.voxel_optimizer.draw_call_optimizer import DrawCallOptimizer


class PerformanceBenchmarker:
    """Simulates and benchmarks contraption rendering workloads."""

    def __init__(self, optimizer: DrawCallOptimizer) -> None:
        """Initialize benchmarker with a configured DrawCallOptimizer.

        :param optimizer: Configured DrawCallOptimizer instance.
        """
        self._optimizer: DrawCallOptimizer = optimizer

    def run_benchmark_suite(
        self, block_type_counts: List[int], blocks_per_cluster: int = 120
    ) -> Dict[str, Any]:
        """Execute simulation sweeps across varying numbers of unique block types.

        :param block_type_counts: List of unique block type counts to evaluate.
        :param blocks_per_cluster: Total blocks instantiated in each cluster.
        :return: Dictionary containing benchmark results and summary metrics.
        """
        results: List[Dict[str, Any]] = []

        for count in block_type_counts:
            spawner = UnifiedVoxelSpawner()
            entities = []
            for i in range(blocks_per_cluster):
                block_id = f"contraption:block_{i % count}"
                loc = Vector3D(float(i % 10), float((i // 10) % 10), float(i // 100))
                entity = spawner.spawn_cluster_block(loc, block_id, "benchmark_cluster")
                entities.append(entity)

            metrics: RenderMetrics = self._optimizer.evaluate_metrics(entities)
            results.append({
                "unique_block_types": count,
                "total_blocks": blocks_per_cluster,
                "metrics": metrics.to_dict(),
            })

        return {
            "test_cases": results,
            "target_case_60_types": self.evaluate_target_issue_case(),
        }

    def evaluate_target_issue_case(self) -> Dict[str, Any]:
        """Evaluate the specific issue scenario: 60 unique block types in a contraption.

        :return: Metrics dictionary specifically for the 60 block types regression case.
        """
        spawner = UnifiedVoxelSpawner()
        entities = []
        for i in range(120):
            block_id = f"contraption:ruin_block_{i % 60}"
            loc = Vector3D(float(i), 64.0, 0.0)
            entity = spawner.spawn_cluster_block(loc, block_id, "contraption_ruin")
            entities.append(entity)

        metrics = self._optimizer.evaluate_metrics(entities)
        return metrics.to_dict()
