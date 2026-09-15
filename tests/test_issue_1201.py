"""Test suite for Issue #1201: Parametric Flower Rainwater Collector for Tinacos."""

from __future__ import annotations

import math
import struct
from pathlib import Path
import pytest

from packages.tinaco_cad.params import CollectorParameters, TINACO_PRESETS
from packages.tinaco_cad.geometry import TriangleMesh, CADModelGenerator
from packages.tinaco_cad.hydraulics import HydraulicEngine, CDMX_STORM_INTENSITIES
from packages.tinaco_cad.exporters import CADExporter
from scripts.verify_issue_1201 import run_verification


def test_parameter_defaults_and_validation() -> None:
    """Validate default parameter values and boundary condition enforcement."""
    params = CollectorParameters()
    assert params.num_petals == 8
    assert params.petal_length == 380.0
    assert params.tinaco_collar_diameter == 450.0
    assert params.slope_radians == math.radians(18.0)
    assert params.overall_diameter_mm > params.tinaco_collar_diameter

    with pytest.raises(ValueError, match="Petal count"):
        CollectorParameters(num_petals=2)

    with pytest.raises(ValueError, match="Petal count"):
        CollectorParameters(num_petals=20)

    with pytest.raises(ValueError, match="Petal length"):
        CollectorParameters(petal_length=10.0)

    with pytest.raises(ValueError, match="slope angle"):
        CollectorParameters(petal_slope_deg=75.0)

    with pytest.raises(ValueError, match="Central drain diameter"):
        CollectorParameters(central_drain_diameter=500.0, tinaco_collar_diameter=450.0)


def test_tinaco_presets_coverage() -> None:
    """Verify standard Mexican rooftop tinaco tank model presets."""
    preset_names = [
        "rotoplas_450",
        "rotoplas_600",
        "rotoplas_750",
        "rotoplas_1100",
        "rotoplas_1100_wide",
        "rotoplas_2500",
        "eureka_universal",
        "citijal_standard",
    ]

    for name in preset_names:
        params = CollectorParameters.from_preset(name)
        assert params.tinaco_collar_diameter >= 450.0
        assert params.tinaco_collar_depth >= 40.0
        assert params.projected_catchment_area_m2 > 0.5
        assert params.catchment_expansion_factor > 1.0

    with pytest.raises(KeyError):
        CollectorParameters.from_preset("non_existent_brand")


def test_geometric_mesh_generation_and_properties() -> None:
    """Validate 3D polygonal mesh creation, vertex count, and spatial bounds."""
    params = CollectorParameters.from_preset("rotoplas_1100")
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    assert len(mesh.vertices) > 500
    assert len(mesh.triangles) > 800
    assert len(mesh.normals) == len(mesh.triangles)

    for nx, ny, nz in mesh.normals:
        magnitude = math.sqrt(nx * nx + ny * ny + nz * nz)
        assert pytest.approx(magnitude, rel=1e-3) == 1.0

    min_box, max_box = mesh.bounding_box()
    span_x = max_box[0] - min_box[0]
    span_y = max_box[1] - min_box[1]
    span_z = max_box[2] - min_box[2]

    assert pytest.approx(span_x, rel=1e-2) == span_y
    assert span_x > params.tinaco_collar_diameter
    assert span_z > params.hub_height

    assert mesh.surface_area_m2() > 0.5
    assert mesh.estimate_volume_cm3() > 100.0


def test_mesh_manifold_integrity() -> None:
    """Verify that generated CAD mesh contains valid edge topologies."""
    params = CollectorParameters(num_petals=6)
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    assert mesh.is_manifold() is True


def test_petal_radial_symmetry() -> None:
    """Ensure petals are distributed with geometric angular symmetry."""
    num_petals = 8
    params = CollectorParameters(num_petals=num_petals)
    expected_step_angle = (2.0 * math.pi) / num_petals

    for i in range(num_petals):
        angle = (2.0 * math.pi * i) / num_petals
        assert pytest.approx(angle % (2.0 * math.pi)) == (i * expected_step_angle) % (2.0 * math.pi)


