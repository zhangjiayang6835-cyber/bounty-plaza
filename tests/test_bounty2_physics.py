"""
Automated acceptance tests for Bounty #2: Karabut Glow-Discharge Nuclear Screening Simulator.
Run: pytest tests/test_bounty2_physics.py -v
"""
import json
import pathlib
import subprocess

import pytest

# Physical constants (acceptance criteria)
HG201_KEV = 1564.8
HG201_TOLERANCE = 0.5  # keV

D0_BOND_PM = 2.3
D0_BOND_TOLERANCE = 0.05  # pm

ST_EFFICIENCY_MIN = 0.92
KAPPA_PS = 16.6  # ps⁻¹

GAMMA_511_TOLERANCE_FRACTION = 0.15  # 15%
KARABUT_1995_511_REFERENCE = 1.0  # normalized to 1.0; submitter scales accordingly

MAX_RUNTIME_CPU_HOURS = 4.0

MANIFEST_CANDIDATES = [
    pathlib.Path("results/physics_manifest.json"),
    pathlib.Path(__file__).parent.parent / "results" / "physics_manifest.json",
]


def _find_manifest():
    for p in MANIFEST_CANDIDATES:
        if p.exists():
            return p
    return MANIFEST_CANDIDATES[0]


MANIFEST = _find_manifest()

pytestmark = pytest.mark.skipif(
    not MANIFEST.exists(),
    reason=f"{MANIFEST} not found — run the FCQC simulation first",
)


