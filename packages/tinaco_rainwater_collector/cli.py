"""Command-line interface and automation pipeline for tinaco rainwater collector."""

from __future__ import annotations

import argparse
import os
import sys


from packages.tinaco_rainwater_collector.cad_engine import CADGeometryEngine
from packages.tinaco_rainwater_collector.drawings import EngineeringDrawingGenerator
from packages.tinaco_rainwater_collector.hydraulics import HydraulicEngine
from packages.tinaco_rainwater_collector.models import (
    FlowerCollectorConfig,
    MeasurementChecklist,
    TinacoAdapter,
)
from packages.tinaco_rainwater_collector.settlement import SettlementEngine


def handle_cad(output_dir: str) -> int:
    """Generate and write 3D CAD STEP and STL models to disk."""
    os.makedirs(output_dir, exist_ok=True)
    engine = CADGeometryEngine()

    step_data = engine.export_step_iso10303_21()
    step_path = os.path.join(output_dir, "tinaco_flower_collector.step")
    with open(step_path, "w", encoding="utf-8") as handle:
        handle.write(step_data)

    stl_data = engine.export_stl_binary()
    stl_path = os.path.join(output_dir, "tinaco_flower_collector.stl")
    with open(stl_path, "wb") as handle:
        handle.write(stl_data)

    print(f"[OK] Generated STEP model: {step_path} ({len(step_data):,} bytes)")
    print(f"[OK] Generated Binary STL model: {stl_path} ({len(stl_data):,} bytes)")
    return 0


def handle_drawings(output_dir: str) -> int:
    """Generate and save vector SVG drawing and ASCII blueprint."""
    os.makedirs(output_dir, exist_ok=True)
    generator = EngineeringDrawingGenerator()

    svg_data = generator.generate_svg_drawing()
    svg_path = os.path.join(output_dir, "tinaco_flower_collector.svg")
    with open(svg_path, "w", encoding="utf-8") as handle:
        handle.write(svg_data)

    ascii_data = generator.generate_ascii_blueprint()
    ascii_path = os.path.join(output_dir, "blueprint.txt")
    with open(ascii_path, "w", encoding="utf-8") as handle:
        handle.write(ascii_data)

    print(f"[OK] Generated SVG drawing: {svg_path} ({len(svg_data):,} bytes)")
    print(f"[OK] Generated ASCII blueprint: {ascii_path}")
    print("\n" + ascii_data)
    return 0


def handle_hydraulics() -> int:
    """Execute hydraulic flow analysis and print performance metrics."""
    config = FlowerCollectorConfig()
    engine = HydraulicEngine(config)
    res = engine.analyze()

    print("=" * 60)
    print("HYDRAULIC ADEQUACY REPORT - MEXICO CITY PEAK STORM")
    print("=" * 60)
    print(f"Catchment Area:           {res.catchment_area_m2} m2")
    print(f"Rainfall Intensity:       {res.rainfall_intensity_mm_per_hr} mm/hr")
    print(f"Runoff Inflow Rate:       {res.peak_inflow_liters_per_sec} L/s")
    print(f"Drain Bore Diameter:      {res.drain_bore_diameter_mm} mm")
    print(f"Discharge Capacity:       {res.drain_capacity_liters_per_sec} L/s")
    print(f"Hydraulic Safety Factor:  {res.safety_factor}x (Min required: 5.0x)")
    print(f"Drainage Transit Time:    {res.drainage_transit_time_sec} s")
    print(f"Adequacy Assessment:      {'PASS' if res.is_adequate else 'FAIL'}")
    print("=" * 60)
    return 0 if res.is_adequate else 1


def handle_bom() -> int:
    """Print bill of materials schedule and site pre-build checklist."""
    engine = CADGeometryEngine()
    bom = engine.generate_bill_of_materials()
    checklist = MeasurementChecklist()
    adapter = TinacoAdapter()

    print("=" * 70)
    print("BILL OF MATERIALS (BOM)")
    print("=" * 70)
    for item in bom.items:
        print(
            f"#{item.item_number:<2} | {item.part_name:<32} | "
            f"Qty: {item.quantity:<2} | Mass: {item.unit_mass_kg:.3f} kg"
        )
    print("-" * 70)
    print(f"Total Assembled Dry Mass:  {bom.total_mass_kg:.3f} kg")
    print(f"Estimated Hardware Cost:   ${bom.estimated_hardware_cost_usd:.2f} USD")
    print("=" * 70)
    print("\nSITE MEASUREMENT & FITMENT VERIFICATION")
    print("-" * 70)
    fit_valid = checklist.validate_site_suitability(adapter)
    print(f"Target Tinaco:             {checklist.tinaco_brand}")
    print(
        f"Measured Rim OD:           {checklist.measured_rim_od_mm} mm "
        f"(Adapter: {adapter.min_rim_diameter_mm}-{adapter.max_rim_diameter_mm} mm)"
    )
    print(f"Overhead Clearance:        {checklist.overhead_clearance_mm} mm (Min required: 600 mm)")
    print(f"Fitment Validation:        {'PASS' if fit_valid else 'FAIL'}")
    print("=" * 70)
    return 0 if fit_valid else 1


def handle_settlement() -> int:
    """Print canonical settlement ledger and cryptographic receipt."""
    settlement = SettlementEngine()
    receipt_json = settlement.export_json()
    print("=" * 60)
    print("CANONICAL SETTLEMENT RECEIPT (BASE CONTRACT ESCROW)")
    print("=" * 60)
    print(receipt_json)
    print("=" * 60)
    return 0


def main() -> int:
    """CLI routing entrypoint."""
    parser = argparse.ArgumentParser(description="Tinaco Rainwater Collector Automation CLI")
    parser.add_argument(
        "command",
        choices=["cad", "drawings", "hydraulics", "bom", "settle", "all"],
        help="Subcommand to execute",
    )
    parser.add_argument("--output", default="dist", help="Output directory for generated files")
    args = parser.parse_args()

    if args.command == "cad":
        return handle_cad(args.output)
    if args.command == "drawings":
        return handle_drawings(args.output)
    if args.command == "hydraulics":
        return handle_hydraulics()
    if args.command == "bom":
        return handle_bom()
    if args.command == "settle":
        return handle_settlement()
    if args.command == "all":
        ret = handle_cad(args.output)
        ret |= handle_drawings(args.output)
        ret |= handle_hydraulics()
        ret |= handle_bom()
        ret |= handle_settlement()
        return ret

    return 0


if __name__ == "__main__":
    sys.exit(main())