def test_hydraulic_inflow_and_drain_calculations() -> None:
    """Test Rational Method runoff inflow and Torricelli gravity drainage equations."""
    params = CollectorParameters.from_preset("rotoplas_1100")
    engine = HydraulicEngine(params)

    inflow_light = engine.calculate_peak_inflow(CDMX_STORM_INTENSITIES["light_shower"])
    inflow_cloudburst = engine.calculate_peak_inflow(CDMX_STORM_INTENSITIES["torrential_cloudburst_50yr"])

    assert inflow_light > 0.0
    assert inflow_cloudburst > inflow_light
    assert pytest.approx(inflow_cloudburst / inflow_light, rel=1e-2) == 110.0 / 5.0

    drain_capacity = engine.calculate_drain_capacity()
    assert drain_capacity > 5.0

    drain_capacity_half_head = engine.calculate_drain_capacity(hydraulic_head_mm=params.hub_height / 2.0)
    assert drain_capacity_half_head < drain_capacity
    assert pytest.approx(drain_capacity / drain_capacity_half_head, rel=1e-2) == math.sqrt(2.0)


def test_anti_overflow_assessment_safety_margin() -> None:
    """Verify anti-overflow verification under extreme 50-year CDMX storms."""
    params = CollectorParameters.from_preset("rotoplas_1100")
    engine = HydraulicEngine(params)
    assessment = engine.assess_performance()

    assert assessment.anti_overflow_verified is True
    assert assessment.hydraulic_safety_margin > 10.0
    assert assessment.annual_harvest_volume_liters > 500.0
    assert assessment.filling_time_minutes_rotoplas_1100 > 0.0


def test_cad_exporter_stl_ascii(tmp_path: Path) -> None:
    """Verify ASCII STL file export structure and triangle syntax."""
    params = CollectorParameters(num_petals=4, petal_length=150.0)
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    exporter = CADExporter(mesh, params)
    stl_file = tmp_path / "test_model.stl"
    exporter.export_stl_ascii(stl_file)

    assert stl_file.exists()
    content = stl_file.read_text(encoding="utf-8")
    assert content.startswith("solid tinaco_rainwater_collector")
    assert content.strip().endswith("endsolid tinaco_rainwater_collector")
    assert "facet normal" in content
    assert "outer loop" in content


def test_cad_exporter_stl_binary(tmp_path: Path) -> None:
    """Verify binary STL file format compliance, header size, and facet counts."""
    params = CollectorParameters(num_petals=6, petal_length=200.0)
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    exporter = CADExporter(mesh, params)
    stl_file = tmp_path / "test_model_binary.stl"
    exporter.export_stl_binary(stl_file)

    assert stl_file.exists()
    file_bytes = stl_file.read_bytes()
    assert len(file_bytes) >= 84

    num_triangles = struct.unpack("<I", file_bytes[80:84])[0]
    assert num_triangles == len(mesh.triangles)

    expected_file_size = 84 + (num_triangles * 50)
    assert len(file_bytes) == expected_file_size


def test_cad_exporter_obj(tmp_path: Path) -> None:
    """Verify Wavefront OBJ export format, vertex listings, and face definitions."""
    params = CollectorParameters(num_petals=4, petal_length=150.0)
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    exporter = CADExporter(mesh, params)
    obj_file = tmp_path / "test_model.obj"
    exporter.export_obj(obj_file)

    assert obj_file.exists()
    content = obj_file.read_text(encoding="utf-8")
    assert "o TinacoFlowerCollector" in content
    assert "v " in content
    assert "vn " in content
    assert "f " in content


def test_cad_exporter_step(tmp_path: Path) -> None:
    """Verify ISO 10303-21 STEP CAD exchange file header and schema conformance."""
    params = CollectorParameters.from_preset("rotoplas_750")
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    exporter = CADExporter(mesh, params)
    step_file = tmp_path / "test_model.step"
    exporter.export_step(step_file)

    assert step_file.exists()
    content = step_file.read_text(encoding="utf-8")
    assert content.startswith("ISO-10303-21;")
    assert "FILE_DESCRIPTION" in content
    assert "AUTOMOTIVE_DESIGN" in content
    assert "PRODUCT('TINACO_FLOWER_COLLECTOR'" in content
    assert content.strip().endswith("END-ISO-10303-21;")


def test_cad_exporter_svg_flat_pattern(tmp_path: Path) -> None:
    """Verify 2D unfolded manufacturing flat pattern SVG output."""
    params = CollectorParameters(num_petals=8)
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    exporter = CADExporter(mesh, params)
    svg_file = tmp_path / "petal_pattern.svg"
    exporter.export_svg_flat_pattern(svg_file)

    assert svg_file.exists()
    content = svg_file.read_text(encoding="utf-8")
    assert "<svg" in content
    assert "</svg>" in content
    assert "cutline" in content
    assert "foldline" in content
    assert f"TINACO PETAL PATTERN (1 of {params.num_petals})" in content


def test_end_to_end_verification_script() -> None:
    """Verify that the end-to-end verification script succeeds with exit code 0."""
    exit_code = run_verification()
    assert exit_code == 0