@pytest.fixture(scope="module")
def manifest():
    p = _find_manifest()
    if not p.exists():
        pytest.skip(f"{p} not found — run simulation first")
    with open(p, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Test 1: Hg-201 transition energy
# ---------------------------------------------------------------------------
def test_hg201_line_energy(manifest):
    energy = manifest["hg201"]["transition_keV"]
    assert abs(energy - HG201_KEV) <= HG201_TOLERANCE, (
        f"Hg-201 line {energy:.2f} keV, required {HG201_KEV} ± {HG201_TOLERANCE} keV"
    )


# ---------------------------------------------------------------------------
# Test 2: D(0) bond length
# ---------------------------------------------------------------------------
def test_d0_bond_length(manifest):
    bond_pm = manifest["d0_cluster"]["bond_length_pm"]
    assert abs(bond_pm - D0_BOND_PM) <= D0_BOND_TOLERANCE, (
        f"D(0) bond {bond_pm:.3f} pm, required {D0_BOND_PM} ± {D0_BOND_TOLERANCE} pm"
    )


# ---------------------------------------------------------------------------
# Test 3: ST-efficiency at κ = 16.6 ps⁻¹
# ---------------------------------------------------------------------------
def test_st_efficiency(manifest):
    results = manifest["spin_transfer"]
    # Find entry with kappa closest to 16.6
    target_entry = min(results, key=lambda x: abs(x["kappa_ps"] - KAPPA_PS))
    assert abs(target_entry["kappa_ps"] - KAPPA_PS) < 0.1, (
        f"No ST result near κ={KAPPA_PS} ps⁻¹ — closest: {target_entry['kappa_ps']}"
    )
    st_eff = target_entry["st_efficiency"]
    assert st_eff >= ST_EFFICIENCY_MIN, (
        f"ST-efficiency {st_eff:.4f} < {ST_EFFICIENCY_MIN} at κ={KAPPA_PS} ps⁻¹"
    )


# ---------------------------------------------------------------------------
# Test 4: 511 keV gamma line intensity
# ---------------------------------------------------------------------------
def test_gamma_511_intensity(manifest):
    predicted = manifest["gamma_511"]["relative_intensity"]
    reference = manifest["gamma_511"].get("karabut_1995_reference", KARABUT_1995_511_REFERENCE)
    deviation = abs(predicted - reference) / reference
    assert deviation <= GAMMA_511_TOLERANCE_FRACTION, (
        f"511 keV gamma intensity deviation {deviation:.1%} > {GAMMA_511_TOLERANCE_FRACTION:.0%}"
    )


# ---------------------------------------------------------------------------
# Test 5: Determinism (same seed → same output)
# ---------------------------------------------------------------------------
def test_simulation_determinism(manifest):
    seed = manifest.get("simulation_seed", 42)
    run_cmd = manifest.get("run_command")
    if not run_cmd:
        pytest.skip("run_command not specified in manifest")

    out1 = pathlib.Path("results/det_run1.json")
    out2 = pathlib.Path("results/det_run2.json")
    out1.parent.mkdir(parents=True, exist_ok=True)

    # Two independent runs with same seed
    subprocess.run(run_cmd + [f"--seed={seed}", f"--output={out1}"], check=True, timeout=300)
    subprocess.run(run_cmd + [f"--seed={seed}", f"--output={out2}"], check=True, timeout=300)

    with open(out1, "r", encoding="utf-8") as f1, open(out2, "r", encoding="utf-8") as f2:
        d1, d2 = json.load(f1), json.load(f2)

    assert d1 == d2, "Simulation is not deterministic: two identical-seed runs produced different output"


# ---------------------------------------------------------------------------
# Test 6: Runtime constraint
# ---------------------------------------------------------------------------
def test_runtime(manifest):
    runtime_hours = manifest.get("benchmark_runtime_hours")
    if runtime_hours is None:
        pytest.skip("benchmark_runtime_hours not reported in manifest")
    assert runtime_hours <= MAX_RUNTIME_CPU_HOURS, (
        f"Runtime {runtime_hours:.2f}h exceeds limit {MAX_RUNTIME_CPU_HOURS}h on reference hardware"
    )


# ---------------------------------------------------------------------------
# Test 7: arXiv preprint
# ---------------------------------------------------------------------------
def test_arxiv_preprint(manifest):
    arxiv_id = manifest.get("arxiv_preprint_id", "")
    assert arxiv_id, "arxiv_preprint_id not set in manifest"
    assert arxiv_id.startswith("2"), f"Invalid arXiv ID format: {arxiv_id}"


# Physical constants added from NGP 4.5 Technical Report (§Shield 1, LENR section)
D0_PHASE_S1_PM = 0.56          # ultra-dense D(0) s=1 internuclear distance
D0_PHASE_S1_TOLERANCE = 0.02   # pm
GAMMA_511_LIFETIME_US = 2.2    # positron quasi-particle lifetime, μs
GAMMA_511_LIFETIME_TOL = 0.1   # μs


# ---------------------------------------------------------------------------
# Test 8: D(0) ultra-dense phase s=1 bond length at 0.56 pm
# ---------------------------------------------------------------------------
def test_d0_phase_s1_bond(manifest):
    """D(0) s=1 phase internuclear distance must be 0.56 ± 0.02 pm (Holmlid)."""
    bond_s1 = manifest["d0_cluster"]["phase_s1_bond_length_pm"]
    assert abs(bond_s1 - D0_PHASE_S1_PM) <= D0_PHASE_S1_TOLERANCE, (
        f"D(0) s=1 phase bond {bond_s1:.3f} pm, required {D0_PHASE_S1_PM} ± {D0_PHASE_S1_TOLERANCE} pm"
    )


# ---------------------------------------------------------------------------
# Test 9: 511 keV positron quasi-particle lifetime ≈ 2.2 μs
# ---------------------------------------------------------------------------
def test_gamma_511_particle_lifetime(manifest):
    """Metastable leptonic quasi-particle lifetime must be 2.2 ± 0.1 μs (Heff marker)."""
    lifetime_us = manifest["gamma_511"]["positron_lifetime_us"]
    assert abs(lifetime_us - GAMMA_511_LIFETIME_US) <= GAMMA_511_LIFETIME_TOL, (
        f"511 keV positron lifetime {lifetime_us:.2f} μs, required {GAMMA_511_LIFETIME_US} ± {GAMMA_511_LIFETIME_TOL} μs"
    )
