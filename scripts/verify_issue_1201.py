"""End-to-end verification script for Issue #1201: Tinaco Flower Rainwater Collector."""

from __future__ import annotations

import sys
from pathlib import Path
from packages.tinaco_cad.params import CollectorParameters
from packages.tinaco_cad.geometry import CADModelGenerator, TriangleMesh
from packages.tinaco_cad.hydraulics import HydraulicEngine, HydraulicAssessment
from packages.tinaco_cad.exporters import CADExporter


def _export_and_check_artifacts(
    exporter: CADExporter,
    output_dir: Path,
) -> bool:
    """Export all CAD formats and ensure non-empty output files."""
    ascii_path = output_dir / "tinaco_collector.stl"
    bin_path = output_dir / "tinaco_collector_binary.stl"
    obj_path = output_dir / "tinaco_collector.obj"
    step_path = output_dir / "tinaco_collector.step"
    svg_path = output_dir / "tinaco_collector_petal_pattern.svg"

    exporter.export_stl_ascii(ascii_path)
    exporter.export_stl_binary(bin_path)
    exporter.export_obj(obj_path)
    exporter.export_step(step_path)
    exporter.export_svg_flat_pattern(svg_path)

    for artifact in [ascii_path, bin_path, obj_path, step_path, svg_path]:
        if not artifact.exists() or artifact.stat().st_size == 0:
            return False
    return True


def _print_report(
    params: CollectorParameters,
    mesh: TriangleMesh,
    assessment: HydraulicAssessment,
) -> None:
    """Print structured engineering verification summary report."""
    min_box, max_box = mesh.bounding_box()
    span_x = max_box[0] - min_box[0]
    span_y = max_box[1] - min_box[1]
    span_z = max_box[2] - min_box[2]

    header = "=" * 66
    sub_header = "-" * 66
    lines = [
        header,
        "TINACO FLOWER RAINWATER COLLECTOR - ENGINEERING VERIFICATION REPORT",
        header,
        f"Target Tinaco Model:      Rotoplas 1100L (Collar: {params.tinaco_collar_diameter}mm)",
        f"Collector Outer Diameter: {params.overall_diameter_mm:.1f} mm",
        f"Number of Petals:         {params.num_petals} petals",
        f"Petal Inward Slope:       {params.petal_slope_deg} degrees",
        f"Vertices Generated:       {len(mesh.vertices)} points",
        f"Triangles Generated:      {len(mesh.triangles)} facets",
        f"Surface Area:             {mesh.surface_area_m2():.3f} m^2",
        f"Bounding Box Span (XYZ):  {span_x:.1f} x {span_y:.1f} x {span_z:.1f} mm",
        sub_header,
        "HYDRAULIC SIZING & MEXICO CITY PRECIPITATION PERFORMANCE:",
        f"Catchment Area:           {assessment.catchment_area_m2} m^2",
        f"Expansion Ratio:          {params.catchment_expansion_factor:.2f}x bare tinaco aperture",
        f"Peak Torrential Inflow:   {assessment.peak_inflow_liters_per_sec} L/s (110mm/h storm)",
        f"Drain Gravity Capacity:   {assessment.drain_capacity_liters_per_sec} L/s",
        f"Safety Margin:            {assessment.hydraulic_safety_margin}x (Verified: "
        f"{assessment.anti_overflow_verified})",
        f"Annual Harvest (CDMX):    {assessment.annual_harvest_volume_liters:.1f} Liters/year",
        f"Tank Fill Time (30mm/h):  {assessment.filling_time_minutes_rotoplas_1100:.1f} minutes",
        sub_header,
        "GENERATED CAD ARTIFACTS: STEP, STL (binary/ASCII), OBJ, SVG",
        header,
        "VERIFICATION STATUS: SUCCESSFUL (ALL CRITERIA SATISFIED)",
        header,
    ]
    print("\n".join(lines))


def run_verification() -> int:
    """Execute complete validation suite across geometry, hydraulics, and CAD exports.

    Returns:
        Exit status code 0 on complete success, 1 on failure.
    """
    output_dir = Path("output")
    output_dir.mkdir(parents=True, exist_ok=True)

    params = CollectorParameters.from_preset("rotoplas_1100")
    generator = CADModelGenerator(params)
    mesh = generator.build_complete_mesh()

    if len(mesh.vertices) < 100 or len(mesh.triangles) < 100 or not mesh.is_manifold():
        return 1

    engine = HydraulicEngine(params)
    assessment = engine.assess_performance()

    if not assessment.anti_overflow_verified:
        return 1

    exporter = CADExporter(mesh, params)
    if not _export_and_check_artifacts(exporter, output_dir):
        return 1

    _print_report(params, mesh, assessment)
    return 0


if __name__ == "__main__":
    sys.exit(run_verification())
