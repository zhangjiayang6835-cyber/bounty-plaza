"""Engineering specifications, bill of materials (BOM), and site measurement protocol."""

from typing import Dict, List

from packages.tinaco_collector.models import (
    BillOfMaterialsItem,
    CollectorAssembly,
    SiteMeasurementRequirement,
)


TINACO_SPECIFICATIONS_CATALOG: Dict[str, Dict[str, float]] = {
    "Rotoplas 450L (Standard Residential)": {
        "capacity_liters": 450.0,
        "tank_diameter_mm": 850.0,
        "tank_height_mm": 990.0,
        "mouth_outer_diameter_mm": 450.0,
        "lip_height_mm": 45.0,
        "neck_thickness_mm": 4.5,
    },
    "Rotoplas 750L (Medium Household)": {
        "capacity_liters": 750.0,
        "tank_diameter_mm": 1020.0,
        "tank_height_mm": 1100.0,
        "mouth_outer_diameter_mm": 450.0,
        "lip_height_mm": 45.0,
        "neck_thickness_mm": 5.0,
    },
    "Rotoplas 1100L (Most Common Mexico City)": {
        "capacity_liters": 1100.0,
        "tank_diameter_mm": 1100.0,
        "tank_height_mm": 1390.0,
        "mouth_outer_diameter_mm": 470.0,
        "lip_height_mm": 50.0,
        "neck_thickness_mm": 5.5,
    },
    "Rotoplas 2500L (Large Residential / Multi-Family)": {
        "capacity_liters": 2500.0,
        "tank_diameter_mm": 1550.0,
        "tank_height_mm": 1600.0,
        "mouth_outer_diameter_mm": 600.0,
        "lip_height_mm": 65.0,
        "neck_thickness_mm": 6.5,
    },
    "Citijal 1200L (Alternative Brand Mexico)": {
        "capacity_liters": 1200.0,
        "tank_diameter_mm": 1140.0,
        "tank_height_mm": 1420.0,
        "mouth_outer_diameter_mm": 500.0,
        "lip_height_mm": 55.0,
        "neck_thickness_mm": 5.0,
    },
    "Aquaplas 750L (Compact Rooftop)": {
        "capacity_liters": 750.0,
        "tank_diameter_mm": 1000.0,
        "tank_height_mm": 1120.0,
        "mouth_outer_diameter_mm": 450.0,
        "lip_height_mm": 42.0,
        "neck_thickness_mm": 4.8,
    },
}


