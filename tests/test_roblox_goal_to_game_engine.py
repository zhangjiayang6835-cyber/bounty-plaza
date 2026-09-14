"""Unit tests for Roblox Studio Engine Path & Asset Pipeline Validator.
Resolves Issue #821: [Bounty] Engine Support: Roblox Studio path for Goal to Game skill ($2000 USD).
"""

import json
import pytest
from scripts.roblox_goal_to_game_engine import (
    RobloxGoalToGameEngine,
    ThrixelAssetDescriptor,
    MeshValidationResult,
    RobloxCollisionFidelity,
    ROBLOX_MAX_TRIANGLES,
    METERS_TO_STUDS_FACTOR,
)


@pytest.fixture
def engine():
    return RobloxGoalToGameEngine(project_name="LighthouseKeeperExperience")


@pytest.fixture
def valid_lighthouse_mesh():
    return ThrixelAssetDescriptor(
        asset_id="thrixel_lh_001",
        name="LighthouseTower",
        triangle_count=12500,
        dimensions_meters=(6.0, 24.0, 6.0),
        has_open_edges=False,
        has_texture_maps=True,
        collision_fidelity=RobloxCollisionFidelity.PRECISE_CONVEX,
    )


@pytest.fixture
def over_budget_mesh():
    return ThrixelAssetDescriptor(
        asset_id="thrixel_rock_dense",
        name="DetailedCliffFace",
        triangle_count=28500,  # Exceeds 20,000 limit
        dimensions_meters=(10.0, 8.0, 5.0),
        has_open_edges=False,
        has_texture_maps=True,
    )


@pytest.fixture
def non_watertight_mesh():
    return ThrixelAssetDescriptor(
        asset_id="thrixel_open_boat",
        name="RowboatHole",
        triangle_count=4500,
        dimensions_meters=(2.0, 1.0, 4.0),
        has_open_edges=True,  # Open boundaries / non-manifold
        has_texture_maps=True,
    )


def test_valid_mesh_passes_validation(engine, valid_lighthouse_mesh):
    """Verifies that an asset within triangle caps and watertight topology passes validation."""
    result = engine.validate_mesh(valid_lighthouse_mesh)
    assert result.passed is True
    assert len(result.errors) == 0
    assert result.is_watertight is True
    assert result.triangle_count <= ROBLOX_MAX_TRIANGLES


def test_over_budget_mesh_rejected(engine, over_budget_mesh):
    """Verifies that a mesh exceeding 20,000 triangles is caught and rejected."""
    result = engine.validate_mesh(over_budget_mesh)
    assert result.passed is False
    assert any("exceeds Roblox triangle cap" in err for err in result.errors)


def test_non_watertight_mesh_rejected(engine, non_watertight_mesh):
    """Verifies that a mesh with open non-manifold boundaries is caught."""
    result = engine.validate_mesh(non_watertight_mesh)
    assert result.passed is False
    assert result.is_watertight is False
    assert any("not watertight" in err for err in result.errors)


def test_dimension_to_stud_conversion(engine):
    """Verifies metric to Roblox stud conversion precision."""
    dims_m = (2.0, 5.0, 10.0)
    studs = engine.convert_dimensions_to_studs(dims_m)
    assert studs[0] == round(2.0 * METERS_TO_STUDS_FACTOR, 3)
    assert studs[1] == round(5.0 * METERS_TO_STUDS_FACTOR, 3)
    assert studs[2] == round(10.0 * METERS_TO_STUDS_FACTOR, 3)


def test_rojo_project_json_structure(engine):
    """Verifies Rojo default.project.json contains valid DataModel tree and paths."""
    rojo_json = engine.generate_rojo_project_json()
    parsed = json.loads(rojo_json)
    assert parsed["name"] == "LighthouseKeeperExperience"
    assert parsed["tree"]["$className"] == "DataModel"
    assert "ReplicatedStorage" in parsed["tree"]
    assert "ServerScriptService" in parsed["tree"]
    assert "Workspace" in parsed["tree"]


def test_luau_storm_controller_syntax(engine):
    """Verifies generated Luau script has strict typing and proper loop structure."""
    luau_code = engine.generate_luau_storm_controller()
    assert "--!strict" in luau_code
    assert "game:GetService(\"Lighting\")" in luau_code
    assert "onNightFall()" in luau_code
    assert "onDayBreak()" in luau_code
    assert "startCycle" in luau_code


def test_engine_markdown_guide_contents(engine):
    """Verifies that the markdown guide documents triangle caps, scale factors, and Rojo layout."""
    guide = engine.generate_engine_markdown_guide()
    assert "20,000 triangles" in guide
    assert "Watertight Manifold" in guide
    assert "1 meter = 3.571 studs" in guide
    assert "Rojo" in guide
