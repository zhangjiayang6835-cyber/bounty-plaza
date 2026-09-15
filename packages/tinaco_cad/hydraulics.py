"""Hydraulic simulation and rainwater harvesting calculations for Mexico City tinaco retrofit."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict
from packages.tinaco_cad.params import CollectorParameters


CDMX_STORM_INTENSITIES: Dict[str, float] = {
    "light_shower": 5.0,
    "moderate_rain": 15.0,
    "typical_summer_storm": 30.0,
    "heavy_downpour_10yr": 65.0,
    "torrential_cloudburst_50yr": 110.0,
}

CDMX_MONTHLY_PRECIPITATION_MM: Dict[str, float] = {
    "january": 10.0,
    "february": 7.0,
    "march": 13.0,
    "april": 27.0,
    "may": 58.0,
    "june": 138.0,
    "july": 175.0,
    "august": 169.0,
    "september": 142.0,
    "october": 67.0,
    "november": 12.0,
    "december": 8.0,
}


@dataclass
class HydraulicAssessment:
    """Comprehensive performance metrics of rainwater catchment and drainage.

    Attributes:
        catchment_area_m2: Effective horizontal projected collection area (m^2).
        peak_inflow_liters_per_sec: Inflow discharge rate under peak torrential storm (L/s).
        drain_capacity_liters_per_sec: Maximum gravity discharge capacity through drain (L/s).
        hydraulic_safety_margin: Ratio of drain discharge capacity over peak storm inflow.
        annual_harvest_volume_liters: Total expected clean water harvested annually (L).
        filling_time_minutes_rotoplas_1100: Time to fill an 1100L tank during typical downpour.
        anti_overflow_verified: Boolean flag indicating drain outpaces peak storm inflow.
    """

    catchment_area_m2: float
    peak_inflow_liters_per_sec: float
    drain_capacity_liters_per_sec: float
    hydraulic_safety_margin: float
    annual_harvest_volume_liters: float
    filling_time_minutes_rotoplas_1100: float
    anti_overflow_verified: bool


class HydraulicEngine:
    """Hydrodynamic calculation engine for parametric tinaco rainwater collectors."""

    GRAVITY_ACCEL: float = 9.80665
    RUNOFF_COEFFICIENT_HDPE: float = 0.95
    ORIFICE_DISCHARGE_COEFF: float = 0.62
    FILTER_RETENTION_EFFICIENCY: float = 0.92

    def __init__(self, params: CollectorParameters) -> None:
        """Initialize engine with collector geometry specifications.

        Args:
            params: Validated collector configuration parameters.
        """
        self.params = params

    def calculate_peak_inflow(self, storm_intensity_mm_h: float) -> float:
        """Calculate peak rainwater catchment inflow using Rational Method.

        Args:
            storm_intensity_mm_h: Rainfall intensity rate in millimeters per hour.

        Returns:
            Discharge inflow rate in liters per second.
        """
        area_m2 = self.params.projected_catchment_area_m2
        intensity_m_s = (storm_intensity_mm_h / 1000.0) / 3600.0
        inflow_m3_s = self.RUNOFF_COEFFICIENT_HDPE * intensity_m_s * area_m2
        return inflow_m3_s * 1000.0

    def calculate_drain_capacity(self, hydraulic_head_mm: float | None = None) -> float:
        """Calculate gravity discharge flow through central hub orifice.

        Args:
            hydraulic_head_mm: Water level head above orifice in millimeters.
                Defaults to full hub height.

        Returns:
            Maximum outflow discharge rate in liters per second.
        """
        head_m = (hydraulic_head_mm or self.params.hub_height) / 1000.0
        drain_radius_m = self.params.drain_radius / 1000.0
        orifice_area_m2 = math.pi * (drain_radius_m**2)

        velocity_m_s = math.sqrt(2.0 * self.GRAVITY_ACCEL * head_m)
        discharge_m3_s = self.ORIFICE_DISCHARGE_COEFF * orifice_area_m2 * velocity_m_s
        return discharge_m3_s * 1000.0

    def calculate_annual_yield(self) -> float:
        """Estimate total clean water captured across typical Mexico City hydrological year.

        Returns:
            Annual volume in liters after filtration and first-flush deductions.
        """
        area_m2 = self.params.projected_catchment_area_m2
        annual_depth_m = self.params.cdmx_annual_rainfall_mm / 1000.0
        gross_volume_liters = area_m2 * annual_depth_m * 1000.0
        net_harvest = (
            gross_volume_liters
            * self.RUNOFF_COEFFICIENT_HDPE
            * self.FILTER_RETENTION_EFFICIENCY
        )
        return net_harvest

    def assess_performance(self) -> HydraulicAssessment:
        """Execute comprehensive evaluation against Mexico City precipitation benchmarks.

        Returns:
            Populated HydraulicAssessment data instance.
        """
        peak_intensity = CDMX_STORM_INTENSITIES["torrential_cloudburst_50yr"]
        peak_inflow = self.calculate_peak_inflow(peak_intensity)
        drain_cap = self.calculate_drain_capacity()

        safety_margin = drain_cap / max(peak_inflow, 1e-6)
        annual_yield = self.calculate_annual_yield()

        typical_storm_intensity = CDMX_STORM_INTENSITIES["typical_summer_storm"]
        typical_inflow = self.calculate_peak_inflow(typical_storm_intensity)
        minutes_to_fill_1100l = (1100.0 / max(typical_inflow, 1e-6)) / 60.0

        return HydraulicAssessment(
            catchment_area_m2=round(self.params.projected_catchment_area_m2, 4),
            peak_inflow_liters_per_sec=round(peak_inflow, 4),
            drain_capacity_liters_per_sec=round(drain_cap, 4),
            hydraulic_safety_margin=round(safety_margin, 2),
            annual_harvest_volume_liters=round(annual_yield, 1),
            filling_time_minutes_rotoplas_1100=round(minutes_to_fill_1100l, 1),
            anti_overflow_verified=safety_margin >= 1.5,
        )
