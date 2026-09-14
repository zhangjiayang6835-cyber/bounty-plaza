"""Generate CAD model exports, technical drawings, and engineering specifications."""

import os
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from packages.tinaco_collector import (
    CollectorAssembly,
    ParametricCadEngine,
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


def generate_all_artifacts(output_dir: Path) -> int:
    """Generate all required CAD files, drawings, and markdown specifications.

    Args:
        output_dir: Destination path for CAD and technical artifacts.

    Returns:
        Exit code 0 on success, non-zero on validation error.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    assembly = CollectorAssembly()

    report = validate_collector_geometry(assembly)
    if not report.is_valid:
        print(f"Collector geometry validation failed: {report.errors}")
        return 1

    scad_content = ParametricCadEngine.generate_openscad_source(assembly)
    scad_valid, scad_reason = validate_openscad_syntax(scad_content)
    if not scad_valid:
        print(f"OpenSCAD syntax error: {scad_reason}")
        return 1
    (output_dir / "tinaco_flower_collector.scad").write_text(scad_content, encoding="utf-8")

    collector_mesh = ParametricCadEngine.generate_flower_collector_mesh(
        assembly.petals,
        assembly.drain,
    )
    adapter_mesh = ParametricCadEngine.generate_adjustable_adapter_mesh(
        assembly.adapter,
        assembly.drain,
    )
    full_mesh = ParametricCadEngine.generate_complete_assembly_mesh(assembly)

    for mesh in (collector_mesh, adapter_mesh, full_mesh):
        mesh_valid, mesh_reason = validate_mesh_watertightness(mesh)
        if not mesh_valid:
            print(f"Mesh validation error on {mesh.name}: {mesh_reason}")
            return 1

    (output_dir / "tinaco_flower_collector.stl").write_bytes(collector_mesh.to_stl_binary())
    (output_dir / "tinaco_adapter.stl").write_bytes(adapter_mesh.to_stl_binary())
    (output_dir / "tinaco_flower_assembly.stl").write_bytes(full_mesh.to_stl_binary())

    stl_valid, stl_reason = validate_stl_syntax((output_dir / "tinaco_flower_assembly.stl").read_bytes())
    if not stl_valid:
        print(f"STL validation error: {stl_reason}")
        return 1

    step_collector = collector_mesh.to_step("tinaco_flower_collector")
    step_adapter = adapter_mesh.to_step("tinaco_adapter")
    step_full = full_mesh.to_step("tinaco_flower_assembly")

    for name, content in [
        ("tinaco_flower_collector.step", step_collector),
        ("tinaco_adapter.step", step_adapter),
        ("tinaco_flower_assembly.step", step_full),
    ]:
        step_valid, step_reason = validate_step_syntax(content)
        if not step_valid:
            print(f"STEP validation error on {name}: {step_reason}")
            return 1
        (output_dir / name).write_text(content, encoding="utf-8")

    svg_drawing = generate_assembly_drawing_svg(assembly)
    (output_dir / "assembly_drawing.svg").write_text(svg_drawing, encoding="utf-8")

    ascii_drawing = generate_ascii_engineering_drawing(assembly)
    (output_dir / "assembly_drawing.txt").write_text(ascii_drawing, encoding="utf-8")

    bom_items = generate_bill_of_materials(assembly)
    bom_md = export_bom_markdown(bom_items)
    (output_dir / "bill_of_materials.md").write_text(bom_md, encoding="utf-8")

    checklist = generate_site_measurement_checklist()
    checklist_md = export_checklist_markdown(checklist)
    (output_dir / "site_measurement_checklist.md").write_text(checklist_md, encoding="utf-8")

    print(f"All CAD artifacts generated and validated in: {output_dir}")
    return 0


def main() -> int:
    """CLI entrypoint for CAD generation."""
    cad_dir = PROJECT_ROOT / "cad"
    return generate_all_artifacts(cad_dir)


if __name__ == "__main__":
    sys.exit(main())
