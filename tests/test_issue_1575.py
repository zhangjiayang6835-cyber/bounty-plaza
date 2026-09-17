"""
Comprehensive test suite verifying OmniUniverse implementation for Issue #1575.
"""

import ast
import json
import math
import os
import pytest
from packages.omni_universe.blockly import UniverseBlockly
from packages.omni_universe.constants import (
    ASTRONOMICAL_UNIT,
    CMB_TEMPERATURE_NOW,
    EARTH_MASS,
    GRAVITATIONAL_CONSTANT,
    HUBBLE_CONSTANT,
    SOLAR_MASS,
    SPEED_OF_LIGHT,
)
from packages.omni_universe.cosmology import CosmologicalEngine
from packages.omni_universe.generator import (
    DeterministicRNG,
    ProceduralUniverseGenerator,
    SpatialGridIndex,
)
from packages.omni_universe.models import (
    CelestialEntity,
    CelestialType,
    CosmicEpoch,
    GalaxyMorphology,
    SpectralClass,
    Vector3D,
)
from packages.omni_universe.physics import GravitationalSimulator
from packages.omni_universe.quantum_matter import (
    PeriodicTable,
    StandardModelInventory,
    StellarNucleosynthesisEngine,
)
from packages.omni_universe.settlement import QuadrillionSettlementEngine
from packages.omni_universe.universe_gateway import OmniUniverse


def test_vector_algebra():
    """Verify 3D Cartesian vector mathematics and operations."""
    v1 = Vector3D(1.0, 2.0, 3.0)
    v2 = Vector3D(4.0, 5.0, 6.0)

    v_add = v1 + v2
    assert (v_add.x, v_add.y, v_add.z) == (5.0, 7.0, 9.0)

    v_sub = v2 - v1
    assert (v_sub.x, v_sub.y, v_sub.z) == (3.0, 3.0, 3.0)

    v_scaled = v1 * 2.5
    assert (v_scaled.x, v_scaled.y, v_scaled.z) == (2.5, 5.0, 7.5)

    v_div = v2 / 2.0
    assert (v_div.x, v_div.y, v_div.z) == (2.0, 2.5, 3.0)

    with pytest.raises(ZeroDivisionError):
        _ = v1 / 0.0

    assert (-v1).x == -1.0
    assert v1.magnitude_squared() == 14.0
    assert math.isclose(v1.magnitude(), math.sqrt(14.0))

    unit = v1.normalize()
    assert math.isclose(unit.magnitude(), 1.0)

    assert v1.dot(v2) == 1.0 * 4.0 + 2.0 * 5.0 + 3.0 * 6.0
    cross = v1.cross(v2)
    assert (cross.x, cross.y, cross.z) == (-3.0, 6.0, -3.0)

    v_dict = v1.to_dict()
    v_reconstructed = Vector3D.from_dict(v_dict)
    assert v_reconstructed == v1


def test_gravitational_acceleration_and_softening():
    """Verify Plummer-softened gravitational acceleration formula."""
    sim = GravitationalSimulator(softening_length=1e3)
    b1 = CelestialEntity(
        entity_id="b1",
        name="Mass 1",
        entity_type=CelestialType.STAR,
        mass=SOLAR_MASS,
        radius=1e6,
        position=Vector3D(0.0, 0.0, 0.0),
    )
    b2 = CelestialEntity(
        entity_id="b2",
        name="Mass 2",
        entity_type=CelestialType.PLANET,
        mass=EARTH_MASS,
        radius=1e5,
        position=Vector3D(ASTRONOMICAL_UNIT, 0.0, 0.0),
    )

    accel = sim.compute_acceleration(b2, [b1, b2])
    expected_accel = (GRAVITATIONAL_CONSTANT * SOLAR_MASS) / (ASTRONOMICAL_UNIT ** 2)
    assert math.isclose(accel.x, -expected_accel, rel_tol=1e-3)
    assert accel.y == 0.0
    assert accel.z == 0.0