def generate_bill_of_materials(assembly: CollectorAssembly) -> List[BillOfMaterialsItem]:
    """Generate comprehensive line-item bill of materials with realistic CDMX market pricing.

    Args:
        assembly: Collector assembly configuration.

    Returns:
        Structured list of bill of materials items.
    """
    items = [
        BillOfMaterialsItem(
            item_number=1,
            part_name="Flower Petal Catchment Blade",
            category="Polymer Shell",
            material="UV-Stabilized Food-Grade HDPE (FDA 21 CFR 177.1520)",
            quantity=assembly.petals.petal_count,
            unit="pcs",
            unit_cost_mxn=185.0,
            unit_cost_usd=10.0,
            fabrication_process="Rotational Molding / Vacuum Thermoforming (4mm sheet)",
            specifications="18.5° slope, 45mm splash lip, overlap lap joint with predrilled holes",
        ),
        BillOfMaterialsItem(
            item_number=2,
            part_name="Central Vortex-Damping Funnel Core",
            category="Fluid Handling Core",
            material="Virgin Food-Grade HDPE (High Density Polyethylene)",
            quantity=1,
            unit="pcs",
            unit_cost_mxn=320.0,
            unit_cost_usd=17.3,
            fabrication_process="Injection Molding / Precision Rotomolding",
            specifications=f"DIA {assembly.drain.throat_diameter_mm:.0f}mm throat to DIA {assembly.drain.drain_neck_diameter_mm:.0f}mm downspout, 4 integral anti-swirl vanes",
        ),
        BillOfMaterialsItem(
            item_number=3,
            part_name="Adjustable Tinaco Adapter Clamp Segments",
            category="Mounting Subsystem",
            material="Impact-Modified UV-Resistant Polypropylene / HDPE Copolymer",
            quantity=assembly.adapter.segment_count,
            unit="pcs",
            unit_cost_mxn=110.0,
            unit_cost_usd=5.95,
            fabrication_process="High-Pressure Injection Molding with CNC-machined slots",
            specifications=f"4-quadrant curved segments with slotted radial guides, clamp span {assembly.adapter.min_clamp_diameter_mm:.0f}-{assembly.adapter.max_clamp_diameter_mm:.0f}mm",
        ),
        BillOfMaterialsItem(
            item_number=4,
            part_name="Adapter Collar Clamping Bolt Assembly",
            category="Fasteners",
            material="Grade 316 Marine Stainless Steel (A4-70)",
            quantity=assembly.adapter.segment_count,
            unit="sets",
            unit_cost_mxn=45.0,
            unit_cost_usd=2.43,
            fabrication_process="Cold Heading / Thread Rolling (DIN 933 / DIN 985)",
            specifications="M8 x 50mm Hex Bolt + DIN 985 Nylon Locknut + 2x DIN 9021 Wide Washers",
        ),
        BillOfMaterialsItem(
            item_number=5,
            part_name="Petal Lap-Joint Interlock Fastener Kit",
            category="Fasteners",
            material="Grade 316 Marine Stainless Steel (A4-70)",
            quantity=assembly.petals.petal_count * 2,
            unit="sets",
            unit_cost_mxn=18.0,
            unit_cost_usd=0.97,
            fabrication_process="Cold Forging with bonded EPDM sealing washer",
            specifications="M6 x 20mm Truss Head Security Torx + EPDM Sealing Washer + Blind Rivet Nut",
        ),
        BillOfMaterialsItem(
            item_number=6,
            part_name="Sanitary Rim Sealing Gasket",
            category="Seals & Gaskets",
            material="Food-Grade Extruded EPDM Bulb Profile (NSF/ANSI 61 compliant)",
            quantity=1,
            unit="pcs",
            unit_cost_mxn=140.0,
            unit_cost_usd=7.57,
            fabrication_process="Continuous Profile Extrusion with vulcanized corner joint",
            specifications="2.2m continuous loop, 10x15mm hollow bulb with integrated lip seal",
        ),
        BillOfMaterialsItem(
            item_number=7,
            part_name="Coarse Debris / Leaf Filter Screen",
            category="Filtration",
            material="Grade 304 Woven Stainless Steel Wire Cloth",
            quantity=1,
            unit="pcs",
            unit_cost_mxn=95.0,
            unit_cost_usd=5.14,
            fabrication_process="Die-cut circular disc with stamped stainless steel rim ring",
            specifications=f"DIA {assembly.drain.filter_seat_diameter_mm:.0f}mm, 500-micron nominal pore aperture, removable pull tab",
        ),
        BillOfMaterialsItem(
            item_number=8,
            part_name="Secondary Mosquito / Vector Barrier Mesh",
            category="Vector Control",
            material="Grade 304 Stainless Steel Micro-Mesh",
            quantity=1,
            unit="pcs",
            unit_cost_mxn=65.0,
            unit_cost_usd=3.51,
            fabrication_process="Ultrasonic welded fine wire cloth insert",
            specifications="1.2mm aperture preventing Aedes aegypti breeding, downstream of coarse screen",
        ),
        BillOfMaterialsItem(
            item_number=9,
            part_name="Rooftop Wind Tie-Down Guy Webbing Assembly",
            category="Structural Anchorage",
            material="UV-Resistant High-Tenacity Polyester Webbing with 316 SS Ratchet",
            quantity=4,
            unit="sets",
            unit_cost_mxn=85.0,
            unit_cost_usd=4.59,
            fabrication_process="Industrial stitched strap with forged snap hook",
            specifications="25mm width x 2.5m length, 500 kg breaking strength, anchors to tinaco base cradle",
        ),
    ]
    return items


