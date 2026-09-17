"""
Cosmological evolution, Lambda-CDM expansion, epochs, and entropy metrics.
"""

from __future__ import annotations
import math
from packages.omni_universe.constants import (
    HUBBLE_CONSTANT,
    CMB_TEMPERATURE_NOW,
    BOLTZMANN_CONSTANT,
    GRAVITATIONAL_CONSTANT,
    REDUCED_PLANCK_CONSTANT,
    SPEED_OF_LIGHT,
    UNIVERSE_AGE_SECONDS,
)
from packages.omni_universe.models import CosmicEpoch


class CosmologicalEngine:
    """Cosmological dynamics model based on the Lambda-CDM standard model."""

    EPOCH_THRESHOLDS: list[tuple[float, CosmicEpoch]] = [
        (1e-43, CosmicEpoch.PLANCK),
        (1e-32, CosmicEpoch.INFLATIONARY),
        (1e-12, CosmicEpoch.ELECTROWEAK),
        (1e-6, CosmicEpoch.QUARK_GLUON),
        (1.0, CosmicEpoch.HADRON),
        (10.0, CosmicEpoch.LEPTON),
        (1200.0, CosmicEpoch.PHOTON_NUCLEOSYNTHESIS),
        (380000.0 * 365.25 * 86400.0, CosmicEpoch.RECOMBINATION_CMB),
        (100e6 * 365.25 * 86400.0, CosmicEpoch.DARK_AGES),
        (1e9 * 365.25 * 86400.0, CosmicEpoch.REIONIZATION),
        (100e12 * 365.25 * 86400.0, CosmicEpoch.STELLIFEROUS),
        (1e40 * 365.25 * 86400.0, CosmicEpoch.DEGENERATE),
        (1e100 * 365.25 * 86400.0, CosmicEpoch.BLACK_HOLE_ERA),
    ]

    def __init__(
        self,
        hubble_constant: float = HUBBLE_CONSTANT,
        omega_matter: float = 0.315,
        omega_lambda: float = 0.685,
        omega_radiation: float = 9.0e-5,
    ) -> None:
        """Initialize cosmological model with specified density parameters."""
        self.hubble_constant = float(hubble_constant)
        self.omega_matter = float(omega_matter)
        self.omega_lambda = float(omega_lambda)
        self.omega_radiation = float(omega_radiation)

    @classmethod
    def get_epoch_for_age(cls, age_seconds: float) -> CosmicEpoch:
        """Determine cosmological epoch corresponding to elapsed time since Big Bang."""
        for limit, epoch in cls.EPOCH_THRESHOLDS:
            if age_seconds < limit:
                return epoch
        return CosmicEpoch.HEAT_DEATH

    def hubble_parameter_at_redshift(self, redshift: float) -> float:
        """Calculate Hubble parameter H(z) at cosmological redshift z."""
        if redshift < -1.0:
            raise ValueError("Redshift cannot be less than -1.0.")
        term_m = self.omega_matter * ((1.0 + redshift) ** 3)
        term_r = self.omega_radiation * ((1.0 + redshift) ** 4)
        term_l = self.omega_lambda
        e_z = math.sqrt(term_m + term_r + term_l)
        return self.hubble_constant * e_z

    @staticmethod
    def cmb_temperature_at_redshift(redshift: float) -> float:
        """Calculate Cosmic Microwave Background radiation temperature at redshift z."""
        if redshift < -1.0:
            raise ValueError("Redshift cannot be less than -1.0.")
        return CMB_TEMPERATURE_NOW * (1.0 + redshift)

    @staticmethod
    def cosmic_scale_factor(redshift: float) -> float:
        """Calculate cosmic expansion scale factor a(t) normalized to 1.0 today."""
        if redshift <= -1.0:
            raise ValueError("Redshift must be greater than -1.0.")
        return 1.0 / (1.0 + redshift)

    def cosmic_energy_inventory(self) -> dict[str, float]:
        """Return fractional energy density components of the cosmos."""
        total = self.omega_matter + self.omega_lambda + self.omega_radiation
        return {
            "dark_energy": self.omega_lambda / total,
            "matter_total": self.omega_matter / total,
            "baryonic_matter": 0.049 / total,
            "cold_dark_matter": (self.omega_matter - 0.049) / total,
            "radiation": self.omega_radiation / total,
        }

    @staticmethod
    def bekenstein_hawking_entropy(black_hole_mass_kg: float) -> float:
        """Calculate thermodynamic entropy of a Schwarzschild black hole in Joules/Kelvin."""
        if black_hole_mass_kg <= 0.0:
            return 0.0
        numerator = 4.0 * math.pi * BOLTZMANN_CONSTANT * GRAVITATIONAL_CONSTANT * (black_hole_mass_kg ** 2)
        denominator = REDUCED_PLANCK_CONSTANT * SPEED_OF_LIGHT
        return numerator / denominator

    def calculate_cosmic_state(self, age_seconds: float = UNIVERSE_AGE_SECONDS) -> dict[str, float | str]:
        """Generate high-level state descriptor for given cosmic age."""
        epoch = self.get_epoch_for_age(age_seconds)
        age_gyr = age_seconds / (1e9 * 365.25 * 86400.0)
        return {
            "epoch": epoch.value,
            "age_seconds": age_seconds,
            "age_gigayears": age_gyr,
            "cmb_temperature_k": CMB_TEMPERATURE_NOW,
            "hubble_constant": self.hubble_constant,
        }
