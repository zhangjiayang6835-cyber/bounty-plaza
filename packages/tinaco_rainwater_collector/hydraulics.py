"""Hydraulic performance and rainfall runoff flow dynamics engine."""

from __future__ import annotations

import math
from dataclasses import dataclass

from packages.tinaco_rainwater_collector.models import DrainOutlet, FlowerCollectorConfig


@dataclass
class HydraulicResult:
    """Calculated flow characteristics and drainage safety metrics."""

    catchment_area_m2: float
    rainfall_intensity_mm_per_hr: float
    runoff_coefficient: float
    peak_inflow_liters_per_sec: float
    drain_bore_diameter_mm: float
    effective_head_m: float
    discharge_coefficient: float
    drain_capacity_liters_per_sec: float
    safety_factor: float
    petal_slope_gradient: float
    estimated_drainage_velocity_m_per_sec: float
    drainage_transit_time_sec: float
    is_adequate: bool


class HydraulicEngine:
    """Fluid mechanics solver for gravity-fed rainwater collection systems."""

    def __init__(self, config: FlowerCollectorConfig, outlet: DrainOutlet = None) -> None:
        """Initialize hydraulic engine with geometric configuration."""
        self.config = config
        self.outlet = outlet or DrainOutlet(
            funnel_top_diameter_mm=config.inner_funnel_diameter_mm,
            drain_bore_diameter_mm=config.drain_bore_diameter_mm,
            funnel_depth_mm=config.funnel_depth_mm,
        )

    def calculate_peak_inflow(
        self,
        rainfall_intensity_mm_per_hr: float = 80.0,
        runoff_coefficient: float = 0.95,
    ) -> float:
        """Compute peak storm inflow volume using rational method in liters per second."""
        area_m2 = self.config.catchment_area_m2
        inflow_m3_per_sec = (runoff_coefficient * rainfall_intensity_mm_per_hr * area_m2) / (
            3.6 * 1_000_000.0
        )
        return inflow_m3_per_sec * 1000.0

    def calculate_orifice_discharge(
        self,
        effective_head_m: float = 0.12,
        discharge_coefficient: float = 0.62,
    ) -> float:
        """Compute maximum gravity discharge capacity through drain bore in liters per second."""
        radius_m = (self.config.drain_bore_diameter_mm / 2.0) / 1000.0
        area_m2 = math.pi * (radius_m**2)
        gravity_accel = 9.80665
        discharge_m3_per_sec = (
            discharge_coefficient * area_m2 * math.sqrt(2.0 * gravity_accel * effective_head_m)
        )
        return discharge_m3_per_sec * 1000.0

    def calculate_petal_sheet_velocity(
        self,
        manning_roughness: float = 0.010,
        hydraulic_radius_m: float = 0.005,
    ) -> float:
        """Compute open channel surface water velocity across HDPE petal face."""
        slope_gradient = math.tan(math.radians(self.config.slope_angle_deg))
        velocity = (1.0 / manning_roughness) * (hydraulic_radius_m ** (2.0 / 3.0)) * math.sqrt(
            slope_gradient
        )
        return velocity

    def analyze(
        self,
        rainfall_intensity_mm_per_hr: float = 80.0,
        runoff_coefficient: float = 0.95,
        effective_head_m: float = 0.12,
    ) -> HydraulicResult:
        """Run complete hydraulic adequacy evaluation under specified storm parameters."""
        inflow_lps = self.calculate_peak_inflow(
            rainfall_intensity_mm_per_hr=rainfall_intensity_mm_per_hr,
            runoff_coefficient=runoff_coefficient,
        )
        capacity_lps = self.calculate_orifice_discharge(effective_head_m=effective_head_m)
        safety_factor = capacity_lps / max(inflow_lps, 1e-6)

        velocity = self.calculate_petal_sheet_velocity()
        radial_distance_m = (
            (self.config.outer_diameter_mm - self.config.inner_funnel_diameter_mm) / 2.0
        ) / 1000.0
        transit_time = radial_distance_m / max(velocity, 0.01)

        is_adequate = safety_factor >= 5.0 and transit_time <= 2.0

        return HydraulicResult(
            catchment_area_m2=round(self.config.catchment_area_m2, 4),
            rainfall_intensity_mm_per_hr=rainfall_intensity_mm_per_hr,
            runoff_coefficient=runoff_coefficient,
            peak_inflow_liters_per_sec=round(inflow_lps, 4),
            drain_bore_diameter_mm=self.config.drain_bore_diameter_mm,
            effective_head_m=effective_head_m,
            discharge_coefficient=0.62,
            drain_capacity_liters_per_sec=round(capacity_lps, 4),
            safety_factor=round(safety_factor, 2),
            petal_slope_gradient=round(math.tan(math.radians(self.config.slope_angle_deg)), 4),
            estimated_drainage_velocity_m_per_sec=round(velocity, 4),
            drainage_transit_time_sec=round(transit_time, 4),
            is_adequate=is_adequate,
        )
