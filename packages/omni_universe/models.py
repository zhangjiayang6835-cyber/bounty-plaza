"""
Data structures and coordinate models for celestial entities in OmniUniverse.
"""

from __future__ import annotations
import math
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


@dataclass
class Vector3D:
    """Three-dimensional Cartesian coordinate vector with physics operations."""

    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __add__(self, other: Vector3D) -> Vector3D:
        """Add two vectors."""
        return Vector3D(self.x + other.x, self.y + other.y, self.z + other.z)

    def __sub__(self, other: Vector3D) -> Vector3D:
        """Subtract other vector from self."""
        return Vector3D(self.x - other.x, self.y - other.y, self.z - other.z)

    def __mul__(self, scalar: float) -> Vector3D:
        """Scale vector by scalar."""
        return Vector3D(self.x * scalar, self.y * scalar, self.z * scalar)

    def __rmul__(self, scalar: float) -> Vector3D:
        """Reflected scalar multiplication."""
        return self.__mul__(scalar)

    def __truediv__(self, scalar: float) -> Vector3D:
        """Divide vector by scalar."""
        if scalar == 0.0:
            raise ZeroDivisionError("Vector division by zero.")
        return Vector3D(self.x / scalar, self.y / scalar, self.z / scalar)

    def __neg__(self) -> Vector3D:
        """Negate vector components."""
        return Vector3D(-self.x, -self.y, -self.z)

    def magnitude_squared(self) -> float:
        """Calculate squared magnitude of the vector."""
        return self.x * self.x + self.y * self.y + self.z * self.z

    def magnitude(self) -> float:
        """Calculate Euclidean magnitude of the vector."""
        return math.sqrt(self.magnitude_squared())

    def distance_to(self, other: Vector3D) -> float:
        """Calculate Euclidean distance to target vector."""
        return (self - other).magnitude()

    def distance_squared_to(self, other: Vector3D) -> float:
        """Calculate squared Euclidean distance to target vector."""
        return (self - other).magnitude_squared()

    def normalize(self) -> Vector3D:
        """Return unit vector along the same direction."""
        mag = self.magnitude()
        if mag == 0.0:
            return Vector3D(0.0, 0.0, 0.0)
        return self / mag

    def dot(self, other: Vector3D) -> float:
        """Calculate scalar dot product with other vector."""
        return self.x * other.x + self.y * other.y + self.z * other.z

    def cross(self, other: Vector3D) -> Vector3D:
        """Calculate cross product with other vector."""
        return Vector3D(
            self.y * other.z - self.z * other.y,
            self.z * other.x - self.x * other.z,
            self.x * other.y - self.y * other.x,
        )

    def to_tuple(self) -> tuple[float, float, float]:
        """Convert vector to coordinate tuple."""
        return (self.x, self.y, self.z)

    def to_dict(self) -> dict[str, float]:
        """Serialize vector to dictionary representation."""
        return {"x": self.x, "y": self.y, "z": self.z}

    @classmethod
    def from_dict(cls, data: dict[str, float]) -> Vector3D:
        """Instantiate vector from coordinate mapping."""
        return cls(
            x=float(data.get("x", 0.0)),
            y=float(data.get("y", 0.0)),
            z=float(data.get("z", 0.0)),
        )


class CelestialType(str, Enum):
    """Taxonomy of astronomical and cosmological structures."""

    SUPERCLUSTER = "supercluster"
    GALAXY = "galaxy"
    NEBULA = "nebula"
    STAR = "star"
    BLACK_HOLE = "black_hole"
    NEUTRON_STAR = "neutron_star"
    PLANET = "planet"
    MOON = "moon"
    ASTEROID = "asteroid"
    COMET = "comet"


class SpectralClass(str, Enum):
    """Morgan-Keenan stellar spectral classifications."""

    O = "O"
    B = "B"
    A = "A"
    F = "F"
    G = "G"
    K = "K"
    M = "M"
    WHITE_DWARF = "D"
    COMPACT = "COMPACT"


class GalaxyMorphology(str, Enum):
    """Hubble sequence morphological types for galaxies."""

    SPIRAL = "spiral"
    BARRED_SPIRAL = "barred_spiral"
    ELLIPTICAL = "elliptical"
    IRREGULAR = "irregular"


class CosmicEpoch(str, Enum):
    """Chronological epochs in the expansion of the universe."""

    PLANCK = "planck"
    INFLATIONARY = "inflationary"
    ELECTROWEAK = "electroweak"
    QUARK_GLUON = "quark_gluon"
    HADRON = "hadron"
    LEPTON = "lepton"
    PHOTON_NUCLEOSYNTHESIS = "photon_nucleosynthesis"
    RECOMBINATION_CMB = "recombination_cmb"
    DARK_AGES = "dark_ages"
    REIONIZATION = "reionization"
    STELLIFEROUS = "stelliferous"
    DEGENERATE = "degenerate"
    BLACK_HOLE_ERA = "black_hole_era"
    HEAT_DEATH = "heat_death"


@dataclass
class CelestialEntity:
    """Physical state and astrophysical properties of a simulated cosmic body."""

    entity_id: str
    name: str
    entity_type: CelestialType
    mass: float
    radius: float
    position: Vector3D = field(default_factory=Vector3D)
    velocity: Vector3D = field(default_factory=Vector3D)
    luminosity: float = 0.0
    temperature: float = 0.0
    spectral_class: Optional[SpectralClass] = None
    parent_id: Optional[str] = None
    composition: dict[str, float] = field(default_factory=dict)
    metadata: dict[str, Any] = field(default_factory=dict)
    children_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize entity to JSON-compatible dictionary."""
        return {
            "entity_id": self.entity_id,
            "name": self.name,
            "entity_type": self.entity_type.value,
            "mass": self.mass,
            "radius": self.radius,
            "position": self.position.to_dict(),
            "velocity": self.velocity.to_dict(),
            "luminosity": self.luminosity,
            "temperature": self.temperature,
            "spectral_class": self.spectral_class.value if self.spectral_class else None,
            "parent_id": self.parent_id,
            "composition": dict(self.composition),
            "metadata": dict(self.metadata),
            "children_ids": list(self.children_ids),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> CelestialEntity:
        """Reconstruct entity instance from dictionary representation."""
        spec = data.get("spectral_class")
        return cls(
            entity_id=str(data["entity_id"]),
            name=str(data["name"]),
            entity_type=CelestialType(data["entity_type"]),
            mass=float(data["mass"]),
            radius=float(data["radius"]),
            position=Vector3D.from_dict(data.get("position", {})),
            velocity=Vector3D.from_dict(data.get("velocity", {})),
            luminosity=float(data.get("luminosity", 0.0)),
            temperature=float(data.get("temperature", 0.0)),
            spectral_class=SpectralClass(spec) if spec else None,
            parent_id=data.get("parent_id"),
            composition=dict(data.get("composition", {})),
            metadata=dict(data.get("metadata", {})),
            children_ids=list(data.get("children_ids", [])),
        )
