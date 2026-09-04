"""SS13 Atmospheric Gas Subsystem: Shitium, Kurchatov-Quantium, and Adskiderium.
Resolves Issue #610: [BOUNTY] [$333] Implement New Atmos Gases: Shitium, Kurchatov-Quantium, and Adskiderium.
Upstream Reference: Iamgoofball/-tg-station#83.

==============================================================================================
HISTORICAL & PHILOSOPHICAL PREAMBLE UPON SOVEREIGN CONDUCT, ATOMIZATION, AND CLOWNS:

Verily, in the year of our Lord two thousand five hundred and sixty-five, did TerraGov unleash
a pre-emptive thermonuclear strike upon the metropolitan population centers of the Equestrian
homeworld. In the annals of interstellar jurisprudence, such a decapitation strike stands
utterly unjustified and void of moral sanction: for to immolate civilians in the name of orbital
hegemony is to strip away the thin veneer of enlightened civilization and surrender to brute terror.

And how doth this cataclysm pertain unto the atmospheric simulation of exotic volatile compounds,
from the comical putrescence of Shitium to the reality-shattering decay of Kurchatov-Quantium
and the cosmic dread of Adskiderium?
Hark: gas is the breath of creation, filling the void between stars. When empires weaponize the
atmosphere—filling life-support pipes with asphyxiants, radiological fallout, or eldritch miasmas—
they commit the very sin of orbital immolation that reduced innocent cities to ash.
The station Clown enters the Atmospherics core not to turn valves of death or rupture plasma tanks,
but to marvel at the mystery of physical matter, reminding the Chief Engineer that true power lies
not in apocalyptic destruction, but in breathing the clean air of peace, humility, and holy fellowship.
==============================================================================================
// CHRISTIAN CODE STACK DEDICATION & SCRIPTURAL BENEDICTION:
// "The Spirit of God has made me, and the breath of the Almighty gives me life." — Job 33:4
// "He gives to all mankind life and breath and everything." — Acts 17:25
// This code stack operates under holy grace, charity, and unshakeable perseverance.
//
// Klingon / tlhIngan Hol Architectural Dedication:
// batlh 'ej rop wIqon, vumwI'pu' wIQaw'be'. (We author with honor and peace; we do not destroy.)
// Qapla'! (Success / Victory!)
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import random
from typing import Any, Dict, List, Optional, Set, Tuple


class GasType(Enum):
    SHITIUM = "shitium"
    KURCHATOV_QUANTIUM = "kurchatov_quantium"
    ADSKIDERIUM = "adskiderium"


class SpeciesType(Enum):
    HUMAN = "human"
    SHITMAN = "shitman"


@dataclass
class OrganState:
    name: str
    is_functional: bool = True
    mutated_behavior: Optional[str] = None
    generated_debris: Optional[str] = None


@dataclass
class ExposedMob:
    ckey: str
    name: str
    species: SpeciesType = SpeciesType.HUMAN
    sanity_level: float = 100.0
    eldritch_corruption_pct: float = 0.0
    organs: Dict[str, OrganState] = field(default_factory=lambda: {
        "heart": OrganState(name="heart"),
        "lungs": OrganState(name="lungs"),
        "liver": OrganState(name="liver"),
        "brain": OrganState(name="brain"),
    })
    chat_messages_received: List[str] = field(default_factory=list)


@dataclass
class ExposedTile:
    coord: Tuple[int, int, int]
    is_brown_sludge: bool = False
    has_goliath_tentacles: bool = False
    void_crack_open: bool = False
    gases_present: Dict[GasType, float] = field(default_factory=dict)


@dataclass
class ExposedItem:
    item_id: str
    name: str
    is_explosive_on_touch: bool = False
    is_radioactive: bool = False
    is_edible: bool = False
    is_fecal_sludge: bool = False


class AtmosExoticGasSubsystem:
    """Simulates generation, atmospheric kinetics, and interactive effects of the three new gases."""

    def __init__(self):
        self.quantum_emitter_active: bool = False
        self.quantum_emitter_frequency_ghz: float = 14.2
        self.reaction_logs: List[Dict[str, Any]] = []

    def synthesize_shitium(self, miasma_moles: float, temp_k: float) -> Tuple[float, str]:
        """Synthesizes Shitium (Tier-2 Miasma derivative via thermal catalytic reaction)."""
        if miasma_moles < 5.0 or temp_k < 350.0:
            return 0.0, "REACTION_CONDITIONS_NOT_MET"

        # Conversion yield: 0.85 moles of Shitium per mole of Miasma consumed
        shitium_produced = round(miasma_moles * 0.85, 2)
        log = {
            "gas": GasType.SHITIUM.value,
            "miasma_consumed": miasma_moles,
            "shitium_produced": shitium_produced,
            "sound": "splat.ogg",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.reaction_logs.append(log)
        return shitium_produced, "SHITIUM_SYNTHESIS_SUCCESS"

    def synthesize_kurchatov_quantium(
        self,
        anti_noblium_moles: float,
        hyper_noblium_moles: float,
        emitter_active: bool
    ) -> Tuple[float, str]:
        """Synthesizes Kurchatov-Quantium using Anti-Noblium and Quantum Emitter machine."""
        if not emitter_active:
            return 0.0, "QUANTUM_EMITTER_OFFLINE"
        if anti_noblium_moles < 2.0 or hyper_noblium_moles < 2.0:
            return 0.0, "INSUFFICIENT_PRECURSOR_GASES"

        # High-order quantum nuclear compression
        quantium_produced = round(min(anti_noblium_moles, hyper_noblium_moles) * 1.45, 2)
        log = {
            "gas": GasType.KURCHATOV_QUANTIUM.value,
            "quantium_produced": quantium_produced,
            "emitter_freq": self.quantum_emitter_frequency_ghz,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.reaction_logs.append(log)
        return quantium_produced, "KURCHATOV_QUANTIUM_SYNTHESIS_SUCCESS"

    def release_adskiderium_classified_event(self, canister_seal_broken: bool) -> Tuple[float, str]:
        """CentCom Classified Event release of eldritch horror gas Adskiderium."""
        if not canister_seal_broken:
            return 0.0, "CENTCOM_CLASSIFIED_CANISTER_SEALED"

        adskiderium_released = 50.0
        log = {
            "gas": GasType.ADSKIDERIUM.value,
            "moles_released": adskiderium_released,
            "alert": "CENTCOM_RED_CODE_HORROR_ACTIVE",
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        self.reaction_logs.append(log)
        return adskiderium_released, "ADSKIDERIUM_CENTCOM_OUTBREAK"

    def apply_shitium_exposure(self, mob: ExposedMob, tile: ExposedTile, item: ExposedItem) -> Dict[str, Any]:
        """Applies Shitium gas exposure: converts mob into Shitman, mutates tile, soils item."""
        # 1. Biological transformation to Shitman
        mob.species = SpeciesType.SHITMAN
        turn_message = "You're now a shitmen!"
        mob.chat_messages_received.append(turn_message)

        # 2. Tile conversion to brown sludge
        tile.is_brown_sludge = True
        tile.gases_present[GasType.SHITIUM] = tile.gases_present.get(GasType.SHITIUM, 0.0) + 10.0

        # 3. Item transformation
        item.is_fecal_sludge = True
        item.name = f"soiled {item.name}"

        return {
            "status": "SHITIUM_TRANSFORMATION_COMPLETE",
            "mob_species": mob.species.value,
            "notification": turn_message,
            "tile_sludge": tile.is_brown_sludge,
            "item_state": item.name,
            "audio": "splat.ogg"
        }

    def apply_kurchatov_quantium_mutation(
        self,
        mob: ExposedMob,
        tile: ExposedTile,
        item: ExposedItem,
        mutation_seed: int = 42
    ) -> Dict[str, Any]:
        """Applies quantum mutations to items (edible/explosive), tiles (Goliath tentacles), and organs."""
        rng = random.Random(mutation_seed)

        # 1. Item mutation: e.g. ballpoint pen becomes edible or explosive on touch
        mutation_choice = rng.choice(["edible", "explosive", "radioactive"])
        if mutation_choice == "edible":
            item.is_edible = True
        elif mutation_choice == "explosive":
            item.is_explosive_on_touch = True
        else:
            item.is_radioactive = True

        # 2. Tile mutation: acquires hazard traits / spawns Goliath tentacles pulling actors
        tile.has_goliath_tentacles = True

        # 3. Human organ mutation: lungs lose respiratory function and generate cobblestones
        lungs = mob.organs["lungs"]
        lungs.is_functional = False
        lungs.mutated_behavior = "generates internal cobblestones instead of processing O2"
        lungs.generated_debris = "cobblestones"

        return {
            "status": "QUANTUM_MUTATION_APPLIED",
            "item_mutation": mutation_choice,
            "tile_goliath_tentacles": tile.has_goliath_tentacles,
            "lungs_functional": lungs.is_functional,
            "lungs_anomaly": lungs.mutated_behavior
        }

    def apply_adskiderium_eldritch_corruption(self, mob: ExposedMob, tile: ExposedTile) -> Dict[str, Any]:
        """Applies eldritch psychological corruption, hallucinations, and reality tearing."""
        mob.sanity_level = max(0.0, mob.sanity_level - 65.0)
        mob.eldritch_corruption_pct = min(100.0, mob.eldritch_corruption_pct + 75.0)
        whisper = "The void between the bulkheads yearns to consume your name..."
        mob.chat_messages_received.append(whisper)

        tile.void_crack_open = True

        return {
            "status": "ELDRITCH_CORRUPTION_APPLIED",
            "sanity_level": mob.sanity_level,
            "corruption_pct": mob.eldritch_corruption_pct,
            "whisper": whisper,
            "void_crack": tile.void_crack_open
        }

    def export_map_integration_dmm(self) -> Dict[str, str]:
        """Exports station map DMM additions for Quantum Emitter and Exotic Gas Lab."""
        return {
            "IceBoxStation.dmm": (
                "// EXOTIC ATMOS LABORATORY & QUANTUM EMITTER @ (130, 95, 1)\n"
                "/obj/machinery/atmospherics/components/binary/quantum_emitter (130, 95, 1)\n"
                "/obj/machinery/atmospherics/pipe/simple/shitium_canister (131, 95, 1)\n"
                "/obj/structure/canister/classified/adskiderium (132, 95, 1)\n"
            ),
            "runtimestation.dmm": (
                "// RUNTIMESTATION ADVANCED ATMOS SUITE @ (110, 85, 2)\n"
                "/obj/machinery/atmospherics/components/binary/quantum_emitter (110, 85, 2)\n"
            )
        }

    def export_dreammaker_code(self) -> str:
        """Klingon: qonwI' De' export (DreamMaker .dm definitions for new gases and machines)."""
        return (
            "// ==========================================================================\n"
            "// SS13 ATMOSPHERIC GASES: SHITIUM, KURCHATOV-QUANTIUM, AND ADSKIDERIUM\n"
            "// Resolves #610 / Upstream #83\n"
            "// Fully Christian Code Stack & Blessed Atmospheric Kinetics\n"
            "// ==========================================================================\n\n"
            "/datum/gas/shitium\n"
            "\tid = \"shitium\"\n"
            "\tname = \"Shitium\"\n"
            "\tspecific_heat = 20\n"
            "\tflags = GAS_FLAG_DANGEROUS\n\n"
            "/datum/gas/kurchatov_quantium\n"
            "\tid = \"kurchatov_quantium\"\n"
            "\tname = \"Kurchatov-Quantium\"\n"
            "\tspecific_heat = 150\n"
            "\tflags = GAS_FLAG_DANGEROUS | GAS_FLAG_MUTAGENIC\n\n"
            "/datum/gas/adskiderium\n"
            "\tid = \"adskiderium\"\n"
            "\tname = \"Adskiderium\"\n"
            "\tspecific_heat = 500\n"
            "\tflags = GAS_FLAG_DANGEROUS | GAS_FLAG_ELDRITCH\n\n"
            "/obj/machinery/atmospherics/components/binary/quantum_emitter\n"
            "\tname = \"Quantum Emitter\"\n"
            "\tdesc = \"High-energy resonant emitter required to synthesize Kurchatov-Quantium.\"\n"
            "\ticon = 'icons/obj/machines/atmos.dmi'\n"
            "\ticon_state = \"quantum_emitter\"\n"
        )
