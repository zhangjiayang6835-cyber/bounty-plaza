"""Comprehensive pytest test suite for Mexico City Tinaco Rainwater Harvester (#1294)."""

import math
from pathlib import Path
import struct
import sys
import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.tinaco_collector import (
    AdjustableTinacoAdapter,
    BillOfMaterialsItem,
    CentralDrainOutlet,
    CollectorAssembly,
    Mesh3D,
    ParametricCadEngine,
    PetalGeometry,
    SiteMeasurementRequirement,
    TINACO_SPECIFICATIONS_CATALOG,
    export_bom_markdown,
    export_checklist_markdown,
    generate_ascii_engineering_drawing,
    generate_assembly_drawing_svg,
    generate_bill_of_materials,
    generate_site_measurement_checklist,
    validate_collector_geometry,
    validate_mesh_watertightness,
    validate_openscad_syntax,
    validate_step_syntax,
    validate_stl_syntax,
)


def test_petal_geometry_calculations():
    """Verify dimensional calculations, catchment area, and runoff formulas."""
    petals = PetalGeometry(
        petal_count=8,
        outer_radius_mm=850.0,
        inner_radius_mm=225.0,
        inward_slope_deg=18.5,
        wall_thickness_mm=4.0,
        rim_lip_height_mm=45.0,
    )

    assert petals.outer_diameter_mm == 1700.0
    assert petals.throat_diameter_mm == 450.0
    assert petals.radial_span_mm == 625.0

    expected_drop = 625.0 * math.tan(math.radians(18.5))
    assert abs(petals.vertical_drop_mm - expected_drop) < 1e-4

    expected_area = math.pi * (850.0**2 - 225.0**2) / 1_000_000.0
    assert abs(petals.catchment_area_m2 - expected_area) < 1e-4
    assert 2.0 <= petals.catchment_area_m2 <= 2.3

    runoff_liters = petals.calculate_event_runoff_liters(30.0, runoff_coefficient=0.95)
    assert runoff_liters == pytest.approx(petals.catchment_area_m2 * 30.0 * 0.95, rel=1e-3)

    peak_flow = petals.calculate_peak_flow_rate_lps(60.0)
    assert peak_flow > 0.0
    assert peak_flow == pytest.approx((petals.catchment_area_m2 * 60.0 * 0.95) / 3600.0, rel=1e-3)

    mass = petals.estimated_mass_kg
    assert 5.0 <= mass <= 15.0


def test_central_drain_outlet_hydraulics():
    """Verify hydraulic discharge equations and anti-vortex drain capacity."""
    drain = CentralDrainOutlet(
        throat_diameter_mm=450.0,
        drain_neck_diameter_mm=110.0,
        funnel_depth_mm=180.0,
        discharge_coefficient=0.62,
    )

    assert drain.throat_radius_mm == 225.0
    assert drain.neck_radius_mm == 55.0

    area_neck_m2 = math.pi * (0.055**2)
    velocity_m_s = math.sqrt(2.0 * 9.80665 * 0.18)
    expected_capacity_lps = 0.62 * area_neck_m2 * velocity_m_s * 1000.0

    capacity = drain.calculate_gravity_discharge_capacity_lps()
    assert abs(capacity - expected_capacity_lps) < 1e-3
    assert capacity > 10.0

    assert drain.verify_drainage_capacity(peak_inflow_lps=0.05, safety_factor=3.0)


def test_adjustable_tinaco_adapter():
    """Verify multi-segment clamp bounds, compatibility, and expansion math."""
    adapter = AdjustableTinacoAdapter(
        min_clamp_diameter_mm=400.0,
        max_clamp_diameter_mm=650.0,
        nominal_diameter_mm=500.0,
        segment_count=4,
    )

    assert adapter.is_compatible_diameter(400.0)
    assert adapter.is_compatible_diameter(450.0)
    assert adapter.is_compatible_diameter(500.0)
    assert adapter.is_compatible_diameter(600.0)
    assert adapter.is_compatible_diameter(650.0)

    assert not adapter.is_compatible_diameter(380.0)
    assert not adapter.is_compatible_diameter(670.0)

    gap_nominal = adapter.calculate_expansion_gap_mm(500.0)
    expected_gap = (math.pi * 500.0 - math.pi * 400.0) / 4.0
    assert abs(gap_nominal - expected_gap) < 1e-4


def test_tinaco_catalog_database_coverage():
    """Verify that all standard Mexico City tinaco catalog models are supported."""
    adapter = AdjustableTinacoAdapter()
    assert len(TINACO_SPECIFICATIONS_CATALOG) >= 5

    for name, spec in TINACO_SPECIFICATIONS_CATALOG.items():
        mouth_dia = spec["mouth_outer_diameter_mm"]
        assert adapter.is_compatible_diameter(mouth_dia), f"Adapter fails to support {name}"


