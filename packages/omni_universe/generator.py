"""
Deterministic procedural universe synthesis, celestial hierarchies, and spatial indexing.
"""

from __future__ import annotations
import hashlib
import math
from typing import Iterator, Optional
from packages.omni_universe.constants import (
    ASTRONOMICAL_UNIT,
    EARTH_MASS,
    EARTH_RADIUS,
    KILOPARSEC,
    SOLAR_MASS,
    SOLAR_RADIUS,
)
from packages.omni_universe.models import (
    CelestialEntity,
    CelestialType,
    GalaxyMorphology,
    SpectralClass,
    Vector3D,
)
from packages.omni_universe.physics import GravitationalSimulator


class DeterministicRNG:
    """Cryptographic SHA-256 pseudo-random generator guaranteeing cross-platform determinism."""

    def __init__(self, seed: str | int) -> None:
        """Initialize generator state from seed representation."""
        self.state_seed = str(seed).encode("utf-8")
        self.counter = 0

    def next_float(self) -> float:
        """Produce floating-point value in interval [0.0, 1.0)."""
        data = self.state_seed + self.counter.to_bytes(8, byteorder="big")
        digest = hashlib.sha256(data).digest()
        self.counter += 1
        int_val = int.from_bytes(digest[:8], byteorder="big")
        return int_val / (2.0 ** 64)

    def uniform(self, low: float, high: float) -> float:
        """Produce uniform float within [low, high)."""
        return low + (self.next_float() * (high - low))

    def randint(self, low: int, high: int) -> int:
        """Produce inclusive uniform random integer."""
        return int(low + math.floor(self.next_float() * (high - low + 1)))


class SpatialGridIndex:
    """Three-dimensional spatial hash grid for cosmological entity radius queries."""

    def __init__(self, cell_size: float = 100.0 * ASTRONOMICAL_UNIT) -> None:
        """Initialize spatial index with cubic grid cell diameter."""
        self.cell_size = float(cell_size)
        self.grid: dict[tuple[int, int, int], list[CelestialEntity]] = {}

    def _hash_position(self, pos: Vector3D) -> tuple[int, int, int]:
        """Map 3D Cartesian coordinates to integer grid cell index."""
        return (
            math.floor(pos.x / self.cell_size),
            math.floor(pos.y / self.cell_size),
            math.floor(pos.z / self.cell_size),
        )

    def insert(self, entity: CelestialEntity) -> None:
        """Index celestial entity into corresponding grid cell."""
        cell = self._hash_position(entity.position)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(entity)

    @staticmethod
    def _iter_bounding_cells(
        min_cell: tuple[int, int, int],
        max_cell: tuple[int, int, int],
    ) -> Iterator[tuple[int, int, int]]:
        """Yield discrete coordinate triplets bounded by spatial box."""
        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                for cz in range(min_cell[2], max_cell[2] + 1):
                    yield (cx, cy, cz)

    def query_radius(self, center: Vector3D, radius: float) -> list[CelestialEntity]:
        """Find all indexed entities located within spherical radius of center."""
        results: list[CelestialEntity] = []
        r_squared = radius * radius
        min_cell = self._hash_position(center - Vector3D(radius, radius, radius))
        max_cell = self._hash_position(center + Vector3D(radius, radius, radius))

        for cell in self._iter_bounding_cells(min_cell, max_cell):
            for entity in self.grid.get(cell, []):
                if entity.position.distance_squared_to(center) <= r_squared:
                    results.append(entity)
        return results