def generate_site_measurement_checklist() -> List[SiteMeasurementRequirement]:
    """Generate mandatory pre-fabrication on-site dimensional verification checklist.

    Returns:
        Structured checklist of dimensions to measure on Mexico City rooftops prior to fabrication.
    """
    return [
        SiteMeasurementRequirement(
            code="DIM-01",
            parameter_name="Tinaco Manhole Neck Outer Diameter (D_mouth)",
            target_nominal_mm=470.0,
            min_tolerance_mm=400.0,
            max_tolerance_mm=650.0,
            measurement_method="Circumferential Pi-tape or 600mm external vernier caliper across 3 orthogonal diameters",
            consequence_of_error="Adapter collar will fail to clamp securely if neck diameter exceeds adapter quadrant range",
        ),
        SiteMeasurementRequirement(
            code="DIM-02",
            parameter_name="Tinaco Mouth Vertical Rim Lip Height (H_lip)",
            target_nominal_mm=50.0,
            min_tolerance_mm=35.0,
            max_tolerance_mm=90.0,
            measurement_method="Depth gauge or steel machinist ruler from top lip crown down to shoulder weld/transition",
            consequence_of_error="Insufficient lip height (<35mm) prevents adapter clamp bolts from establishing positive mechanical bite",
        ),
        SiteMeasurementRequirement(
            code="DIM-03",
            parameter_name="Tinaco Neck Rim Wall Thickness (T_wall)",
            target_nominal_mm=5.5,
            min_tolerance_mm=3.0,
            max_tolerance_mm=8.5,
            measurement_method="External micrometer or dial caliper at 4 equidistant points around the rim circumference",
            consequence_of_error="Excessive clamp torque on thin-walled rims (<3mm) risks hoop stress cracking and vacuum seal loss",
        ),
        SiteMeasurementRequirement(
            code="DIM-04",
            parameter_name="Top Dome Crown Curvature Radius (R_dome)",
            target_nominal_mm=550.0,
            min_tolerance_mm=450.0,
            max_tolerance_mm=750.0,
            measurement_method="Contour profile gauge or 3-point sagitta calculation using 1000mm straight edge",
            consequence_of_error="Steep convex domes could interfere with petal downward slope, requiring customized collar riser spacers",
        ),
        SiteMeasurementRequirement(
            code="DIM-05",
            parameter_name="Clearance to Atmospheric Rooftop Vent (L_vent)",
            target_nominal_mm=350.0,
            min_tolerance_mm=250.0,
            max_tolerance_mm=1200.0,
            measurement_method="Radial tape measurement from neck center to outer edge of tank atmospheric breathing jarro",
            consequence_of_error="Interference with atmospheric jarro prevents proper domestic hydraulic pressure equalization",
        ),
        SiteMeasurementRequirement(
            code="DIM-06",
            parameter_name="Distance to Internal Float Ballcock Valve (L_float)",
            target_nominal_mm=220.0,
            min_tolerance_mm=150.0,
            max_tolerance_mm=450.0,
            measurement_method="Internal vertical and horizontal ruler probe through lid opening to float pivot bracket",
            consequence_of_error="Collector downspout drop tube could collide with float arm, preventing municipal water shutoff",
        ),
        SiteMeasurementRequirement(
            code="DIM-07",
            parameter_name="Rooftop Edge Parapet Safety Clearance (W_roof)",
            target_nominal_mm=1200.0,
            min_tolerance_mm=900.0,
            max_tolerance_mm=5000.0,
            measurement_method="Laser distance meter or 10m fiberglass tape from outer petal radius to parapet wall",
            consequence_of_error="Overhanging petal array increases aerodynamic vortex lift during Mexico City thunderstorm microbursts",
        ),
        SiteMeasurementRequirement(
            code="DIM-08",
            parameter_name="Vertical Overhead Obstacle Clearance (H_clear)",
            target_nominal_mm=800.0,
            min_tolerance_mm=600.0,
            max_tolerance_mm=3000.0,
            measurement_method="Vertical laser measure from tinaco top lid to lowest overhead utility cable, solar heater, or clothesline",
            consequence_of_error="Obstacles prevent full 360-degree blooming petal assembly and impede routine seasonal maintenance",
        ),
    ]


def export_bom_markdown(items: List[BillOfMaterialsItem]) -> str:
    """Format bill of materials into GitHub Flavored Markdown table.

    Args:
        items: List of bill of materials items.

    Returns:
        Rendered markdown table string.
    """
    lines = [
        "### Bill of Materials (BOM) — Mexico City Tinaco Rainwater Collector",
        "",
        "| Item | Part Name | Material | Qty | Fabrication Method | Unit Cost (USD) | Total Cost (USD) | Total Cost (MXN) |",
        "|:----:|:----------|:---------|:---:|:-------------------|:---------------:|:----------------:|:----------------:|",
    ]
    total_usd = 0.0
    total_mxn = 0.0
    for item in items:
        lines.append(
            f"| {item.item_number} | {item.part_name} | {item.material} | {item.quantity} {item.unit} | {item.fabrication_process} | ${item.unit_cost_usd:.2f} | ${item.total_cost_usd:.2f} | ${item.total_cost_mxn:.2f} |"
        )
        total_usd += item.total_cost_usd
        total_mxn += item.total_cost_mxn

    lines.append(
        f"| **TOTAL** | **Full Assembly Kit** | **All Components Included** | -- | **Modular Tooling** | -- | **${total_usd:.2f}** | **${total_mxn:.2f}** |"
    )
    lines.append("")
    lines.append(f"> Note: Pricing calculated at current benchmark exchange rate of 18.50 MXN / 1.00 USD.")
    return "\n".join(lines)


def export_checklist_markdown(requirements: List[SiteMeasurementRequirement]) -> str:
    """Format pre-fabrication checklist into GitHub Flavored Markdown.

    Args:
        requirements: List of site measurement requirements.

    Returns:
        Rendered markdown checklist document.
    """
    lines = [
        "### Mandatory Pre-Fabrication Measurement Protocol (Site Survey)",
        "",
        "Before finalizing fabrication tooling or custom thermoforming for a specific rooftop tinaco in Mexico City, a technician must physically verify and document the following critical dimensions:",
        "",
        "| Code | Measurement Parameter | Target Nominal | Allowable Tolerance | Verified Tool / Method | Engineering Impact If Out of Spec |",
        "|:----:|:----------------------|:--------------:|:-------------------:|:-----------------------|:-----------------------------------|",
    ]
    for req in requirements:
        lines.append(
            f"| `{req.code}` | **{req.parameter_name}** | {req.target_nominal_mm:.1f} mm | [{req.min_tolerance_mm:.1f} mm – {req.max_tolerance_mm:.1f} mm] | {req.measurement_method} | {req.consequence_of_error} |"
        )
    lines.append("")
    return "\n".join(lines)