def test_collector_assembly_composition():
    """Verify assembly dimensional integration, total mass, and serialization."""
    assembly = CollectorAssembly()

    assert assembly.total_outer_diameter_mm == 1700.0
    assert assembly.total_height_mm > 400.0
    assert 10.0 <= assembly.total_estimated_mass_kg <= 25.0

    data = assembly.to_dict()
    assert data["assembly_id"] == "CDMX-TINACO-RAIN-01"
    assert "petals" in data
    assert "drain" in data
    assert "adapter" in data
    assert data["petals"]["petal_count"] == 8


def test_collector_geometry_validation():
    """Verify geometry validator against healthy and pathological inputs."""
    valid_assembly = CollectorAssembly()
    report = validate_collector_geometry(valid_assembly)
    assert report.is_valid
    assert report.checks_passed == 6
    assert len(report.errors) == 0

    bad_slope = CollectorAssembly(
        petals=PetalGeometry(inward_slope_deg=2.0)
    )
    bad_slope_report = validate_collector_geometry(bad_slope)
    assert not bad_slope_report.is_valid
    assert any("MINIMUM_DRAINAGE_SLOPE" in err for err in bad_slope_report.errors)

    bad_adapter = CollectorAssembly(
        adapter=AdjustableTinacoAdapter(min_clamp_diameter_mm=500.0, max_clamp_diameter_mm=550.0)
    )
    bad_adapter_report = validate_collector_geometry(bad_adapter)
    assert not bad_adapter_report.is_valid
    assert any("ADAPTER_UNIVERSAL_COMPATIBILITY" in err for err in bad_adapter_report.errors)


def test_mesh_3d_calculations():
    """Verify surface area, signed volume, bounding box, and normals recomputation."""
    vertices = [
        (0.0, 0.0, 0.0),
        (10.0, 0.0, 0.0),
        (10.0, 10.0, 0.0),
        (0.0, 10.0, 0.0),
        (0.0, 0.0, 10.0),
        (10.0, 0.0, 10.0),
        (10.0, 10.0, 10.0),
        (0.0, 10.0, 10.0),
    ]
    faces = [
        (0, 2, 1), (0, 3, 2),
        (4, 5, 6), (4, 6, 7),
        (0, 1, 5), (0, 5, 4),
        (2, 3, 7), (2, 7, 6),
        (0, 4, 7), (0, 7, 3),
        (1, 2, 6), (1, 6, 5),
    ]
    mesh = Mesh3D(name="unit_box", vertices=vertices, faces=faces)
    mesh.recompute_normals()

    assert len(mesh.normals) == len(faces)
    assert mesh.surface_area == pytest.approx(600.0, rel=1e-3)
    assert abs(mesh.signed_volume) == pytest.approx(1000.0, rel=1e-3)

    bbox = mesh.bounding_box
    assert bbox == ((0.0, 0.0, 0.0), (10.0, 10.0, 10.0))

    is_valid, _ = validate_mesh_watertightness(mesh)
    assert is_valid


def test_mesh_watertightness_failures():
    """Verify mesh validator catches empty or degenerate meshes."""
    empty_mesh = Mesh3D(name="empty")
    is_valid, reason = validate_mesh_watertightness(empty_mesh)
    assert not is_valid
    assert "0 vertices" in reason

    flat_mesh = Mesh3D(
        name="flat",
        vertices=[(0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)],
        faces=[(0, 1, 2)],
    )
    flat_mesh.recompute_normals()
    is_valid, reason = validate_mesh_watertightness(flat_mesh)
    assert not is_valid
    assert "flat bounding box" in reason


def test_parametric_cad_mesh_generation():
    """Verify mesh generation for individual petals, collector, adapter, and full assembly."""
    assembly = CollectorAssembly()

    blade_mesh = ParametricCadEngine.generate_petal_blade_mesh(assembly.petals, petal_index=0)
    assert len(blade_mesh.vertices) > 50
    assert len(blade_mesh.faces) > 50

    collector_mesh = ParametricCadEngine.generate_flower_collector_mesh(
        assembly.petals,
        assembly.drain,
    )
    assert len(collector_mesh.vertices) > 200
    assert len(collector_mesh.faces) > 200
    assert collector_mesh.surface_area > 1_000_000.0

    adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(
        assembly.adapter,
        assembly.drain,
    )
    assert len(adapter_mesh.vertices) > 100
    assert len(adapter_mesh.faces) > 100

    full_mesh = ParametricCadEngine.generate_complete_assembly_mesh(assembly)
    assert len(full_mesh.vertices) == len(collector_mesh.vertices) + len(adapter_mesh.vertices)
    assert len(full_mesh.faces) == len(collector_mesh.faces) + len(adapter_mesh.faces)


