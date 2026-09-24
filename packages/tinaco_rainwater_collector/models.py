"""Data structures and parametric configuration models for the tinaco rainwater collector."""

from __future__ import annotations

import math
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Point3D:
    """Three-dimensional spatial coordinate vector."""

    x: float
    y: float
    z: float

    def distance_to(self, other: Point3D) -> float:
        """Calculate Euclidean distance between two points in 3D space."""
        return math.sqrt(
            (self.x - other.x) ** 2
            + (self.y - other.y) ** 2
            + (self.z - other.z) ** 2
        )

    def dot(self, other: Point3D) -> float:
        """Compute scalar dot product with another vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Point3D) -> Point3D:
        """Compute vector cross product with another vector."""
        return Point3D(
            x=self.y * other.z - self.z * other.y,
            y=self.z * other.x - self.x * other.z,
            z=self.x * other.y - self.y * other.x,
        )

    def norm(self) -> float:
        """Compute Euclidean vector magnitude."""
        return math.sqrt(self.x**2 + self.y**2 + self.z**2)

    def normalized(self) -> Point3D:
        """Return unit direction vector."""
        magnitude = self.norm()
        if magnitude == 0:
            return Point3D(0.0, 0.0, 1.0)
        return Point3D(
            self.x / magnitude,
            self.y / magnitude,
            self.z / magnitude,
        )

    def to_step_cartesian(self, entity_id: int) -> str:
        """Format point as ISO 10303-21 CARTESIAN_POINT entity."""
        return f"#{entity_id}=CARTESIAN_POINT('',({self.x:.4f},{self.y:.4f},{self.z:.4f}));"


@dataclass(frozen=True)
class Facet3D:
    """Triangular boundary element facet for stereolithography meshes."""

    normal: Point3D
    v1: Point3D
    v2: Point3D
    v3: Point3D

    def to_ascii_stl(self) -> str:
        """Generate ASCII STL representation of this triangle facet."""
        lines = [
            f"  facet normal {self.normal.x:.6e} {self.normal.y:.6e} {self.normal.z:.6e}",
            "    outer loop",
            f"      vertex {self.v1.x:.6e} {self.v1.y:.6e} {self.v1.z:.6e}",
            f"      vertex {self.v2.x:.6e} {self.v2.y:.6e} {self.v2.z:.6e}",
            f"      vertex {self.v3.x:.6e} {self.v3.y:.6e} {self.v3.z:.6e}",
            "    endloop",
            "  endfacet",
        ]
        return "\n".join(lines)


@dataclass
class PetalGeometry:
    """Geometric and kinematic profile of an individual collector petal."""

    index: int
    start_angle_deg: float
    end_angle_deg: float
    outer_radius_mm: float
    inner_radius_mm: float
    outer_height_mm: float
    inner_height_mm: float
    slope_deg: float
    apex_point: Point3D
    throat_point: Point3D

    @property
    def sweep_angle_deg(self) -> float:
        """Return angular coverage of petal in degrees."""
        return self.end_angle_deg - self.start_angle_deg

    @property
    def radial_length_mm(self) -> float:
        """Return horizontal radial extension from throat to apex."""
        return self.outer_radius_mm - self.inner_radius_mm

    @property
    def elevation_drop_mm(self) -> float:
        """Return gravitational vertical drop from rim to central drain."""
        return self.outer_height_mm - self.inner_height_mm

    def verify_drainage_gradient(self) -> bool:
        """Verify monotonic inward descent ensuring positive gravity flow."""
        return self.elevation_drop_mm > 0 and self.slope_deg >= 5.0


@dataclass
class DrainOutlet:
    """Central discharge funnel and downspout connection assembly."""

    funnel_top_diameter_mm: float = 220.0
    drain_bore_diameter_mm: float = 110.0
    funnel_depth_mm: float = 120.0
    downspout_length_mm: float = 180.0
    mesh_aperture_mm: float = 1.2
    mesh_wire_diameter_mm: float = 0.3
    filter_collar_depth_mm: float = 60.0

    @property
    def drain_area_mm2(self) -> float:
        """Calculate circular cross-sectional discharge area of central bore."""
        radius = self.drain_bore_diameter_mm / 2.0
        return math.pi * (radius**2)

    @property
    def funnel_top_area_mm2(self) -> float:
        """Calculate catchment entrance area at top of central funnel."""
        radius = self.funnel_top_diameter_mm / 2.0
        return math.pi * (radius**2)

    @property
    def filter_mesh_open_area_ratio(self) -> float:
        """Calculate fractional open porosity area of wire debris screen."""
        pitch = self.mesh_aperture_mm + self.mesh_wire_diameter_mm
        return (self.mesh_aperture_mm / pitch) ** 2


@dataclass
class TinacoAdapter:
    """Adjustable mounting flange and clamp mechanism for tinaco tank rim."""

    min_rim_diameter_mm: float = 400.0
    max_rim_diameter_mm: float = 650.0
    nominal_rim_diameter_mm: float = 450.0
    flange_height_mm: float = 80.0
    clamp_count: int = 6
    bolt_diameter_mm: float = 8.0
    gasket_thickness_mm: float = 4.0
    gasket_material: str = "EPDM UV-Stabilized Closed-Cell Rubber"

    def is_compatible(self, rim_diameter_mm: float) -> bool:
        """Check if target tinaco rim diameter falls within adjustable clamp range."""
        return self.min_rim_diameter_mm <= rim_diameter_mm <= self.max_rim_diameter_mm


@dataclass
class FlowerCollectorConfig:
    """Full parametric engineering specification for the flower collector."""

    petal_count: int = 8
    outer_diameter_mm: float = 1400.0
    inner_funnel_diameter_mm: float = 220.0
    drain_bore_diameter_mm: float = 110.0
    funnel_depth_mm: float = 120.0
    slope_angle_deg: float = 12.0
    wall_thickness_mm: float = 4.0
    tinaco_rim_nominal_mm: float = 450.0
    tinaco_rim_min_mm: float = 400.0
    tinaco_rim_max_mm: float = 650.0
    material_name: str = "Food-Grade UV-Stabilized HDPE"
    material_density_g_cm3: float = 0.95

    def validate(self) -> list[str]:
        """Validate all parametric dimensions against manufacturing and physical constraints."""
        errors = []
        if self.petal_count < 4:
            errors.append("Petal count must be at least 4.")
        if self.outer_diameter_mm <= self.inner_funnel_diameter_mm:
            errors.append("Outer collector diameter must exceed funnel diameter.")
        if self.inner_funnel_diameter_mm <= self.drain_bore_diameter_mm:
            errors.append("Inner funnel diameter must exceed drain bore diameter.")
        if self.slope_angle_deg < 5.0:
            errors.append("Inward slope angle must be at least 5.0 degrees for drainage.")
        if self.wall_thickness_mm < 2.0:
            errors.append("Wall thickness must be at least 2.0 mm for structural rigidity.")
        if self.tinaco_rim_min_mm > self.tinaco_rim_nominal_mm:
            errors.append("Nominal rim diameter cannot be smaller than minimum adapter range.")
        if self.tinaco_rim_max_mm < self.tinaco_rim_nominal_mm:
            errors.append("Nominal rim diameter cannot exceed maximum adapter range.")
        return errors

    @property
    def catchment_area_m2(self) -> float:
        """Calculate horizontal projected rainwater capture footprint area."""
        radius_m = (self.outer_diameter_mm / 2.0) / 1000.0
        return math.pi * (radius_m**2)

    @property
    def total_height_mm(self) -> float:
        """Calculate overall vertical assembly height from drain bottom to petal tip."""
        radial_run = (self.outer_diameter_mm - self.inner_funnel_diameter_mm) / 2.0
        rise = radial_run * math.tan(math.radians(self.slope_angle_deg))
        return rise + self.funnel_depth_mm + 180.0


@dataclass
class BOMItem:
    """Discrete bill of materials item entry."""

    item_number: int
    part_name: str
    quantity: int
    material: str
    fabrication_method: str
    unit_mass_kg: float
    tolerance: str


@dataclass
class BillOfMaterials:
    """Master bill of materials schedule with mass and cost totals."""

    items: list[BOMItem] = field(default_factory=list)

    @property
    def total_mass_kg(self) -> float:
        """Compute aggregate dry mass of assembled collector."""
        return sum(item.quantity * item.unit_mass_kg for item in self.items)

    @property
    def estimated_hardware_cost_usd(self) -> float:
        """Compute baseline raw materials and hardware cost."""
        return 48.50


@dataclass
class MeasurementChecklist:
    """Verification checklist for target tinaco roof tank before fabrication."""

    tinaco_brand: str = "Rotoplas Standard 1100L"
    measured_rim_od_mm: float = 455.0
    measured_rim_id_mm: float = 445.0
    measured_lip_height_mm: float = 38.0
    overhead_clearance_mm: float = 850.0
    vent_pipe_distance_mm: float = 280.0
    adapter_engaged: bool = True

    def validate_site_suitability(self, adapter: TinacoAdapter) -> bool:
        """Confirm site inspection measurements allow secure installation."""
        if not adapter.is_compatible(self.measured_rim_od_mm):
            return False
        if self.overhead_clearance_mm < 600.0:
            return False
        if self.measured_lip_height_mm < 20.0:
            return False
        return self.adapter_engaged
