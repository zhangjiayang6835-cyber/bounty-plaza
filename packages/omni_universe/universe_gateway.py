"""
High-level OmniUniverse gateway orchestrating cosmology, physics, generation, and settlement.
"""

from __future__ import annotations
from typing import Any, Optional
from packages.omni_universe.constants import (
    UNIVERSE_AGE_SECONDS,
)
from packages.omni_universe.cosmology import CosmologicalEngine
from packages.omni_universe.generator import (
    ProceduralUniverseGenerator,
    SpatialGridIndex,
)
from packages.omni_universe.models import (
    CelestialEntity,
    CelestialType,
    CosmicEpoch,
    GalaxyMorphology,
    SpectralClass,
    Vector3D,
)
from packages.omni_universe.physics import GravitationalSimulator
from packages.omni_universe.quantum_matter import StellarNucleosynthesisEngine
from packages.omni_universe.settlement import (
    QuadrillionSettlementEngine,
    SettlementReceipt,
)


class OmniUniverse:
    """Unified cosmic universe simulator for OmniBlocks visual execution and settlement."""

    def __init__(self, seed: str | int = "omniblocks_universe_genesis") -> None:
        """Initialize simulation environment with cosmological engine and spatial index."""
        self.seed = str(seed)
        self.cosmology = CosmologicalEngine()
        self.physics = GravitationalSimulator()
        self.generator = ProceduralUniverseGenerator(self.seed)
        self.spatial_index = SpatialGridIndex()
        self.entities: dict[str, CelestialEntity] = {}
        self.age_seconds: float = UNIVERSE_AGE_SECONDS
        self.epoch: CosmicEpoch = self.cosmology.get_epoch_for_age(self.age_seconds)

    def set_epoch(self, epoch: str | CosmicEpoch) -> None:
        """Explicitly override cosmic epoch."""
        if isinstance(epoch, str):
            self.epoch = CosmicEpoch(epoch.lower())
        else:
            self.epoch = epoch

    def set_age_gyr(self, age_gyr: float) -> None:
        """Update simulated age of the universe in gigayears."""
        if age_gyr < 0.0:
            raise ValueError("Age cannot be negative.")
        self.age_seconds = age_gyr * 1e9 * 365.25 * 86400.0
        self.epoch = self.cosmology.get_epoch_for_age(self.age_seconds)

    def add_entity(self, entity: CelestialEntity) -> None:
        """Insert celestial entity into universe registry and spatial index."""
        self.entities[entity.entity_id] = entity
        self.spatial_index.insert(entity)

    def get_entity(self, entity_id: str) -> Optional[CelestialEntity]:
        """Retrieve entity by its unique identifier."""
        return self.entities.get(entity_id)

    def get_all_entities(self) -> list[CelestialEntity]:
        """Return list of all registered celestial entities."""
        return list(self.entities.values())

    def find_entities_by_type(self, entity_type: CelestialType) -> list[CelestialEntity]:
        """Filter universe entities by celestial taxonomy type."""
        return [e for e in self.entities.values() if e.entity_type == entity_type]

    def find_entities_in_radius(self, center: Vector3D, radius: float) -> list[CelestialEntity]:
        """Query spatial index for bodies within spherical distance from center."""
        return self.spatial_index.query_radius(center, radius)

    def spawn_galaxy(
        self,
        name: str,
        morphology: str = "spiral",
        stars: int = 5,
        center: Optional[Vector3D] = None,
    ) -> list[CelestialEntity]:
        """Procedurally generate and register a galaxy with central black hole and stars."""
        morph_enum = GalaxyMorphology(morphology.lower())
        galaxy_id = f"gal_{name.lower().replace(' ', '_')}"
        created = self.generator.generate_galaxy(
            galaxy_id=galaxy_id,
            name=name,
            morphology=morph_enum,
            center=center,
            stellar_count=stars,
        )
        for entity in created:
            self.add_entity(entity)
        return created

    def step(self, years: float, substeps: int = 1) -> None:
        """Advance cosmological time and integrate gravitational N-body orbits."""
        if years <= 0.0 or substeps < 1:
            return
        total_seconds = years * 365.25 * 86400.0
        dt = total_seconds / substeps
        bodies = list(self.entities.values())

        for _ in range(substeps):
            self.physics.step_nbody(bodies, dt)
            self.age_seconds += dt

        self.epoch = self.cosmology.get_epoch_for_age(self.age_seconds)

    def trigger_supernova(self, star_id: str) -> tuple[CelestialEntity, dict[str, float]]:
        """Trigger core-collapse supernova, mutate star into remnant, and return nucleosynthesis yields."""
        star = self.get_entity(star_id)
        if not star:
            raise KeyError(f"Star not found: {star_id}")
        if star.entity_type != CelestialType.STAR:
            raise ValueError(f"Entity {star_id} is not a star.")

        solar_masses = star.mass / 1.98847e30
        remnant_type, yields = StellarNucleosynthesisEngine.simulate_supernova(solar_masses)

        star.entity_type = remnant_type
        if remnant_type == CelestialType.BLACK_HOLE:
            star.name = f"{star.name} (Black Hole Remnant)"
            star.spectral_class = SpectralClass.COMPACT
            star.radius = self.physics.schwarzschild_radius(star.mass)
            star.luminosity = 0.0
        elif remnant_type == CelestialType.NEUTRON_STAR:
            star.name = f"{star.name} (Pulsar Remnant)"
            star.spectral_class = SpectralClass.COMPACT
            star.radius = 12000.0
            star.luminosity = 1e20
        else:
            star.name = f"{star.name} (White Dwarf)"
            star.spectral_class = SpectralClass.WHITE_DWARF
            star.radius = 6.0e6
            star.luminosity = 1e23

        star.composition = yields
        return star, yields

    def execute_bounty_settlement(
        self,
        evm_address: str,
        stellar_address: str,
    ) -> SettlementReceipt:
        """Execute exact arbitrary-precision settlement for Issue #1575."""
        return QuadrillionSettlementEngine.calculate_settlement(
            evm_address=evm_address,
            stellar_address=stellar_address,
        )

    def get_summary(self) -> dict[str, Any]:
        """Compile comprehensive metrics of cosmic simulation."""
        type_counts: dict[str, int] = {}
        for entity in self.entities.values():
            key = entity.entity_type.value
            type_counts[key] = type_counts.get(key, 0) + 1

        return {
            "seed": self.seed,
            "epoch": self.epoch.value,
            "age_seconds": self.age_seconds,
            "age_gigayears": self.age_seconds / (1e9 * 365.25 * 86400.0),
            "total_entities": len(self.entities),
            "entity_breakdown": type_counts,
            "hubble_constant": self.cosmology.hubble_constant,
            "cosmic_energy": self.cosmology.cosmic_energy_inventory(),
        }
