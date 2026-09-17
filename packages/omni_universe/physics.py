"""
Astrophysical laws, relativistic limits, and N-body gravitational integration.
"""

from __future__ import annotations
import math
from typing import Sequence
from packages.omni_universe.constants import (
    GRAVITATIONAL_CONSTANT,
    SPEED_OF_LIGHT,
    SOLAR_MASS,
    SOLAR_LUMINOSITY,
    STEFAN_BOLTZMANN_CONSTANT,
)
from packages.omni_universe.models import (
    Vector3D,
    CelestialEntity,
    SpectralClass,
)


class GravitationalSimulator:
    """Numerical N-body symplectic gravitational engine with relativistic safety bounds."""

    def __init__(self, softening_length: float = 1e6) -> None:
        """Initialize simulator with Plummer softening length in meters."""
        self.softening_length = float(softening_length)
        self.softening_squared = self.softening_length * self.softening_length

    def compute_acceleration(
        self,
        target: CelestialEntity,
        bodies: Sequence[CelestialEntity],
    ) -> Vector3D:
        """Calculate total gravitational acceleration vector acting on target entity."""
        accel = Vector3D(0.0, 0.0, 0.0)
        target_pos = target.position
        for body in bodies:
            if body.entity_id == target.entity_id:
                continue
            delta = body.position - target_pos
            dist_sq = delta.magnitude_squared() + self.softening_squared
            dist = math.sqrt(dist_sq)
            if dist == 0.0:
                continue
            force_scalar = (GRAVITATIONAL_CONSTANT * body.mass) / (dist_sq * dist)
            accel = accel + (delta * force_scalar)
        return accel

    def step_nbody(self, bodies: list[CelestialEntity], dt: float) -> None:
        """Execute one symplectic Velocity-Verlet integration step across all entities."""
        if not bodies or dt == 0.0:
            return

        accelerations = [self.compute_acceleration(b, bodies) for b in bodies]

        for i, body in enumerate(bodies):
            a_curr = accelerations[i]
            body.position = body.position + (body.velocity * dt) + (a_curr * (0.5 * dt * dt))

        new_accelerations = [self.compute_acceleration(b, bodies) for b in bodies]

        c_limit = 0.9999 * SPEED_OF_LIGHT
        for i, body in enumerate(bodies):
            a_avg = (accelerations[i] + new_accelerations[i]) * 0.5
            new_vel = body.velocity + (a_avg * dt)
            speed = new_vel.magnitude()
            if speed > c_limit:
                new_vel = new_vel.normalize() * c_limit
            body.velocity = new_vel

    @staticmethod
    def schwarzschild_radius(mass: float) -> float:
        """Calculate event horizon radius for a Schwarzschild black hole."""
        if mass <= 0.0:
            return 0.0
        return (2.0 * GRAVITATIONAL_CONSTANT * mass) / (SPEED_OF_LIGHT * SPEED_OF_LIGHT)

    @staticmethod
    def keplerian_orbital_velocity(central_mass: float, orbital_radius: float) -> float:
        """Calculate circular orbital speed at given radius around a central mass."""
        if central_mass <= 0.0 or orbital_radius <= 0.0:
            return 0.0
        return math.sqrt((GRAVITATIONAL_CONSTANT * central_mass) / orbital_radius)

    @staticmethod
    def orbital_period(central_mass: float, semi_major_axis: float) -> float:
        """Calculate Keplerian orbital period in seconds."""
        if central_mass <= 0.0 or semi_major_axis <= 0.0:
            return 0.0
        return 2.0 * math.pi * math.sqrt((semi_major_axis ** 3) / (GRAVITATIONAL_CONSTANT * central_mass))

    @staticmethod
    def escape_velocity(central_mass: float, radius: float) -> float:
        """Calculate minimum velocity required to escape gravitational field."""
        if central_mass <= 0.0 or radius <= 0.0:
            return 0.0
        return math.sqrt((2.0 * GRAVITATIONAL_CONSTANT * central_mass) / radius)

    @staticmethod
    def stellar_luminosity_from_mass(mass_kg: float) -> float:
        """Calculate stellar luminosity using the standard mass-luminosity relation."""
        if mass_kg <= 0.0:
            return 0.0
        m_solar = mass_kg / SOLAR_MASS
        return SOLAR_LUMINOSITY * (m_solar ** 3.5)

    @staticmethod
    def effective_temperature(luminosity_watts: float, radius_meters: float) -> float:
        """Calculate stellar surface temperature via Stefan-Boltzmann radiation law."""
        if luminosity_watts <= 0.0 or radius_meters <= 0.0:
            return 0.0
        surface_area = 4.0 * math.pi * (radius_meters ** 2)
        flux = luminosity_watts / surface_area
        return (flux / STEFAN_BOLTZMANN_CONSTANT) ** 0.25

    @staticmethod
    def determine_spectral_class(temperature_kelvin: float) -> SpectralClass:
        """Map surface temperature to standard Morgan-Keenan spectral classification."""
        if temperature_kelvin >= 30000.0:
            return SpectralClass.O
        if temperature_kelvin >= 10000.0:
            return SpectralClass.B
        if temperature_kelvin >= 7500.0:
            return SpectralClass.A
        if temperature_kelvin >= 6000.0:
            return SpectralClass.F
        if temperature_kelvin >= 5200.0:
            return SpectralClass.G
        if temperature_kelvin >= 3700.0:
            return SpectralClass.K
        if temperature_kelvin >= 2400.0:
            return SpectralClass.M
        return SpectralClass.WHITE_DWARF