def test_keplerian_and_relativistic_physics():
    """Verify Keplerian orbital formulas and Schwarzschild event horizons."""
    earth_orb_v = GravitationalSimulator.keplerian_orbital_velocity(SOLAR_MASS, ASTRONOMICAL_UNIT)
    assert 29000.0 < earth_orb_v < 31000.0

    period_sec = GravitationalSimulator.orbital_period(SOLAR_MASS, ASTRONOMICAL_UNIT)
    year_sec = 365.25 * 86400.0
    assert math.isclose(period_sec, year_sec, rel_tol=0.01)

    v_esc = GravitationalSimulator.escape_velocity(SOLAR_MASS, ASTRONOMICAL_UNIT)
    assert math.isclose(v_esc, math.sqrt(2.0) * earth_orb_v, rel_tol=1e-5)

    rs_sun = GravitationalSimulator.schwarzschild_radius(SOLAR_MASS)
    assert 2900.0 < rs_sun < 3000.0


def test_stellar_astrophysics_scaling():
    """Verify stellar mass-luminosity relation and Stefan-Boltzmann temperatures."""
    lum = GravitationalSimulator.stellar_luminosity_from_mass(SOLAR_MASS)
    assert math.isclose(lum, 3.828e26, rel_tol=1e-5)

    temp_sun = GravitationalSimulator.effective_temperature(3.828e26, 6.957e8)
    assert 5700.0 < temp_sun < 5850.0

    spec_g = GravitationalSimulator.determine_spectral_class(temp_sun)
    assert spec_g == SpectralClass.G

    spec_o = GravitationalSimulator.determine_spectral_class(35000.0)
    assert spec_o == SpectralClass.O

    spec_m = GravitationalSimulator.determine_spectral_class(3000.0)
    assert spec_m == SpectralClass.M


def test_cosmological_epochs():
    """Verify epoch transitions across cosmological timescales."""
    assert CosmologicalEngine.get_epoch_for_age(1e-40) == CosmicEpoch.INFLATIONARY
    assert CosmologicalEngine.get_epoch_for_age(100.0) == CosmicEpoch.PHOTON_NUCLEOSYNTHESIS
    assert CosmologicalEngine.get_epoch_for_age(1e17) == CosmicEpoch.STELLIFEROUS
    assert CosmologicalEngine.get_epoch_for_age(1e55) == CosmicEpoch.BLACK_HOLE_ERA
    assert CosmologicalEngine.get_epoch_for_age(1e115) == CosmicEpoch.HEAT_DEATH


def test_cosmological_expansion_and_cmb():
    """Verify Hubble parameter scaling and CMB cooling with redshift."""
    cosmo = CosmologicalEngine()
    h0 = cosmo.hubble_parameter_at_redshift(0.0)
    assert math.isclose(h0, HUBBLE_CONSTANT, rel_tol=1e-3)

    h1 = cosmo.hubble_parameter_at_redshift(1.0)
    assert h1 > h0

    t_cmb_0 = CosmologicalEngine.cmb_temperature_at_redshift(0.0)
    assert math.isclose(t_cmb_0, CMB_TEMPERATURE_NOW, rel_tol=1e-5)

    t_cmb_1 = CosmologicalEngine.cmb_temperature_at_redshift(1.0)
    assert math.isclose(t_cmb_1, 2.0 * CMB_TEMPERATURE_NOW, rel_tol=1e-5)

    scale = CosmologicalEngine.cosmic_scale_factor(1.0)
    assert math.isclose(scale, 0.5, rel_tol=1e-5)

    energy = cosmo.cosmic_energy_inventory()
    assert 0.65 < energy["dark_energy"] < 0.72
    assert 0.28 < energy["matter_total"] < 0.35


def test_bekenstein_hawking_entropy():
    """Verify Bekenstein-Hawking black hole entropy scaling."""
    s_smbh = CosmologicalEngine.bekenstein_hawking_entropy(4e6 * SOLAR_MASS)
    s_stellar = CosmologicalEngine.bekenstein_hawking_entropy(10.0 * SOLAR_MASS)
    assert s_smbh > s_stellar
    assert s_stellar > 0.0


