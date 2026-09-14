"""Parametric data models and engineering structures for tinaco rainwater collector."""

from dataclasses import dataclass, field
import math
from typing import Any, Dict, List, Optional


@dataclass
class PetalGeometry:
    """Defines parametric attributes for collection petals."""

    petal_count: int = 8
    outer_radius_mm: float = 850.0
    inner_radius_mm: float = 225.0
    inward_slope_deg: float = 18.5
    petal_overlap_deg: float = 5.0
    wall_thickness_mm: float = 4.0
    rim_lip_height_mm: float = 45.0
    material_name: str = "UV-Stabilized Food-Grade HDPE"
    material_density_g_cm3: float = 0.95

    @property
    def outer_diameter_mm(self) -> float:
        """Calculate outer collection diameter in millimeters."""
        return self.outer_radius_mm * 2.0

    @property
    def throat_diameter_mm(self) -> float:
        """Calculate inner throat diameter in millimeters."""
        return self.inner_radius_mm * 2.0

    @property
    def radial_span_mm(self) -> float:
        """Calculate radial length span from throat to outer rim in millimeters."""
        return self.outer_radius_mm - self.inner_radius_mm

    @property
    def vertical_drop_mm(self) -> float:
        """Calculate vertical drop from outer rim to central throat in millimeters."""
        slope_rad = math.radians(self.inward_slope_deg)
        return self.radial_span_mm * math.tan(slope_rad)

    @property
    def catchment_area_m2(self) -> float:
        """Calculate horizontal projected catchment area in square meters."""
        area_mm2 = math.pi * (self.outer_radius_mm**2 - self.inner_radius_mm**2)
        return area_mm2 / 1_000_000.0

    def calculate_event_runoff_liters(
        self,
        rainfall_mm: float,
        runoff_coefficient: float = 0.95,
    ) -> float:
        """Calculate harvested volume in liters for a rainfall event.

        Args:
            rainfall_mm: Precipitation depth in millimeters.
            runoff_coefficient: Impervious surface runoff factor (0.0 to 1.0).

        Returns:
            Total harvested water volume in liters.
        """
        return self.catchment_area_m2 * rainfall_mm * runoff_coefficient

    def calculate_peak_flow_rate_lps(
        self,
        rainfall_intensity_mm_per_hr: float,
        runoff_coefficient: float = 0.95,
    ) -> float:
        """Calculate peak runoff flow rate in liters per second using rational method.

        Args:
            rainfall_intensity_mm_per_hr: Storm intensity in millimeters per hour.
            runoff_coefficient: Catchment runoff efficiency factor.

        Returns:
            Peak drainage discharge demand in liters per second.
        """
        hourly_volume_liters = self.calculate_event_runoff_liters(
            rainfall_intensity_mm_per_hr,
            runoff_coefficient,
        )
        return hourly_volume_liters / 3600.0

    @property
    def estimated_mass_kg(self) -> float:
        """Estimate petal array mass in kilograms based on surface area and thickness."""
        surface_factor = 1.0 / math.cos(math.radians(self.inward_slope_deg))
        sloped_area_m2 = self.catchment_area_m2 * surface_factor
        thickness_m = self.wall_thickness_mm / 1000.0
        volume_m3 = sloped_area_m2 * thickness_m
        density_kg_m3 = self.material_density_g_cm3 * 1000.0
        return volume_m3 * density_kg_m3


@dataclass
class CentralDrainOutlet:
    """Defines central vortex-damping drainage core and filter housing."""

    throat_diameter_mm: float = 450.0
    drain_neck_diameter_mm: float = 110.0
    funnel_depth_mm: float = 180.0
    vortex_fin_count: int = 4
    filter_seat_diameter_mm: float = 115.0
    filter_mesh_microns: int = 500
    discharge_coefficient: float = 0.62

    @property
    def throat_radius_mm(self) -> float:
        """Calculate throat radius in millimeters."""
        return self.throat_diameter_mm / 2.0

    @property
    def neck_radius_mm(self) -> float:
        """Calculate drain drop neck radius in millimeters."""
        return self.drain_neck_diameter_mm / 2.0

    @property
    def throat_cross_section_area_mm2(self) -> float:
        """Calculate throat cross-sectional area in square millimeters."""
        return math.pi * (self.throat_radius_mm**2)

    @property
    def neck_cross_section_area_mm2(self) -> float:
        """Calculate neck downspout cross-sectional area in square millimeters."""
        return math.pi * (self.neck_radius_mm**2)

    def calculate_gravity_discharge_capacity_lps(
        self,
        water_head_mm: Optional[float] = None,
    ) -> float:
        """Calculate maximum gravity drainage discharge capacity in liters per second.

        Uses the standard hydraulic orifice equation Q = Cd * A * sqrt(2 * g * h).

        Args:
            water_head_mm: Hydrostatic driving head in millimeters. Defaults to funnel depth.

        Returns:
            Maximum discharge flow rate in liters per second.
        """
        head = water_head_mm if water_head_mm is not None else self.funnel_depth_mm
        gravity_accel_mm_s2 = 9806.65
        area_m2 = self.neck_cross_section_area_mm2 / 1_000_000.0
        head_m = head / 1000.0
        velocity_m_s = math.sqrt(2.0 * 9.80665 * head_m)
        flow_m3_s = self.discharge_coefficient * area_m2 * velocity_m_s
        return flow_m3_s * 1000.0

    def verify_drainage_capacity(
        self,
        peak_inflow_lps: float,
        safety_factor: float = 2.0,
    ) -> bool:
        """Verify whether drainage outlet capacity exceeds peak storm inflow.

        Args:
            peak_inflow_lps: Peak storm water arrival rate in liters per second.
            safety_factor: Required hydraulic safety margin.

        Returns:
            True if outlet capacity meets or exceeds design requirement.
        """
        capacity = self.calculate_gravity_discharge_capacity_lps()
        return capacity >= (peak_inflow_lps * safety_factor)


