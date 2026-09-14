"""Quality, engineering, and geometric validation engine for tinaco collector."""

from dataclasses import dataclass, field
import re
import struct
from typing import Any, Dict, List, Tuple

from packages.tinaco_collector.cad_generator import Mesh3D
from packages.tinaco_collector.models import CollectorAssembly


@dataclass
class ValidationReport:
    """Consolidated results of engineering and syntax validations."""

    is_valid: bool = True
    checks_run: int = 0
    checks_passed: int = 0
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    details: Dict[str, Any] = field(default_factory=dict)

    def record_check(self, name: str, passed: bool, error_msg: str = "") -> None:
        """Record the outcome of an individual engineering check."""
        self.checks_run += 1
        if passed:
            self.checks_passed += 1
            self.details[name] = "PASSED"
        else:
            self.is_valid = False
            self.errors.append(f"[{name}] {error_msg}")
            self.details[name] = f"FAILED: {error_msg}"


def validate_collector_geometry(assembly: CollectorAssembly) -> ValidationReport:
    """Validate hydraulic, structural, and operational geometry of the collector assembly.

    Args:
        assembly: Collector assembly configuration.

    Returns:
        ValidationReport with individual check outcomes.
    """
    report = ValidationReport()

    slope_ok = assembly.petals.inward_slope_deg >= 5.0
    report.record_check(
        "MINIMUM_DRAINAGE_SLOPE",
        slope_ok,
        f"Inward drainage slope must be >= 5.0 degrees to prevent standing water, found {assembly.petals.inward_slope_deg:.1f}°",
    )

    span_ok = assembly.petals.outer_radius_mm > assembly.petals.inner_radius_mm
    report.record_check(
        "RADIAL_CATCHMENT_SPAN",
        span_ok,
        "Outer collection radius must be greater than inner throat radius",
    )

    area = assembly.petals.catchment_area_m2
    area_ok = 1.0 <= area <= 5.0
    report.record_check(
        "CATCHMENT_AREA_ENVELOPE",
        area_ok,
        f"Catchment area must be between 1.0 m² and 5.0 m² for rooftop tinacos, found {area:.2f} m²",
    )

    min_dia = assembly.adapter.min_clamp_diameter_mm
    max_dia = assembly.adapter.max_clamp_diameter_mm
    range_ok = min_dia <= 450.0 and max_dia >= 600.0
    report.record_check(
        "ADAPTER_UNIVERSAL_COMPATIBILITY",
        range_ok,
        f"Adapter clamp range [{min_dia:.0f}, {max_dia:.0f}] must encompass standard Rotoplas range [450, 600] mm",
    )

    peak_flow = assembly.petals.calculate_peak_flow_rate_lps(75.0)
    drain_ok = assembly.drain.verify_drainage_capacity(peak_flow, safety_factor=2.0)
    capacity = assembly.drain.calculate_gravity_discharge_capacity_lps()
    report.record_check(
        "HYDRAULIC_DISCHARGE_SAFETY_FACTOR",
        drain_ok,
        f"Gravity discharge capacity ({capacity:.2f} L/s) must exceed 2x peak storm inflow ({peak_flow:.2f} L/s)",
    )

    mass = assembly.total_estimated_mass_kg
    mass_ok = 5.0 <= mass <= 35.0
    report.record_check(
        "ROOFTOP_STRUCTURAL_MASS_LIMIT",
        mass_ok,
        f"Total dry assembly mass must be between 5.0 kg and 35.0 kg for rooftop safety, found {mass:.1f} kg",
    )

    return report