class ProceduralUniverseGenerator:
    """Procedural synthesis of multi-tier cosmic structures using deterministic seeding."""

    def __init__(self, seed: str | int = "omniblocks_universe_genesis") -> None:
        """Initialize generator with master universe seed."""
        self.seed = str(seed)
        self.rng = DeterministicRNG(self.seed)

    def generate_galaxy(
        self,
        galaxy_id: str,
        name: str,
        morphology: GalaxyMorphology = GalaxyMorphology.SPIRAL,
        center: Optional[Vector3D] = None,
        stellar_count: int = 5,
    ) -> list[CelestialEntity]:
        """Synthesize galaxy core black hole and surrounding stellar systems."""
        pos = center if center is not None else Vector3D(0.0, 0.0, 0.0)
        entities: list[CelestialEntity] = []

        smbh_mass = 4.154e6 * SOLAR_MASS
        smbh_radius = GravitationalSimulator.schwarzschild_radius(smbh_mass)
        smbh = CelestialEntity(
            entity_id=f"{galaxy_id}_smbh",
            name=f"{name} Core Black Hole",
            entity_type=CelestialType.BLACK_HOLE,
            mass=smbh_mass,
            radius=smbh_radius,
            position=pos,
            velocity=Vector3D(0.0, 0.0, 0.0),
            spectral_class=SpectralClass.COMPACT,
            parent_id=galaxy_id,
            metadata={"morphology": morphology.value},
        )
        entities.append(smbh)

        for i in range(stellar_count):
            arm_angle = (i * (2.0 * math.pi / max(stellar_count, 1))) + self.rng.uniform(-0.2, 0.2)
            distance = (8.0 + (i * 2.0)) * KILOPARSEC
            x = pos.x + distance * math.cos(arm_angle)
            y = pos.y + distance * math.sin(arm_angle)
            z = pos.z + self.rng.uniform(-0.1, 0.1) * KILOPARSEC
            star_pos = Vector3D(x, y, z)

            orb_speed = GravitationalSimulator.keplerian_orbital_velocity(smbh_mass, distance)
            star_vel = Vector3D(-orb_speed * math.sin(arm_angle), orb_speed * math.cos(arm_angle), 0.0)

            star_system = self.generate_star_system(
                star_id=f"{galaxy_id}_star_{i+1}",
                name=f"{name} Sector-{i+1} Star",
                position=star_pos,
                velocity=star_vel,
                planets_count=self.rng.randint(2, 5),
            )
            entities.extend(star_system)

        return entities

    def _generate_planets(self, star: CelestialEntity, count: int) -> list[CelestialEntity]:
        """Synthesize orbiting planetary bodies for given host star."""
        planets: list[CelestialEntity] = []
        labels = ["Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta"]
        for p in range(count):
            label = labels[p % len(labels)]
            orb_dist = (0.4 + (p * 0.8)) * ASTRONOMICAL_UNIT
            orb_speed = GravitationalSimulator.keplerian_orbital_velocity(star.mass, orb_dist)

            angle = self.rng.uniform(0.0, 2.0 * math.pi)
            p_pos = star.position + Vector3D(orb_dist * math.cos(angle), orb_dist * math.sin(angle), 0.0)
            p_vel = star.velocity + Vector3D(-orb_speed * math.sin(angle), orb_speed * math.cos(angle), 0.0)

            is_gas = p >= 2
            p_mass = (self.rng.uniform(50.0, 300.0) if is_gas else self.rng.uniform(0.2, 5.0)) * EARTH_MASS
            p_radius = (self.rng.uniform(4.0, 11.0) if is_gas else self.rng.uniform(0.5, 2.0)) * EARTH_RADIUS

            planet = CelestialEntity(
                entity_id=f"{star.entity_id}_planet_{p+1}",
                name=f"{star.name} {label}",
                entity_type=CelestialType.PLANET,
                mass=p_mass,
                radius=p_radius,
                position=p_pos,
                velocity=p_vel,
                parent_id=star.entity_id,
                metadata={"semi_major_axis_au": orb_dist / ASTRONOMICAL_UNIT, "is_gas_giant": is_gas},
            )
            star.children_ids.append(planet.entity_id)
            planets.append(planet)
        return planets

    def generate_star_system(
        self,
        star_id: str,
        name: str,
        position: Vector3D,
        velocity: Vector3D,
        planets_count: int = 3,
    ) -> list[CelestialEntity]:
        """Synthesize central host star and orbiting planetary bodies."""
        mass_factor = self.rng.uniform(0.7, 2.5)
        star_mass = mass_factor * SOLAR_MASS
        star_radius = (mass_factor ** 0.8) * SOLAR_RADIUS
        star_lum = GravitationalSimulator.stellar_luminosity_from_mass(star_mass)
        star_temp = GravitationalSimulator.effective_temperature(star_lum, star_radius)
        star_spec = GravitationalSimulator.determine_spectral_class(star_temp)

        star = CelestialEntity(
            entity_id=star_id,
            name=name,
            entity_type=CelestialType.STAR,
            mass=star_mass,
            radius=star_radius,
            position=position,
            velocity=velocity,
            luminosity=star_lum,
            temperature=star_temp,
            spectral_class=star_spec,
            parent_id=star_id.split("_")[0],
            composition={"H": 0.74, "He": 0.24, "metals": 0.02},
        )

        planets = self._generate_planets(star, planets_count)
        return [star] + planets
