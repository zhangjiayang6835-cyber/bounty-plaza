"""Unit tests for SS13 Floor Turf Render Plane & Z-Ordering Fix.
Resolves Issue #603: [bounty] [$1000] [MISSION CRITICAL!!] floor turfs render over all other sprites.
"""

import pytest
from scripts.ss13_render_plane_layer_fix import (
    RenderPlane,
    RenderLayer,
    VisualAtom,
    RenderCompositorPipeline,
)


def test_render_plane_and_layer_hierarchy():
    # Verify canonical depth hierarchy: FLOOR_PLANE < GAME_PLANE < LIGHTING_PLANE
    assert RenderPlane.FLOOR_PLANE.value < RenderPlane.GAME_PLANE.value
    assert RenderPlane.GAME_PLANE.value < RenderPlane.LIGHTING_PLANE.value
    assert RenderLayer.TURF_LAYER.value < RenderLayer.OBJ_LAYER.value
    assert RenderLayer.OBJ_LAYER.value < RenderLayer.MOB_LAYER.value


def test_visual_atom_depth_key_calculation():
    turf = VisualAtom(
        atom_id="turf_01",
        name="Plasteel Floor",
        atom_type="turf",
        plane=RenderPlane.FLOOR_PLANE.value,
        layer=RenderLayer.TURF_LAYER.value,
        coord=(10, 10, 1)
    )
    mob = VisualAtom(
        atom_id="mob_clown",
        name="Clown",
        atom_type="mob",
        plane=RenderPlane.GAME_PLANE.value,
        layer=RenderLayer.MOB_LAYER.value,
        coord=(10, 10, 1)
    )
    # Turf must have lower depth key than mob
    assert turf.calculate_depth_key() < mob.calculate_depth_key()


def test_audit_and_correct_anomalous_turf_layering():
    pipeline = RenderCompositorPipeline()

    # Create a corrupted floor turf that improperly has plane=GAME_PLANE (0)
    buggy_turf = VisualAtom(
        atom_id="buggy_turf_01",
        name="Glitched Floor",
        atom_type="turf",
        plane=RenderPlane.GAME_PLANE.value,  # Bug: plane 0 instead of -100
        layer=RenderLayer.MOB_LAYER.value,    # Bug: layer 4.0 instead of 2.0
        coord=(15, 20, 1)
    )
    pipeline.add_atom(buggy_turf)

    # Before fix, audit detects anomaly
    audit_res = pipeline.audit_and_correct_turf_layering()
    assert audit_res["status"] == "AUDIT_COMPLETE"
    assert audit_res["anomalies_detected"] == 1
    assert "buggy_turf_01" in audit_res["corrected_turfs"]

    # After fix, turf is restored to canonical floor plane
    assert buggy_turf.plane == RenderPlane.FLOOR_PLANE.value
    assert buggy_turf.layer == RenderLayer.TURF_LAYER.value


def test_compositor_stack_ordering_and_no_occlusion():
    pipeline = RenderCompositorPipeline()
    coord = (40, 50, 1)

    floor = VisualAtom("floor_tile", "Tile", "turf", RenderPlane.FLOOR_PLANE.value, RenderLayer.TURF_LAYER.value, coord)
    table = VisualAtom("table_wood", "Table", "obj", RenderPlane.GAME_PLANE.value, RenderLayer.STRUCTURE_LAYER.value, coord)
    officer = VisualAtom("sec_officer", "Officer", "mob", RenderPlane.GAME_PLANE.value, RenderLayer.MOB_LAYER.value, coord)

    pipeline.add_atom(table)
    pipeline.add_atom(officer)
    pipeline.add_atom(floor)

    stack = pipeline.get_render_stack_at_coord(coord)
    # Expected ordering: Floor (bottom) -> Table (middle) -> Officer (top)
    assert stack[0].atom_id == "floor_tile"
    assert stack[1].atom_id == "table_wood"
    assert stack[2].atom_id == "sec_officer"

    assert pipeline.verify_no_turf_occlusion(coord) is True


def test_occlusion_detection_fails_when_turf_on_top():
    pipeline = RenderCompositorPipeline()
    coord = (60, 60, 1)

    mob = VisualAtom("human", "Assistant", "mob", RenderPlane.GAME_PLANE.value, RenderLayer.MOB_LAYER.value, coord)
    # Turf with elevated plane simulating the bug
    corrupt_floor = VisualAtom("top_floor", "Broken Floor", "turf", 200, 10.0, coord)

    pipeline.add_atom(mob)
    pipeline.add_atom(corrupt_floor)

    # Occlusion check must detect that turf renders over mob
    assert pipeline.verify_no_turf_occlusion(coord) is False


def test_dreammaker_hotfix_patch_export():
    pipeline = RenderCompositorPipeline()
    patch = pipeline.export_dreammaker_hotfix_patch()
    assert "#define FLOOR_PLANE -100" in patch
    assert "/turf/open/floor" in patch
    assert "plane = FLOOR_PLANE" in patch
    assert "layer = TURF_LAYER" in patch
