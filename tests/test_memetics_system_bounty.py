"""Unit tests for Memetics System Meta-Bounty & Cognitive Incursion Subsystem.
Resolves Issue #789: [BOUNTY] [$10000] [AGENTIC] [AI] Memetics System – The Cognitive Dominance of Thought Propagation.
"""

import pytest
from scripts.memetics_system_bounty import (
    MemeticContagionParams,
    MemeticsEpidemicSimulator,
    MemeticsBountyGenerator,
)


def test_memetic_contagion_parameters():
    params = MemeticContagionParams(
        transmission_rate_beta=0.40,
        recovery_rate_gamma=0.08,
        inoculation_factor_eta=0.80,
    )
    # R_0 = 0.40 / 0.08 = 5.0
    assert abs(params.reproduction_number_r0 - 5.0) < 1e-6
    # R_t = 5.0 * (1 - 0.80) = 1.0
    assert abs(params.effective_reproduction_number_rt - 1.0) < 1e-6


def test_memetics_epidemic_simulation():
    sim = MemeticsEpidemicSimulator(total_crew=100, initial_infected=2)
    history = sim.step_simulation(ticks=15)
    assert len(history) == 15
    last = history[-1]
    # Check conservation of total population count
    total = last["susceptible"] + last["infected"] + last["recovered"]
    assert abs(total - 100.0) < 1.0
    # Transmission occurs, so infected or recovered increases
    assert last["infected"] + last["recovered"] > 2.0


def test_bounty_generator_document_structure():
    gen = MemeticsBountyGenerator()
    doc = gen.build_bounty_document()
    assert "# [BOUNTY] [$10000] [AGENTIC] [AI] [OPIR] Memetics System" in doc
    assert "Overview" in doc
    assert "Reward & Payment" in doc
    assert "$10,000 USD" in doc
    assert "GBP, USD, BTC, EUR" in doc
    assert "Opire Singularity Council" in doc
    assert "Mathematical Contagion Engine" in doc
    assert "Memetic Transmission Vectors" in doc
    assert "Containment & Remediation Infrastructure" in doc
    assert "BYOND DreamMaker" in doc


def test_byond_dm_definitions():
    gen = MemeticsBountyGenerator()
    dm = gen.generate_byond_dm_definitions()
    assert "/datum/controller/subsystem/memetics" in dm
    assert "/obj/item/device/memetic_scrubber" in dm
    assert "/obj/structure/memetic_ward" in dm
    assert "proc/scrub_target" in dm
    assert "damping_efficiency = 0.85" in dm
