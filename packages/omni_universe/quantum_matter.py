"""
Elementary particles, periodic table elements, and stellar nucleosynthesis.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
from packages.omni_universe.models import CelestialType


@dataclass(frozen=True)
class ElementaryParticle:
    """Standard Model quantum particle description."""

    name: str
    symbol: str
    particle_type: str
    charge: float
    mass_mev: float
    spin: float


@dataclass(frozen=True)
class ChemicalElement:
    """Chemical element definition for cosmic matter composition."""

    atomic_number: int
    symbol: str
    name: str
    standard_atomic_weight: float
    primordial: bool


class StandardModelInventory:
    """Catalog of fundamental fermions and gauge bosons in particle physics."""

    @staticmethod
    def get_particles() -> list[ElementaryParticle]:
        """Return canonical list of Standard Model fundamental particles."""
        return [
            ElementaryParticle("up_quark", "u", "quark", 2.0 / 3.0, 2.16, 0.5),
            ElementaryParticle("down_quark", "d", "quark", -1.0 / 3.0, 4.67, 0.5),
            ElementaryParticle("charm_quark", "c", "quark", 2.0 / 3.0, 1270.0, 0.5),
            ElementaryParticle("strange_quark", "s", "quark", -1.0 / 3.0, 93.4, 0.5),
            ElementaryParticle("top_quark", "t", "quark", 2.0 / 3.0, 172690.0, 0.5),
            ElementaryParticle("bottom_quark", "b", "quark", -1.0 / 3.0, 4180.0, 0.5),
            ElementaryParticle("electron", "e-", "lepton", -1.0, 0.511, 0.5),
            ElementaryParticle("electron_neutrino", "nu_e", "lepton", 0.0, 0.000001, 0.5),
            ElementaryParticle("muon", "mu-", "lepton", -1.0, 105.66, 0.5),
            ElementaryParticle("muon_neutrino", "nu_mu", "lepton", 0.0, 0.000001, 0.5),
            ElementaryParticle("tau", "tau-", "lepton", -1.0, 1776.86, 0.5),
            ElementaryParticle("tau_neutrino", "nu_tau", "lepton", 0.0, 0.000001, 0.5),
            ElementaryParticle("photon", "gamma", "gauge_boson", 0.0, 0.0, 1.0),
            ElementaryParticle("gluon", "g", "gauge_boson", 0.0, 0.0, 1.0),
            ElementaryParticle("w_boson", "W+", "gauge_boson", 1.0, 80377.0, 1.0),
            ElementaryParticle("z_boson", "Z0", "gauge_boson", 0.0, 91187.6, 1.0),
            ElementaryParticle("higgs_boson", "H0", "scalar_boson", 0.0, 125250.0, 0.0),
        ]


class PeriodicTable:
    """Catalog of chemical elements synthesized across cosmic history."""

    ELEMENTS: list[ChemicalElement] = [
        ChemicalElement(1, "H", "Hydrogen", 1.008, True),
        ChemicalElement(2, "He", "Helium", 4.0026, True),
        ChemicalElement(3, "Li", "Lithium", 6.94, True),
        ChemicalElement(4, "Be", "Beryllium", 9.0122, False),
        ChemicalElement(6, "C", "Carbon", 12.011, False),
        ChemicalElement(7, "N", "Nitrogen", 14.007, False),
        ChemicalElement(8, "O", "Oxygen", 15.999, False),
        ChemicalElement(10, "Ne", "Neon", 20.180, False),
        ChemicalElement(12, "Mg", "Magnesium", 24.305, False),
        ChemicalElement(14, "Si", "Silicon", 28.085, False),
        ChemicalElement(16, "S", "Sulfur", 32.06, False),
        ChemicalElement(26, "Fe", "Iron", 55.845, False),
        ChemicalElement(28, "Ni", "Nickel", 58.693, False),
        ChemicalElement(79, "Au", "Gold", 196.97, False),
        ChemicalElement(92, "U", "Uranium", 238.03, False),
    ]

    @classmethod
    def find_by_symbol(cls, symbol: str) -> Optional[ChemicalElement]:
        """Look up chemical element by atomic symbol."""
        for element in cls.ELEMENTS:
            if element.symbol.lower() == symbol.lower():
                return element
        return None

    @classmethod
    def get_primordial_elements(cls) -> list[ChemicalElement]:
        """Filter elements produced during Big Bang nucleosynthesis."""
        return [el for el in cls.ELEMENTS if el.primordial]


class StellarNucleosynthesisEngine:
    """Model of stellar fusion cycles, shell burning, and supernova yields."""

    @staticmethod
    def simulate_stellar_fusion(
        mass_solar: float,
        fractional_age: float,
    ) -> dict[str, float]:
        """Compute chemical mass fractions inside a star at given life cycle fraction."""
        stage = min(max(fractional_age, 0.0), 1.0)
        if mass_solar < 0.5:
            hydrogen = max(0.1, 0.75 - (0.65 * stage))
            helium = 1.0 - hydrogen
            return {"H": round(hydrogen, 4), "He": round(helium, 4)}

        if mass_solar < 8.0:
            hydrogen = max(0.05, 0.74 - (0.69 * stage))
            helium = max(0.1, 0.24 + (0.45 * stage * (1.0 - stage)))
            carbon = max(0.0, 0.25 * (stage ** 2))
            oxygen = max(0.0, 0.05 * (stage ** 3))
            total = hydrogen + helium + carbon + oxygen
            return {
                "H": round(hydrogen / total, 4),
                "He": round(helium / total, 4),
                "C": round(carbon / total, 4),
                "O": round(oxygen / total, 4),
            }

        hydrogen = max(0.02, 0.70 - (0.68 * stage))
        helium = max(0.05, 0.26 - (0.15 * stage))
        carbon = max(0.01, 0.15 * stage)
        oxygen = max(0.01, 0.12 * (stage ** 1.5))
        silicon = max(0.005, 0.08 * (stage ** 2))
        iron = max(0.001, 0.05 * (stage ** 3))
        total = hydrogen + helium + carbon + oxygen + silicon + iron
        return {
            "H": round(hydrogen / total, 4),
            "He": round(helium / total, 4),
            "C": round(carbon / total, 4),
            "O": round(oxygen / total, 4),
            "Si": round(silicon / total, 4),
            "Fe": round(iron / total, 4),
        }

    @staticmethod
    def simulate_supernova(progenitor_mass_solar: float) -> tuple[CelestialType, dict[str, float]]:
        """Determine stellar remnant type and chemical element yield expelled into ISM."""
        if progenitor_mass_solar < 8.0:
            remnant_type = CelestialType.STAR
            yields = {"H": 0.40, "He": 0.45, "C": 0.10, "O": 0.05}
            return remnant_type, yields

        if progenitor_mass_solar <= 25.0:
            remnant_type = CelestialType.NEUTRON_STAR
            yields = {
                "He": 0.25,
                "C": 0.20,
                "O": 0.25,
                "Si": 0.15,
                "Fe": 0.10,
                "Au": 0.05,
            }
            return remnant_type, yields

        remnant_type = CelestialType.BLACK_HOLE
        yields = {
            "He": 0.15,
            "C": 0.15,
            "O": 0.30,
            "Si": 0.20,
            "Fe": 0.15,
            "U": 0.05,
        }
        return remnant_type, yields
