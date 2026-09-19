"""Unified orchestration facade integrating cosmological simulation, Brainfuck execution, and settlement."""

import hashlib
from typing import Optional
from .brainfuck import BrainfuckOptimizer, BrainfuckProgramSynthesizer, BrainfuckVM
from .cosmology import CosmicSimulation
from .models import (
    BrainfuckExecutionResult,
    CosmologicalParameters,
    SettlementReceipt,
    SimulationState,
    TokenMetrics,
    UniversalExecutionReport,
)
from .settlement import EleventyGazillionSettlementEngine
from .token_accounting import TokenAccountingEngine


class UniverseSimulationGateway:
    """Orchestrates cosmological evolution, Brainfuck Turing verification, and financial settlement."""

    @classmethod
    def execute_complete_pipeline(
        cls,
        parameters: Optional[CosmologicalParameters] = None,
        particle_count: int = 64,
        simulation_steps: int = 5,
        target_message: str = "PPPDUD UNIVERSE SIMULATION",
        minimum_token_threshold: int = 250,
    ) -> UniversalExecutionReport:
        """Executes cosmological steps, compiles and runs Brainfuck, meters tokens, and settles bounty."""
        sim = CosmicSimulation(parameters=parameters, particle_count=particle_count)
        last_state: Optional[SimulationState] = None
        for _ in range(max(simulation_steps, 1)):
            last_state = sim.step_leapfrog(delta_time_myr=10.0)

        bf_source = BrainfuckProgramSynthesizer.synthesize_emitter(target_message)
        bytecode = BrainfuckOptimizer.compile_bytecode(bf_source)
        vm = BrainfuckVM()
        bf_result: BrainfuckExecutionResult = vm.execute(bytecode)

        payload_to_meter = (
            f"COSMIC_EPOCH:{last_state.redshift:.4f}\n"
            f"SCALE_FACTOR:{last_state.scale_factor:.6f}\n"
            f"HUBBLE:{last_state.hubble_parameter:.2f}\n"
            f"HORIZON_ENTROPY:{last_state.horizon_entropy:.2e}\n"
            f"BRAINFUCK_SOURCE:{bf_source}\n"
            f"BRAINFUCK_EMITTED:{bf_result.output_text}\n"
        )
        token_metrics: TokenMetrics = TokenAccountingEngine.analyze_token_expenditure(
            payload=payload_to_meter,
            minimum_token_threshold=minimum_token_threshold,
        )

        settlement_receipt: SettlementReceipt = EleventyGazillionSettlementEngine.calculate_settlement()

        combined_hash_input = (
            f"{last_state.cosmic_time_myr}|"
            f"{bf_result.cycles_executed}|"
            f"{token_metrics.estimated_bpe_tokens}|"
            f"{settlement_receipt.receipt_sha256}"
        )
        report_digest = hashlib.sha256(combined_hash_input.encode("utf-8")).hexdigest()

        report = UniversalExecutionReport(
            simulation_state=last_state,
            brainfuck_result=bf_result,
            token_metrics=token_metrics,
            settlement_receipt=settlement_receipt,
            report_digest=report_digest,
        )
        return report
