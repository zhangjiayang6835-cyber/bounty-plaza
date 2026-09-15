"""Parametric configuration and validation for tinaco rainwater collectors."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Dict, Any


TINACO_PRESETS: Dict[str, Dict[str, float]] = {
    "rotoplas_450": {"collar_diameter": 450.0, "collar_depth": 40.0, "tank_capacity_l": 450.0},
    "rotoplas_600": {"collar_diameter": 450.0, "collar_depth": 40.0, "tank_capacity_l": 600.0},
    "rotoplas_750": {"collar_diameter": 450.0, "collar_depth": 42.0, "tank_capacity_l": 750.0},
    "rotoplas_1100": {"collar_diameter": 450.0, "collar_depth": 45.0, "tank_capacity_l": 1100.0},
    "rotoplas_1100_wide": {
        "collar_diameter": 600.0,
        "collar_depth": 50.0,
        "tank_capacity_l": 1100.0,
    },
    "rotoplas_2500": {"collar_diameter": 600.0, "collar_depth": 55.0, "tank_capacity_l": 2500.0},
    "eureka_universal": {"collar_diameter": 455.0, "collar_depth": 40.0, "tank_capacity_l": 750.0},
    "citijal_standard": {"collar_diameter": 460.0, "collar_depth": 42.0, "tank_capacity_l": 1100.0},
}


@dataclass
class CollectorParameters:
    """Parametric geometry specifications for flower-shaped rainwater collector.

    Attributes:
        tinaco_collar_diameter: Outer mounting diameter matching tinaco rim (mm).
        tinaco_collar_depth: Vertical depth of slip-fit mounting collar (mm).
        num_petals: Total count of radial water collection petals.
        petal_length: Radial extension length of each petal from hub rim (mm).
        petal_max_width: Maximum transverse width across individual petal (mm).
        petal_slope_deg: Inward gravity incline angle directing runoff to hub (deg).
        petal_channel_depth: Trough depression depth along petal centerline (mm).
        petal_wall_height: Vertical sidewall containment flange height (mm).
        wall_thickness: Structural shell nominal wall thickness (mm).
        central_drain_diameter: Diameter of vortex drainage orifice at hub base (mm).
        hub_height: Total vertical depth of central hub reception basin (mm).
        mesh_aperture_mm: Screen mesh aperture size for leaf and debris exclusion (mm).
        overflow_weir_height: Crest elevation of emergency overflow relief notches (mm).
        material_density_g_cm3: Material density for mass estimation (g/cm^3).
        cdmx_annual_rainfall_mm: Baseline mean annual precipitation in Mexico City (mm).
    """

    tinaco_collar_diameter: float = 450.0
    tinaco_collar_depth: float = 40.0
    num_petals: int = 8
    petal_length: float = 380.0
    petal_max_width: float = 260.0
    petal_slope_deg: float = 18.0
    petal_channel_depth: float = 25.0
    petal_wall_height: float = 35.0
    wall_thickness: float = 4.0
    central_drain_diameter: float = 120.0
    hub_height: float = 70.0
    mesh_aperture_mm: float = 3.0
    overflow_weir_height: float = 50.0
    material_density_g_cm3: float = 0.95
    cdmx_annual_rainfall_mm: float = 840.0
    custom_metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate parameter boundaries upon initialization."""
        self.validate()

    def validate(self) -> None:
        """Enforce physical manufacturing and geometric constraints.

        Raises:
            ValueError: If any dimensional parameter violates physical feasibility.
        """
        if self.num_petals < 4 or self.num_petals > 16:
            raise ValueError("Petal count must be between 4 and 16")
        if self.petal_length <= 50.0 or self.petal_length > 1500.0:
            raise ValueError("Petal length must be between 50mm and 1500mm")
        if self.petal_max_width <= 20.0 or self.petal_max_width > 800.0:
            raise ValueError("Petal maximum width must be between 20mm and 800mm")
        if self.petal_slope_deg <= 2.0 or self.petal_slope_deg >= 60.0:
            raise ValueError("Petal slope angle must be between 2 and 60 degrees")
        if self.tinaco_collar_diameter <= 150.0 or self.tinaco_collar_diameter > 1500.0:
            raise ValueError("Collar diameter must be between 150mm and 1500mm")
        if (
            self.central_drain_diameter <= 30.0
            or self.central_drain_diameter >= self.tinaco_collar_diameter
        ):
            raise ValueError("Central drain diameter must be smaller than collar diameter")
        if self.wall_thickness <= 0.5 or self.wall_thickness > 25.0:
            raise ValueError("Wall thickness must be between 0.5mm and 25mm")
        if self.petal_channel_depth < 5.0 or self.petal_channel_depth > 150.0:
            raise ValueError("Petal channel depth must be between 5mm and 150mm")
        if self.overflow_weir_height >= self.hub_height:
            raise ValueError("Overflow weir crest must be lower than total hub height")

    @property
    def slope_radians(self) -> float:
        """Convert petal slope angle to radians."""
        return math.radians(self.petal_slope_deg)

    @property
    def hub_radius(self) -> float:
        """Outer radius of the central mounting hub in millimeters."""
        return self.tinaco_collar_diameter / 2.0

    @property
    def drain_radius(self) -> float:
        """Radius of the central discharge orifice in millimeters."""
        return self.central_drain_diameter / 2.0

    @property
    def overall_outer_radius(self) -> float:
        """Total projected outer horizontal radius from collector center in millimeters."""
        horizontal_projection = self.petal_length * math.cos(self.slope_radians)
        return self.hub_radius + horizontal_projection

    @property
    def overall_diameter_mm(self) -> float:
        """Total outer diameter of collector in millimeters."""
        return self.overall_outer_radius * 2.0

    @property
    def total_vertical_drop_mm(self) -> float:
        """Total vertical elevation gain from hub rim to petal tip in millimeters."""
        return self.petal_length * math.sin(self.slope_radians)

    @property
    def projected_catchment_area_m2(self) -> float:
        """Total effective horizontal projected rainwater catchment area in square meters.

        Calculates the continuous circular envelope bounded by the petal tips.
        """
        radius_meters = self.overall_outer_radius / 1000.0
        return math.pi * (radius_meters**2)

    @property
    def tinaco_opening_area_m2(self) -> float:
        """Original tinaco aperture area in square meters before collector retrofit."""
        collar_radius_m = (self.tinaco_collar_diameter / 2.0) / 1000.0
        return math.pi * (collar_radius_m**2)

    @property
    def catchment_expansion_factor(self) -> float:
        """Multiplier ratio comparing collector catchment area against bare tinaco opening."""
        return self.projected_catchment_area_m2 / self.tinaco_opening_area_m2

    @classmethod
    def from_preset(cls, preset_name: str, **overrides: Any) -> CollectorParameters:
        """Construct a parameter instance using a standard tinaco tank model preset.

        Args:
            preset_name: Identification key matching standard Mexican water storage tanks.
            **overrides: Optional dimensional parameter overrides.

        Returns:
            Configured CollectorParameters instance.

        Raises:
            KeyError: If the specified preset key is unrecognized.
        """
        if preset_name not in TINACO_PRESETS:
            preset_keys = sorted(list(TINACO_PRESETS.keys()))
            raise KeyError(f"Preset {preset_name} unrecognized. Valid presets: {preset_keys}")

        preset_data = TINACO_PRESETS[preset_name]
        combined_params: Dict[str, Any] = {
            "tinaco_collar_diameter": preset_data["collar_diameter"],
            "tinaco_collar_depth": preset_data["collar_depth"],
        }
        combined_params.update(overrides)
        return cls(**combined_params)
