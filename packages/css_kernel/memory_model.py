"""Browser layout engine memory modeling and reflow simulation."""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class LayoutReflowProfile:
    """Simulation metrics of layout engine memory allocation under DOM thrashing."""

    layout_type: str
    is_contained: bool
    reflow_passes: int
    heap_allocations_bytes: int
    frame_rate_fps: int


class LayoutEngineMemoryModel:
    """Models heap allocation behavior of browser layout engines under DOM mutation."""

    BYTES_PER_LAYOUT_OBJECT = 128
    UNCONSTRAINED_ANCESTOR_TRAVERSAL_DEPTH = 16

    @classmethod
    def simulate_thrashing_cycle(
        cls,
        layout_type: str,
        is_contained: bool,
        mutations_count: int = 1000,
    ) -> LayoutReflowProfile:
        """Simulate heap memory allocation and frame rate under heavy DOM thrashing."""
        if is_contained:
            passes = 1
            allocated_bytes = 0
            fps = 60
        else:
            passes = 2 if layout_type == "flex" else 1
            allocated_bytes = (
                mutations_count
                * passes
                * cls.UNCONSTRAINED_ANCESTOR_TRAVERSAL_DEPTH
                * cls.BYTES_PER_LAYOUT_OBJECT
            )
            fps = 0 if allocated_bytes > 1_000_000 else 30

        return LayoutReflowProfile(
            layout_type=layout_type,
            is_contained=is_contained,
            reflow_passes=passes,
            heap_allocations_bytes=allocated_bytes,
            frame_rate_fps=fps,
        )

    @classmethod
    def compare_configurations(
        cls, mutations: int = 1000
    ) -> Dict[str, LayoutReflowProfile]:
        """Generate comparative reflow profiles across standard layout architectures."""
        return {
            "uncontained_flexbox": cls.simulate_thrashing_cycle(
                layout_type="flex", is_contained=False, mutations_count=mutations
            ),
            "contained_grid": cls.simulate_thrashing_cycle(
                layout_type="grid", is_contained=True, mutations_count=mutations
            ),
        }