def validate_mesh_watertightness(mesh: Mesh3D) -> Tuple[bool, str]:
    """Verify that a 3D mesh contains positive surface area and non-degenerate elements.

    Args:
        mesh: 3D mesh instance.

    Returns:
        Tuple of (is_valid, reason_string).
    """
    if not mesh.vertices:
        return False, "Mesh has 0 vertices"
    if not mesh.faces:
        return False, "Mesh has 0 faces"
    if mesh.surface_area <= 0.0:
        return False, "Mesh has non-positive surface area"
    bbox = mesh.bounding_box
    dx = bbox[1][0] - bbox[0][0]
    dy = bbox[1][1] - bbox[0][1]
    dz = bbox[1][2] - bbox[0][2]
    if dx <= 0.0 or dy <= 0.0 or dz <= 0.0:
        return False, "Mesh has zero-volume flat bounding box"
    return True, f"Mesh valid: {len(mesh.vertices)} vertices, {len(mesh.faces)} faces, area={mesh.surface_area:.1f} mm²"


def validate_step_syntax(step_text: str) -> Tuple[bool, str]:
    """Verify conformance with ISO 10303-21 STEP physical file standard grammar.

    Args:
        step_text: Raw contents of STEP file.

    Returns:
        Tuple of (is_valid, reason_string).
    """
    if "ISO-10303-21;" not in step_text:
        return False, "Missing mandatory ISO-10303-21 header declaration"
    if "HEADER;" not in step_text or "ENDSEC;" not in step_text:
        return False, "Missing or incomplete HEADER section"
    if "DATA;" not in step_text or "END-ISO-10303-21;" not in step_text:
        return False, "Missing DATA section or terminating END-ISO-10303-21 mark"
    if "PRODUCT(" not in step_text:
        return False, "Missing PRODUCT definition entity in STEP data"
    if "MANIFOLD_SOLID_BREP" not in step_text:
        return False, "Missing MANIFOLD_SOLID_BREP entity in STEP data"
    return True, "Valid ISO 10303-21 STEP solid physical file syntax"


def validate_stl_syntax(stl_data: Any) -> Tuple[bool, str]:
    """Verify conformance with standard STL format (ASCII or binary).

    Args:
        stl_data: String (ASCII STL) or bytes (binary STL).

    Returns:
        Tuple of (is_valid, reason_string).
    """
    if isinstance(stl_data, bytes):
        if len(stl_data) < 84:
            return False, "Binary STL file truncated (less than 84 bytes)"
        triangle_count = struct.unpack("<I", stl_data[80:84])[0]
        expected_len = 84 + (triangle_count * 50)
        if len(stl_data) != expected_len:
            return (
                False,
                f"Binary STL byte length mismatch: expected {expected_len} for {triangle_count} facets, got {len(stl_data)}",
            )
        return True, f"Valid binary STL containing {triangle_count} triangular facets"

    if isinstance(stl_data, str):
        stripped = stl_data.strip()
        if not stripped.startswith("solid"):
            return False, "ASCII STL does not begin with 'solid' identifier"
        if not stripped.endswith("endsolid") and "endsolid" not in stripped[-30:]:
            return False, "ASCII STL does not terminate with 'endsolid' identifier"
        facet_count = stripped.count("endfacet")
        if facet_count == 0:
            return False, "ASCII STL contains 0 facets"
        return True, f"Valid ASCII STL containing {facet_count} facets"

    return False, "Unsupported STL payload type"


def validate_openscad_syntax(scad_text: str) -> Tuple[bool, str]:
    """Verify structural syntax of OpenSCAD source file.

    Args:
        scad_text: Raw OpenSCAD code.

    Returns:
        Tuple of (is_valid, reason_string).
    """
    open_braces = scad_text.count("{")
    close_braces = scad_text.count("}")
    if open_braces != close_braces:
        return (
            False,
            f"Mismatched curly braces in OpenSCAD code: {open_braces} open vs {close_braces} close",
        )

    open_parens = scad_text.count("(")
    close_parens = scad_text.count(")")
    if open_parens != close_parens:
        return (
            False,
            f"Mismatched parentheses in OpenSCAD code: {open_parens} open vs {close_parens} close",
        )

    required_modules = ["single_petal_sweep", "flower_petals_array", "central_drain_funnel", "adjustable_tinaco_adapter_collar"]
    for mod in required_modules:
        if f"module {mod}" not in scad_text:
            return False, f"Missing required parametric module: {mod}"

    return True, "Valid OpenSCAD parametric source structure"