@dataclass
class AdjustableTinacoAdapter:
    """Defines multi-segment adjustable mounting collar for Mexico City tinacos."""

    min_clamp_diameter_mm: float = 400.0
    max_clamp_diameter_mm: float = 650.0
    nominal_diameter_mm: float = 500.0
    collar_height_mm: float = 120.0
    collar_thickness_mm: float = 5.0
    segment_count: int = 4
    clamp_hardware: str = "M8x50mm DIN 933 316 Stainless Steel"
    torque_rating_nm: float = 12.0
    gasket_material: str = "Food-Grade EPDM Extruded Bulb Profile"
    gasket_thickness_mm: float = 10.0

    def is_compatible_diameter(self, measured_diameter_mm: float) -> bool:
        """Check if target tinaco mouth diameter falls within adjustment range.

        Args:
            measured_diameter_mm: Physical measurement of tinaco manhole rim.

        Returns:
            True if adapter can clamp securely without modification.
        """
        return (
            self.min_clamp_diameter_mm
            <= measured_diameter_mm
            <= self.max_clamp_diameter_mm
        )

    def calculate_expansion_gap_mm(self, target_diameter_mm: float) -> float:
        """Calculate circumferential expansion gap between clamping segments.

        Args:
            target_diameter_mm: Target tinaco rim diameter in millimeters.

        Returns:
            Arc gap distance in millimeters per segment joint.
        """
        circumference = math.pi * target_diameter_mm
        base_circumference = math.pi * self.min_clamp_diameter_mm
        delta_circumference = max(0.0, circumference - base_circumference)
        return delta_circumference / float(self.segment_count)


@dataclass
class CollectorAssembly:
    """Complete parametric assembly unifying petals, drain core, and adapter."""

    assembly_id: str = "CDMX-TINACO-RAIN-01"
    name: str = "Flower-Shaped Tinaco Rainwater Collector"
    location_profile: str = "Mexico City (CDMX) Rooftop Retrofit"
    petals: PetalGeometry = field(default_factory=PetalGeometry)
    drain: CentralDrainOutlet = field(default_factory=CentralDrainOutlet)
    adapter: AdjustableTinacoAdapter = field(default_factory=AdjustableTinacoAdapter)

    @property
    def total_height_mm(self) -> float:
        """Calculate overall vertical height of assembled unit in millimeters."""
        return (
            self.petals.vertical_drop_mm
            + self.drain.funnel_depth_mm
            + self.adapter.collar_height_mm
        )

    @property
    def total_outer_diameter_mm(self) -> float:
        """Calculate maximum diameter of collector petal sweep in millimeters."""
        return self.petals.outer_diameter_mm

    @property
    def total_estimated_mass_kg(self) -> float:
        """Calculate total estimated hardware and polymer mass in kilograms."""
        petals_mass = self.petals.estimated_mass_kg
        drain_mass = 2.4
        adapter_mass = 3.2
        hardware_mass = 0.8
        return round(petals_mass + drain_mass + adapter_mass + hardware_mass, 2)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete parametric configuration to dictionary."""
        return {
            "assembly_id": self.assembly_id,
            "name": self.name,
            "location_profile": self.location_profile,
            "total_height_mm": self.total_height_mm,
            "total_outer_diameter_mm": self.total_outer_diameter_mm,
            "catchment_area_m2": round(self.petals.catchment_area_m2, 3),
            "estimated_mass_kg": self.total_estimated_mass_kg,
            "petals": {
                "petal_count": self.petals.petal_count,
                "outer_radius_mm": self.petals.outer_radius_mm,
                "inner_radius_mm": self.petals.inner_radius_mm,
                "inward_slope_deg": self.petals.inward_slope_deg,
                "wall_thickness_mm": self.petals.wall_thickness_mm,
            },
            "drain": {
                "throat_diameter_mm": self.drain.throat_diameter_mm,
                "drain_neck_diameter_mm": self.drain.drain_neck_diameter_mm,
                "funnel_depth_mm": self.drain.funnel_depth_mm,
                "filter_mesh_microns": self.drain.filter_mesh_microns,
            },
            "adapter": {
                "min_clamp_diameter_mm": self.adapter.min_clamp_diameter_mm,
                "max_clamp_diameter_mm": self.adapter.max_clamp_diameter_mm,
                "collar_height_mm": self.adapter.collar_height_mm,
                "segment_count": self.adapter.segment_count,
            },
        }


@dataclass
class BillOfMaterialsItem:
    """Individual line item in fabrication bill of materials."""

    item_number: int
    part_name: str
    category: str
    material: str
    quantity: int
    unit: str
    unit_cost_mxn: float
    unit_cost_usd: float
    fabrication_process: str
    specifications: str

    @property
    def total_cost_mxn(self) -> float:
        """Calculate line item total in Mexican Pesos."""
        return round(self.quantity * self.unit_cost_mxn, 2)

    @property
    def total_cost_usd(self) -> float:
        """Calculate line item total in US Dollars."""
        return round(self.quantity * self.unit_cost_usd, 2)


@dataclass
class SiteMeasurementRequirement:
    """Pre-fabrication dimensional verification item for rooftop tinaco."""

    code: str
    parameter_name: str
    target_nominal_mm: float
    min_tolerance_mm: float
    max_tolerance_mm: float
    measurement_method: str
    consequence_of_error: str