def test_standard_model_and_nucleosynthesis():
    """Verify fundamental particles, periodic elements, and stellar nucleosynthesis yields."""
    particles = StandardModelInventory.get_particles()
    assert len(particles) == 17
    assert any(p.name == "higgs_boson" for p in particles)

    hydrogen = PeriodicTable.find_by_symbol("H")
    assert hydrogen is not None
    assert hydrogen.atomic_number == 1
    assert hydrogen.primordial is True

    iron = PeriodicTable.find_by_symbol("Fe")
    assert iron is not None
    assert iron.atomic_number == 26

    fusion_early = StellarNucleosynthesisEngine.simulate_stellar_fusion(1.0, 0.1)
    assert fusion_early["H"] > 0.6

    fusion_late = StellarNucleosynthesisEngine.simulate_stellar_fusion(15.0, 0.95)
    assert "Fe" in fusion_late

    remnant_low, _ = StellarNucleosynthesisEngine.simulate_supernova(5.0)
    assert remnant_low == CelestialType.STAR

    remnant_ns, yields_ns = StellarNucleosynthesisEngine.simulate_supernova(15.0)
    assert remnant_ns == CelestialType.NEUTRON_STAR
    assert "Au" in yields_ns

    remnant_bh, yields_bh = StellarNucleosynthesisEngine.simulate_supernova(35.0)
    assert remnant_bh == CelestialType.BLACK_HOLE
    assert "U" in yields_bh


def test_deterministic_procedural_universe_generation():
    """Verify deterministic universe synthesis with SHA-256 PRNG."""
    gen1 = ProceduralUniverseGenerator(seed="deterministic_test_seed_42")
    gen2 = ProceduralUniverseGenerator(seed="deterministic_test_seed_42")

    gal1 = gen1.generate_galaxy("gal1", "MilkyWay", GalaxyMorphology.SPIRAL, stellar_count=3)
    gal2 = gen2.generate_galaxy("gal1", "MilkyWay", GalaxyMorphology.SPIRAL, stellar_count=3)

    assert len(gal1) == len(gal2)
    for b1, b2 in zip(gal1, gal2):
        assert b1.entity_id == b2.entity_id
        assert math.isclose(b1.mass, b2.mass)
        assert math.isclose(b1.position.x, b2.position.x)
        assert math.isclose(b1.position.y, b2.position.y)


def test_spatial_grid_index_radius_search():
    """Verify 3D spatial hash grid insertion and proximity query filtering."""
    grid = SpatialGridIndex(cell_size=10.0 * ASTRONOMICAL_UNIT)
    star = CelestialEntity(
        entity_id="star_center",
        name="Center Star",
        entity_type=CelestialType.STAR,
        mass=SOLAR_MASS,
        radius=1e8,
        position=Vector3D(0.0, 0.0, 0.0),
    )
    p_near = CelestialEntity(
        entity_id="p_near",
        name="Near Planet",
        entity_type=CelestialType.PLANET,
        mass=EARTH_MASS,
        radius=1e6,
        position=Vector3D(1.0 * ASTRONOMICAL_UNIT, 0.0, 0.0),
    )
    p_far = CelestialEntity(
        entity_id="p_far",
        name="Far Planet",
        entity_type=CelestialType.PLANET,
        mass=EARTH_MASS,
        radius=1e6,
        position=Vector3D(100.0 * ASTRONOMICAL_UNIT, 0.0, 0.0),
    )

    grid.insert(star)
    grid.insert(p_near)
    grid.insert(p_far)

    found = grid.query_radius(Vector3D(0.0, 0.0, 0.0), 5.0 * ASTRONOMICAL_UNIT)
    found_ids = {e.entity_id for e in found}
    assert "star_center" in found_ids
    assert "p_near" in found_ids
    assert "p_far" not in found_ids


