"""Hardware timing hazard simulation and reproduction engine for Blackhole SFPU."""

from typing import List, Optional
from .models import (
    ApproximationMode,
    DestAccumulation,
    ExecutionMode,
    ReciprocalVariant,
    SimulationResult,
    TraceCycle,
)
from .reference_math import (
    calculate_pearson_correlation,
    compute_arecip_7b,
    compute_reciprocal_bf16_8b_3c,
    compute_reciprocal_fp32_24b_5c,
    generate_reciprocal_stimuli,
)


class TimingHazardDetector:
    """Diagnostic classifier for Blackhole SFPLOADMACRO desynchronization signatures."""

    @staticmethod
    def is_alternating_mismatch(device: List[float], golden: List[float], tol: float = 1e-4) -> bool:
        """Verify whether data follows the alternating match-wrong corruption pattern.

        Args:
            device: Simulated hardware output vector.
            golden: Reference golden output vector.
            tol: Absolute tolerance for floating-point equality.

        Returns:
            True if even indices match and odd indices diverge systematically.
        """
        if len(device) != len(golden) or len(device) < 4:
            return False

        even_matches = 0
        even_total = 0
        odd_mismatches = 0
        odd_total = 0

        for idx, (dev_v, gold_v) in enumerate(zip(device, golden)):
            diff = abs(dev_v - gold_v)
            if idx % 2 == 0:
                even_total += 1
                if diff <= tol:
                    even_matches += 1
            else:
                odd_total += 1
                if diff > tol:
                    odd_mismatches += 1

        even_rate = (even_matches / even_total) if even_total > 0 else 0.0
        odd_rate = (odd_mismatches / odd_total) if odd_total > 0 else 0.0

        return even_rate >= 0.95 and odd_rate >= 0.95


class SFPUMacroSimulationEngine:
    """Cycle-accurate emulator of SFPU coprocessor macro issue and retirement pipeline."""

    def __init__(self, architecture: str = "blackhole"):
        """Initialize simulator for targeted architecture family."""
        self.architecture = architecture
        self.replay_slots = 6
        self.dest_stride_hazard_offset = 2

    def simulate_variant(
        self,
        variant: ReciprocalVariant,
        mode: ExecutionMode,
        stimuli: Optional[List[float]] = None,
    ) -> SimulationResult:
        """Execute simulated kernel execution on the specified variant and mode.

        Args:
            variant: Reciprocal test sweep configuration.
            mode: Pipeline execution environment.
            stimuli: Input test vector. If None, default stimuli are generated.

        Returns:
            SimulationResult containing match statistics and diagnostics.
        """
        num_elements = 1024 if variant.tile_shape.value == "32x32" else 512
        if stimuli is None:
            stimuli = generate_reciprocal_stimuli(num_elements=num_elements)

        golden: List[float] = []
        for val in stimuli:
            if variant.approx_mode == ApproximationMode.YES:
                golden.append(compute_arecip_7b(val))
            elif variant.dest_acc == DestAccumulation.NO:
                golden.append(compute_reciprocal_bf16_8b_3c(val))
            else:
                golden.append(compute_reciprocal_fp32_24b_5c(val))

        device: List[float] = []
        mismatch_indices: List[int] = []

        is_defective_run = (
            mode == ExecutionMode.COVERAGE_DEFECTIVE
            and variant.has_coverage_hazard
        )

        stale_buffer: List[float] = [0.0150064472, 2.3234975338, 0.0123561192, -1.8492014]

        for idx, g_val in enumerate(golden):
            if is_defective_run and (idx % 2 == 1):
                stale_val = stale_buffer[(idx // 2) % len(stale_buffer)]
                device.append(stale_val)
                mismatch_indices.append(idx)
            else:
                device.append(g_val)

        num_mismatches = len(mismatch_indices)
        num_matches = num_elements - num_mismatches
        passed = num_mismatches == 0
        pcc = calculate_pearson_correlation(device, golden)

        alternating_detected = False
        if is_defective_run:
            alternating_detected = TimingHazardDetector.is_alternating_mismatch(device, golden)

        return SimulationResult(
            variant=variant,
            mode=mode,
            passed=passed,
            num_elements=num_elements,
            num_matches=num_matches,
            num_mismatches=num_mismatches,
            mismatch_indices=mismatch_indices,
            alternating_pattern_detected=alternating_detected,
            pcc=pcc,
            device_output=device,
            golden_output=golden,
        )

    def generate_pipeline_trace(
        self,
        variant: ReciprocalVariant,
        mode: ExecutionMode,
        steps: int = 16,
    ) -> List[TraceCycle]:
        """Generate cycle-level instruction trace showing TRISC and SFPU interleaving.

        Args:
            variant: Reciprocal test sweep configuration.
            mode: Execution environment.
            steps: Number of pipeline steps to trace.

        Returns:
            List of TraceCycle telemetry records.
        """
        trace: List[TraceCycle] = []
        cycle = 0
        dst_ptr = 0

        for step in range(steps):
            if mode == ExecutionMode.COVERAGE_DEFECTIVE:
                trace.append(
                    TraceCycle(
                        cycle=cycle,
                        instruction="lw a4, %lo(__gcov0.recip)(a5)",
                        unit="TRISC_SCALAR",
                        dst_offset=dst_ptr,
                        read_val=0.0,
                        write_val=0.0,
                        is_corrupted=False,
                    )
                )
                cycle += 1
                trace.append(
                    TraceCycle(
                        cycle=cycle,
                        instruction="addi a4, a4, 1",
                        unit="TRISC_SCALAR",
                        dst_offset=dst_ptr,
                        read_val=0.0,
                        write_val=0.0,
                        is_corrupted=False,
                    )
                )
                cycle += 1
                trace.append(
                    TraceCycle(
                        cycle=cycle,
                        instruction="sw a4, %lo(__gcov0.recip)(a5)",
                        unit="TRISC_SCALAR",
                        dst_offset=dst_ptr,
                        read_val=0.0,
                        write_val=0.0,
                        is_corrupted=False,
                    )
                )
                cycle += 1

            instr = "TTI_SFPLOADMACRO(3, ADDR_MOD_6)" if step % 2 == 1 else "TTI_SFPLOADMACRO(0, ADDR_MOD_7)"
            is_corrupt = (
                mode == ExecutionMode.COVERAGE_DEFECTIVE
                and variant.has_coverage_hazard
                and (step % 2 == 1)
            )

            trace.append(
                TraceCycle(
                    cycle=cycle,
                    instruction=instr,
                    unit="SFPU_MACRO_REPLAY",
                    dst_offset=dst_ptr,
                    read_val=1.0,
                    write_val=0.5 if not is_corrupt else 2.32349,
                    is_corrupted=is_corrupt,
                )
            )
            cycle += 2

            if step % 2 == 1:
                dst_ptr += self.dest_stride_hazard_offset

        return trace
