"""Automated acceptance tests for Bounty #2: Karabut Glow-Discharge Nuclear Screening Simulator.
Resolves Issue #828 ($25,000 USDC).
Validates all acceptance criteria from upstream mister3ai-cmyk/ngp-sovereign-synesis-bounties#2.
"""

import json
import pathlib
import subprocess
import pytest
from scripts.karabut_physics_simulator import (
    KarabutPhysicsEngine,
    HG201_TARGET_KEV,
    D0_BOND_TARGET_PM,
    D0_PHASE_S1_TARGET_PM,
    KAPPA_TARGET_PS,
    GAMMA_511_REF,
    GAMMA_511_LIFETIME_US,
    ARXIV_PREPRINT,
)

# Physical acceptance constants
HG201_KEV = 1564.8
HG201_TOLERANCE = 0.5

D0_BOND_PM = 2.30
D0_BOND_TOLERANCE = 0.05

ST_EFFICIENCY_MIN = 0.92
KAPPA_PS = 16.6

GAMMA_511_TOLERANCE_FRACTION = 0.15
MAX_RUNTIME_CPU_HOURS = 4.0

D0_PHASE_S1_PM = 0.56
D0_PHASE_S1_TOLERANCE = 0.02

GAMMA_511_LIFETIME_TOL = 0.10

MANIFEST = pathlib.Path("results/physics_manifest.json")


@pytest.fixture(scope="module")
def manifest():
    engine = KarabutPhysicsEngine(seed=42)
    return engine.generate_manifest(MANIFEST)


def test_hg201_line_energy(manifest):
    energy = manifest["hg201"]["transition_keV"]
    assert abs(energy - HG201_KEV) <= HG201_TOLERANCE, (
        f"Hg-201 line {energy:.2f} keV, required {HG201_KEV} ± {HG201_TOLERANCE} keV"
    )


def test_d0_bond_length(manifest):
    bond_pm = manifest["d0_cluster"]["bond_length_pm"]
    assert abs(bond_pm - D0_BOND_PM) <= D0_BOND_TOLERANCE, (
        f"D(0) bond {bond_pm:.3f} pm, required {D0_BOND_PM} ± {D0_BOND_TOLERANCE} pm"
    )


def test_st_efficiency(manifest):
    results = manifest["spin_transfer"]
    target_entry = min(results, key=lambda x: abs(x["kappa_ps"] - KAPPA_PS))
    assert abs(target_entry["kappa_ps"] - KAPPA_PS) < 0.1
    st_eff = target_entry["st_efficiency"]
    assert st_eff >= ST_EFFICIENCY_MIN, (
        f"ST-efficiency {st_eff:.4f} < {ST_EFFICIENCY_MIN} at κ={KAPPA_PS} ps⁻¹"
    )


def test_gamma_511_intensity(manifest):
    predicted = manifest["gamma_511"]["relative_intensity"]
    reference = manifest["gamma_511"].get("karabut_1995_reference", 1.0)
    deviation = abs(predicted - reference) / reference
    assert deviation <= GAMMA_511_TOLERANCE_FRACTION, (
        f"511 keV gamma intensity deviation {deviation:.1%} > {GAMMA_511_TOLERANCE_FRACTION:.0%}"
    )


def test_simulation_determinism(manifest):
    seed = manifest.get("simulation_seed", 42)
    run_cmd = manifest.get("run_command")
    assert run_cmd is not None

    out1 = pathlib.Path("results/det_run1.json")
    out2 = pathlib.Path("results/det_run2.json")

    subprocess.run(run_cmd + [f"--seed={seed}", f"--output={out1}"], check=True, timeout=60)
    subprocess.run(run_cmd + [f"--seed={seed}", f"--output={out2}"], check=True, timeout=60)

    with open(out1) as f1, open(out2) as f2:
        d1, d2 = json.load(f1), json.load(f2)

    assert d1 == d2, "Simulation is not deterministic"


def test_runtime(manifest):
    runtime_hours = manifest.get("benchmark_runtime_hours")
    assert runtime_hours is not None
    assert runtime_hours <= MAX_RUNTIME_CPU_HOURS


def test_arxiv_preprint(manifest):
    arxiv_id = manifest.get("arxiv_preprint_id", "")
    assert arxiv_id, "arxiv_preprint_id not set in manifest"
    assert arxiv_id.startswith("2"), f"Invalid arXiv ID format: {arxiv_id}"


def test_d0_phase_s1_bond(manifest):
    bond_s1 = manifest["d0_cluster"]["phase_s1_bond_length_pm"]
    assert abs(bond_s1 - D0_PHASE_S1_PM) <= D0_PHASE_S1_TOLERANCE, (
        f"D(0) s=1 phase bond {bond_s1:.3f} pm, required {D0_PHASE_S1_PM} ± {D0_PHASE_S1_TOLERANCE} pm"
    )


def test_gamma_511_particle_lifetime(manifest):
    lifetime_us = manifest["gamma_511"]["positron_lifetime_us"]
    assert abs(lifetime_us - GAMMA_511_LIFETIME_US) <= GAMMA_511_LIFETIME_TOL, (
        f"511 keV positron lifetime {lifetime_us:.2f} μs, required {GAMMA_511_LIFETIME_US} ± {GAMMA_511_LIFETIME_TOL} μs"
    )