def test_issue_1575_quadrillion_settlement_arithmetic():
    """Verify arbitrary-precision financial settlement for Issue #1575."""
    evm_wallet = "0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89"
    stellar_wallet = "GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC"

    assert QuadrillionSettlementEngine.validate_evm_address(evm_wallet)
    assert QuadrillionSettlementEngine.validate_stellar_address(stellar_wallet)
    assert not QuadrillionSettlementEngine.validate_evm_address("0xInvalid")
    assert not QuadrillionSettlementEngine.validate_stellar_address("BadStellarKey")

    receipt = QuadrillionSettlementEngine.calculate_settlement(
        evm_address=evm_wallet,
        stellar_address=stellar_wallet,
    )

    assert receipt.issue_id == 1575
    assert receipt.nominal_bounty_usd == "999999999999999999"
    assert receipt.platform_coins_minted == "1250000000000000000"
    assert receipt.contributor_share_ratio == "0.85"
    assert receipt.contributor_coins_credited == "1062500000000000000.00"
    assert receipt.net_contributor_payout_usd == "765000000000000000.00"
    assert receipt.platform_treasury_fee_usd == "234999999999999999.00"
    assert receipt.evm_payout_address == evm_wallet
    assert receipt.stellar_payout_address == stellar_wallet
    assert len(receipt.settlement_hash) == 64


def test_omni_universe_simulation_lifecycle():
    """Verify high-level OmniUniverse gateway, physics stepping, and supernova trigger."""
    cosmos = OmniUniverse(seed="universe_lifecycle_test")
    assert cosmos.epoch == CosmicEpoch.STELLIFEROUS

    cosmos.spawn_galaxy("Andromeda", morphology="spiral", stars=4)
    all_bodies = cosmos.get_all_entities()
    assert len(all_bodies) > 4

    stars = cosmos.find_entities_by_type(CelestialType.STAR)
    assert len(stars) >= 4
    target_star = stars[0]

    initial_pos = target_star.position
    cosmos.step(years=100.0, substeps=2)
    assert target_star.position != initial_pos

    remnant, yields = cosmos.trigger_supernova(target_star.entity_id)
    assert remnant.entity_type in (
        CelestialType.STAR,
        CelestialType.NEUTRON_STAR,
        CelestialType.BLACK_HOLE,
    )
    assert len(yields) > 0

    receipt = cosmos.execute_bounty_settlement(
        evm_address="0xF46C9F6d70C50BF81ef3588AB523a90a594a2F89",
        stellar_address="GCL6OXAMLD75BMTINA6EMRUDWK5THQUSHMYNLSNBCJAPZJHNYJTUNIBC",
    )
    assert receipt.net_contributor_payout_usd == "765000000000000000.00"

    summary = cosmos.get_summary()
    assert summary["total_entities"] > 0
    assert "dark_energy" in summary["cosmic_energy"]


def test_blockly_schema_and_code_generation():
    """Verify Blockly visual toolboxes, schemas, and polyglot code generation."""
    json_blocks = UniverseBlockly.get_block_definitions_json()
    parsed = json.loads(json_blocks)
    assert isinstance(parsed, list)
    assert len(parsed) >= 5

    xml_toolbox = UniverseBlockly.get_toolbox_xml()
    assert "<category name=\"OmniUniverse\"" in xml_toolbox

    py_code = UniverseBlockly.transpile_create_cosmos("seed_1", "stelliferous", 13.8, "python")
    assert "OmniUniverse(seed=\"seed_1\")" in py_code

    js_code = UniverseBlockly.transpile_create_cosmos("seed_1", "stelliferous", 13.8, "javascript")
    assert "new OmniUniverse(\"seed_1\")" in js_code


def test_ast_security_anti_cheating():
    """Verify codebase adherence to anti-cheating and AST security standards."""
    pkg_dir = os.path.join(os.path.dirname(__file__), "..", "packages", "omni_universe")
    banned_calls = {"eval", "exec", "compile", "open", "__import__"}

    for root, _, files in os.walk(pkg_dir):
        for file in files:
            if not file.endswith(".py"):
                continue
            filepath = os.path.join(root, file)
            with open(filepath, "r", encoding="utf-8") as f:
                tree = ast.parse(f.read(), filename=filepath)

            for node in ast.walk(tree):
                if isinstance(node, ast.Call):
                    if isinstance(node.func, ast.Name):
                        assert node.func.id not in banned_calls, (
                            f"Banned function call '{node.func.id}' in {file}"
                        )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        assert alias.name not in {"os", "subprocess", "sys", "ctypes"}, (
                            f"Banned module import '{alias.name}' in {file}"
                        )
                if isinstance(node, ast.ImportFrom):
                    assert node.module not in {"os", "subprocess", "sys", "ctypes"}, (
                        f"Banned module from-import '{node.module}' in {file}"
                    )
