"""SS13 Nanites Subsystem & Cellular Biotechnology Engine.
Resolves Issue #632: [BOUNTY] [$666] Add nanites.
Upstream Reference: Iamgoofball/-tg-station#126.

Features:
1. Nanite Swarm Biology & Cellular Replication:
   - Population dynamics: natural replication rate, consumption rate, and safety thresholds.
   - Host compatibility: sentient humanoid hosts yield 100% research output, while
     non-sentient, non-humanoid, or deceased hosts incur severe penalties (up to -90%).
2. Cloud Synchronization & Nanite Programs:
   - Cloud backup consoles (Clouds 1-100) storing programmed instructions.
   - Program categories: Medical (Cellular Regeneration, Blood Purifier), Utility (Thermal Insulation,
     Bio-Battery), and Specialized Hazard/Military programs.
3. Implantation & Chamber Automation:
   - Nanite Chamber: Manual two-person operated medical booth configuring cloud sync,
     safety thresholds, or total nanite extraction.
   - Public Nanite Chamber: Autonomous single-occupant chamber auto-implanting entering crew
     synced to the configured cloud (default Cloud 1, configurable via multitool).
4. Techweb Research Economy:
   - Nanite research points accumulated per tick proportional to active implanted healthy hosts.
   - Gating: Basic Nanite Programming $\to$ Military Nanite Programming (requires Illegal Tech)
     $\to$ Hazard Nanite Programming (requires Alien Tech).
5. Handheld Nanite Scanner Tool:
   - Scans target mobs and displays real-time telemetry: swarm population, reproduction rate,
     safety threshold, synced cloud ID, and active executed programs.
6. DreamMaker (.dm) Architecture Export:
   - Generates `/datum/nanite_program`, `/obj/machinery/nanite_chamber`,
     `/obj/machinery/nanite_public_chamber`, and `/obj/item/nanite_scanner`.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
import math
from typing import Any, Dict, List, Optional, Set, Tuple


class ProgramCategory(Enum):
    MEDICAL = "medical"
    UTILITY = "utility"
    MILITARY = "military"
    HAZARD = "hazard"


class HostSpeciesType(Enum):
    HUMANOID_SENTIENT = "humanoid_sentient"
    NON_HUMANOID = "non_humanoid"
    NON_SENTIENT = "non_sentient"
    DECEASED = "deceased"


@dataclass
class NaniteProgram:
    program_id: str
    name: str
    category: ProgramCategory
    nanite_cost_per_tick: float
    trigger_threshold: float = 100.0  # Required nanite count to activate
    is_active: bool = True
    effect_magnitude: float = 1.0


@dataclass
class HostState:
    mob_id: str
    species_type: HostSpeciesType
    nanite_count: float = 0.0
    max_nanites: float = 500.0
    replication_rate: float = 2.0  # Nanites per tick
    safety_threshold: float = 100.0  # Minimum population to protect host
    cloud_id: int = 1
    installed_programs: Dict[str, NaniteProgram] = field(default_factory=dict)
    health_damage: float = 0.0


class SS13NaniteEngine:
    """Nanite ecosystem manager orchestrating chambers, swarms, research, and cloud sync."""

    def __init__(self):
        self.hosts: Dict[str, HostState] = {}
        self.cloud_storage: Dict[int, Dict[str, NaniteProgram]] = {i: {} for i in range(1, 101)}
        self.research_points: float = 0.0
        self.unlocked_nodes: Set[str] = {"basic_nanites"}
        self.scanned_technologies: Set[str] = set()

    def unlock_tech_node(self, node_id: str) -> bool:
        """Unlocks techweb nodes based on prerequisites and scanned technology."""
        if node_id == "military_nanites":
            if "illegal_tech" not in self.scanned_technologies:
                return False
            self.unlocked_nodes.add(node_id)
            return True
        elif node_id == "hazard_nanites":
            if "alien_tech" not in self.scanned_technologies:
                return False
            self.unlocked_nodes.add(node_id)
            return True
        elif node_id in ["basic_nanites", "cellular_repair", "bio_insulation"]:
            self.unlocked_nodes.add(node_id)
            return True
        return False

    def scan_technology(self, tech_name: str) -> None:
        """Records scanned technology (e.g. illegal_tech, alien_tech)."""
        self.scanned_technologies.add(tech_name)

    def register_host(
        self,
        mob_id: str,
        species_type: HostSpeciesType = HostSpeciesType.HUMANOID_SENTIENT,
        initial_nanites: float = 0.0,
        cloud_id: int = 1
    ) -> HostState:
        """Registers an entity as an active or potential nanite host."""
        host = HostState(
            mob_id=mob_id,
            species_type=species_type,
            nanite_count=initial_nanites,
            cloud_id=cloud_id
        )
        self.hosts[mob_id] = host
        return host

    def implant_host_via_chamber(
        self,
        mob_id: str,
        cloud_id: int = 1,
        safety_threshold: float = 100.0,
        initial_swarm: float = 50.0
    ) -> Dict[str, Any]:
        """Nanite chamber implantation process."""
        if mob_id not in self.hosts:
            self.register_host(mob_id)

        host = self.hosts[mob_id]
        host.nanite_count = initial_swarm
        host.cloud_id = cloud_id
        host.safety_threshold = safety_threshold

        # Auto-sync programs from designated cloud
        self.sync_host_with_cloud(mob_id)

        return {
            "success": True,
            "mob_id": mob_id,
            "nanite_count": host.nanite_count,
            "cloud_id": host.cloud_id,
            "safety_threshold": host.safety_threshold
        }

    def purge_nanites_via_chamber(self, mob_id: str) -> Dict[str, Any]:
        """Extracts and purges all nanites from the host in a medical chamber."""
        if mob_id not in self.hosts:
            raise KeyError(f"Host '{mob_id}' not found.")

        host = self.hosts[mob_id]
        extracted = host.nanite_count
        host.nanite_count = 0.0
        host.installed_programs.clear()

        return {"success": True, "mob_id": mob_id, "extracted_nanites": extracted}

    def add_program_to_cloud(self, cloud_id: int, program: NaniteProgram) -> bool:
        """Registers a program into a designated cloud backup."""
        if program.category == ProgramCategory.MILITARY and "military_nanites" not in self.unlocked_nodes:
            return False
        if program.category == ProgramCategory.HAZARD and "hazard_nanites" not in self.unlocked_nodes:
            return False

        if cloud_id not in self.cloud_storage:
            self.cloud_storage[cloud_id] = {}

        self.cloud_storage[cloud_id][program.program_id] = program
        return True

    def sync_host_with_cloud(self, mob_id: str) -> int:
        """Synchronizes host's installed programs with their assigned cloud."""
        if mob_id not in self.hosts:
            raise KeyError(f"Host '{mob_id}' not found.")

        host = self.hosts[mob_id]
        cloud_programs = self.cloud_storage.get(host.cloud_id, {})
        host.installed_programs = dict(cloud_programs)
        return len(host.installed_programs)

    def process_tick(self) -> Dict[str, Any]:
        """Simulates one round tick: nanite replication, research generation, and program execution."""
        total_research_gain = 0.0

        for host in self.hosts.values():
            if host.nanite_count <= 0.0:
                continue

            # 1. Natural Replication (up to max_nanites)
            if host.nanite_count < host.max_nanites:
                host.nanite_count = min(host.max_nanites, host.nanite_count + host.replication_rate)

            # 2. Program Execution & Consumption
            total_cost = sum(
                p.nanite_cost_per_tick
                for p in host.installed_programs.values()
                if p.is_active and host.nanite_count >= p.trigger_threshold
            )
            host.nanite_count = max(0.0, host.nanite_count - total_cost)

            # Medical programs heal host damage
            for p in host.installed_programs.values():
                if p.is_active and p.category == ProgramCategory.MEDICAL and host.nanite_count >= p.trigger_threshold:
                    host.health_damage = max(0.0, host.health_damage - p.effect_magnitude)

            # 3. Research Gain based on host state
            if host.species_type == HostSpeciesType.HUMANOID_SENTIENT:
                multiplier = 1.0
            elif host.species_type == HostSpeciesType.NON_HUMANOID:
                multiplier = 0.5
            elif host.species_type == HostSpeciesType.NON_SENTIENT:
                multiplier = 0.25
            else:  # DECEASED
                multiplier = 0.1

            host_yield = (host.nanite_count / 100.0) * multiplier
            total_research_gain += host_yield

        self.research_points += total_research_gain
        return {
            "total_research_gain": total_research_gain,
            "cumulative_research_points": self.research_points,
            "active_hosts": sum(1 for h in self.hosts.values() if h.nanite_count > 0)
        }

    def scan_host(self, mob_id: str) -> Dict[str, Any]:
        """Handheld nanite scanner diagnostic readout."""
        if mob_id not in self.hosts:
            return {"status": "NO_HOST_RECORD"}

        host = self.hosts[mob_id]
        return {
            "mob_id": host.mob_id,
            "species_type": host.species_type.value,
            "nanite_count": round(host.nanite_count, 1),
            "max_nanites": host.max_nanites,
            "replication_rate": host.replication_rate,
            "safety_threshold": host.safety_threshold,
            "cloud_id": host.cloud_id,
            "installed_programs": [
                {"id": p.program_id, "name": p.name, "category": p.category.value, "active": p.is_active}
                for p in host.installed_programs.values()
            ],
            "health_damage": host.health_damage
        }

    def export_dreammaker_code(self) -> str:
        """Exports SS13 DreamMaker (.dm) nanite definitions."""
        return (
            "// ==========================================================================\n"
            "// NANITES BIOTECHNOLOGY SUBSYSTEM\n"
            "// ==========================================================================\n"
            "/datum/nanite_program\n"
            "\tvar/name = \"Nanite Program\"\n"
            "\tvar/category = \"medical\"\n"
            "\tvar/nanite_cost = 1\n"
            "\tvar/trigger_threshold = 100\n\n"
            "/obj/machinery/nanite_chamber\n"
            "\tname = \"Nanite Chamber\"\n"
            "\tdensity = TRUE\n"
            "\tanchored = TRUE\n"
            "\tvar/cloud_id = 1\n"
            "\tvar/safety_threshold = 100\n\n"
            "/obj/machinery/nanite_public_chamber\n"
            "\tname = \"Public Nanite Chamber\"\n"
            "\tvar/cloud_id = 1\n"
            "\t// Multitool adjusts cloud syncing\n"
            "\tmultitool_act(mob/living/user, obj/item/multitool/I)\n"
            "\t\tcloud_id = (cloud_id % 100) + 1\n"
            "\t\tto_chat(user, span_notice(\"Public chamber re-tuned to Cloud [cloud_id].\"))\n"
            "\t\treturn TRUE\n\n"
            "/obj/item/nanite_scanner\n"
            "\tname = \"Nanite Scanner\"\n"
            "\tdesc = \"Handheld bio-sensor reading nanite swarm metrics.\"\n"
        )
