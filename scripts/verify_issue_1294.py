"""Standalone verification runner for Mexico City Tinaco Rainwater Harvester (#1294).

Executes comprehensive engineering checks across parametric data models,
hydraulic discharge capacities, 3D mesh watertightness, ISO STEP grammar,
binary STL format compliance, and pre-fabrication site checklists.
"""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.tinaco_collector import (
    AdjustableTinacoAdapter,
    CentralDrainOutlet,
    CollectorAssembly,
    ParametricCadEngine,
    PetalGeometry,
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


def verify_parametric_models() -> bool:
    """Validate parametric dimensions, area equations, and runoff calculations."""
    petals = PetalGeometry(
        petal_count=8,
        outer_radius_mm=850.0,
        inner_radius_mm=225.0,
        inward_slope_deg=18.5,
    )
    drain = CentralDrainOutlet()
    adapter = AdjustableTinacoAdapter()

    checks = [
        petals.outer_diameter_mm == 1700.0,
        petals.throat_diameter_mm == 450.0,
        2.0 <= petals.catchment_area_m2 <= 2.3,
        95.0 <= petals.calculate_event_runoff_liters(50.0) <= 115.0,
        drain.calculate_gravity_discharge_capacity_lps() >= 5.0,
        adapter.is_compatible_diameter(450.0),
        adapter.is_compatible_diameter(600.0),
        not adapter.is_compatible_diameter(700.0),
    ]
    return all(checks)


def verify_tinaco_catalog_compatibility() -> bool:
    """Verify that all standard Mexico City tinacos fit within adapter collar bounds."""
    adapter = AdjustableTinacoAdapter()
    return all(
        adapter.is_compatible_diameter(spec["mouth_outer_diameter_mm"])
        for spec in TINACO_SPECIFICATIONS_CATALOG.values()
    )


def verify_geometry_and_hydraulics() -> bool:
    """Verify system-wide hydraulic safety factor and engineering limits."""
    assembly = CollectorAssembly()
    report = validate_collector_geometry(assembly)
    return report.is_valid and report.checks_passed == report.checks_run


def verify_openscad_export() -> bool:
    """Verify OpenSCAD source syntax and module declarations."""
    assembly = CollectorAssembly()
    scad_code = ParametricCadEngine.generate_openscad_source(assembly)
    is_valid, _ = validate_openscad_syntax(scad_code)
    return is_valid and "tinaco_rainwater_harvester_assembly();" in scad_code


def verify_mesh_and_exports() -> bool:
    """Verify watertight mesh generation, binary STL packing, and ISO STEP compliance."""
    assembly = CollectorAssembly()
    collector_mesh = ParametricCadEngine.generate_flower_collector_mesh(
        assembly.petals,
        assembly.drain,
    )
    adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(
        assembly.adapter,
        assembly.drain,
    )

    c_valid, _ = validate_mesh_watertightness(collector_mesh)
    a_valid, _ = validate_mesh_watertightness(adapter_mesh)
    stl_valid, _ = validate_stl_syntax(adapter_mesh.to_stl_binary())
    step_valid, _ = validate_step_syntax(adapter_mesh.to_step("test_adapter"))

    return c_valid and a_valid and stl_valid and step_valid


def verify_drawings_and_specifications() -> bool:
    """Verify SVG technical drawings, ASCII schematics, BOM, and site checklist."""
    assembly = CollectorAssembly()

    svg_content = generate_assembly_drawing_svg(assembly)
    ascii_drawing = generate_ascii_engineering_drawing(assembly)
    bom_items = generate_bill_of_materials(assembly)
    bom_md = export_bom_markdown(bom_items)
    checklist = generate_site_measurement_checklist()
    checklist_md = export_checklist_markdown(checklist)

    checks = [
        "<svg" in svg_content and "</svg>" in svg_content,
        "VIEW 1: PLAN VIEW" in svg_content,
        "VIEW 2: FRONT ELEVATION" in svg_content,
        "VIEW 3: SECTION A-A CUTAWAY" in svg_content,
        "ENGINEERING SCHEMATIC" in ascii_drawing,
        len(bom_items) >= 7,
        "Bill of Materials" in bom_md,
        len(checklist) >= 6,
        "Pre-Fabrication Measurement Protocol" in checklist_md,
    ]
    return all(checks)


def run_all_verifications() -> int:
    """Execute complete suite of standalone verification checks.

    Returns:
        0 if all verifications succeed, 1 otherwise.
    """
    verifications = [
        ("Parametric Data Models & Calculations", verify_parametric_models),
        ("Mexico City Tinaco Catalog Compatibility", verify_tinaco_catalog_compatibility),
        ("Geometry & Hydraulic Safety Factor", verify_geometry_and_hydraulics),
        ("OpenSCAD Source Syntax", verify_openscad_export),
        ("3D Mesh, STL, & STEP Exporters", verify_mesh_and_exports),
        ("Drawings, BOM, & Measurement Checklist", verify_drawings_and_specifications),
    ]

    all_passed = True
    print("=" * 65)
    print("VERIFICATION SUITE: FLOWER-SHAPED TINACO RAINWATER HARVESTER (#1294)")
    print("=" * 65)

    for test_name, test_fn in verifications:
        passed = test_fn()
        status = "PASSED" if passed else "FAILED"
        print(f"[{status}] {test_name}")
        if not passed:
            all_passed = False

    print("-" * 65)
    verdict = "ALL CHECKS SATISFIED" if all_passed else "VERIFICATION FAILED"
    print(f"Result: {verdict}")
    print("=" * 65)
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(run_all_verifications())