def test_stl_export_ascii_and_binary():
    """Verify ASCII and binary STL formatting and validation."""
    adapter = AdjustableTinacoAdapter()
    drain = CentralDrainOutlet()
    adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(adapter, drain)

    ascii_stl = adapter_mesh.to_stl_ascii("adapter_test")
    assert ascii_stl.startswith("solid adapter_test")
    assert "endsolid adapter_test" in ascii_stl
    assert "facet normal" in ascii_stl

    is_valid_ascii, reason_ascii = validate_stl_syntax(ascii_stl)
    assert is_valid_ascii, reason_ascii

    binary_stl = adapter_mesh.to_stl_binary()
    assert len(binary_stl) >= 84
    triangle_count = struct.unpack("<I", binary_stl[80:84])[0]
    assert triangle_count == len(adapter_mesh.faces)
    assert len(binary_stl) == 84 + (triangle_count * 50)

    is_valid_bin, reason_bin = validate_stl_syntax(binary_stl)
    assert is_valid_bin, reason_bin


def test_step_export_iso_10303_21():
    """Verify compliance of generated STEP file with ISO 10303-21 standard."""
    adapter = AdjustableTinacoAdapter()
    drain = CentralDrainOutlet()
    adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(adapter, drain)

    step_text = adapter_mesh.to_step("tinaco_adapter_iso")
    assert step_text.startswith("ISO-10303-21;")
    assert "HEADER;" in step_text
    assert "FILE_SCHEMA(('CONFIG_CONTROL_DESIGN'));" in step_text
    assert "DATA;" in step_text
    assert "MANIFOLD_SOLID_BREP" in step_text
    assert "CLOSED_SHELL" in step_text
    assert "ADVANCED_FACE" in step_text
    assert "END-ISO-10303-21;" in step_text

    is_valid_step, reason_step = validate_step_syntax(step_text)
    assert is_valid_step, reason_step


def test_openscad_source_generation():
    """Verify OpenSCAD source code generation, modules, and syntax."""
    assembly = CollectorAssembly()
    scad_code = ParametricCadEngine.generate_openscad_source(assembly)

    is_valid, reason = validate_openscad_syntax(scad_code)
    assert is_valid, reason

    assert "module single_petal_sweep" in scad_code
    assert "module flower_petals_array" in scad_code
    assert "module central_drain_funnel" in scad_code
    assert "module adjustable_tinaco_adapter_collar" in scad_code
    assert "tinaco_rainwater_harvester_assembly();" in scad_code


def test_assembly_drawings_generation():
    """Verify SVG technical drawings and ASCII engineering schematic."""
    assembly = CollectorAssembly()

    svg_drawing = generate_assembly_drawing_svg(assembly)
    assert "<svg" in svg_drawing
    assert "</svg>" in svg_drawing
    assert "VIEW 1: PLAN VIEW" in svg_drawing
    assert "VIEW 2: FRONT ELEVATION" in svg_drawing
    assert "VIEW 3: SECTION A-A CUTAWAY" in svg_drawing
    assert "VIEW 4: 3D ISOMETRIC SCHEMATIC" in svg_drawing
    assert "CDMX-TRH-001-REV-A" in svg_drawing

    ascii_drawing = generate_ascii_engineering_drawing(assembly)
    assert "ENGINEERING SCHEMATIC" in ascii_drawing
    assert "MEXICO CITY" in ascii_drawing
    assert "ADJUSTABLE TINACO ADAPTER" in ascii_drawing


def test_bill_of_materials_and_site_checklist():
    """Verify BOM line item counts, currency totals, and site measurement requirements."""
    assembly = CollectorAssembly()

    bom_items = generate_bill_of_materials(assembly)
    assert len(bom_items) == 9

    total_usd = sum(item.total_cost_usd for item in bom_items)
    total_mxn = sum(item.total_cost_mxn for item in bom_items)
    assert total_usd > 100.0
    assert total_mxn > 2000.0

    bom_md = export_bom_markdown(bom_items)
    assert "Bill of Materials (BOM)" in bom_md
    assert "UV-Stabilized Food-Grade HDPE" in bom_md
    assert "Grade 316 Marine Stainless Steel" in bom_md

    checklist = generate_site_measurement_checklist()
    assert len(checklist) == 8
    codes = [item.code for item in checklist]
    assert "DIM-01" in codes
    assert "DIM-02" in codes
    assert "DIM-03" in codes
    assert "DIM-08" in codes

    checklist_md = export_checklist_markdown(checklist)
    assert "Pre-Fabrication Measurement Protocol" in checklist_md
    assert "Tinaco Manhole Neck Outer Diameter" in checklist_md


def test_physical_cad_files_exist():
    """Verify that physical CAD files generated in cad/ are present and non-empty."""
    project_root = Path(__file__).resolve().parent.parent
    cad_dir = project_root / "cad"

    expected_files = [
        "tinaco_flower_collector.scad",
        "tinaco_flower_collector.stl",
        "tinaco_adapter.stl",
        "tinaco_flower_assembly.stl",
        "tinaco_flower_collector.step",
        "tinaco_adapter.step",
        "tinaco_flower_assembly.step",
        "assembly_drawing.svg",
        "assembly_drawing.txt",
        "bill_of_materials.md",
        "site_measurement_checklist.md",
    ]

    for fname in expected_files:
        fpath = cad_dir / fname
        assert fpath.exists(), f"Missing CAD deliverable: {fname}"
        assert fpath.stat().st_size > 0, f"CAD deliverable is empty: {fname}"
