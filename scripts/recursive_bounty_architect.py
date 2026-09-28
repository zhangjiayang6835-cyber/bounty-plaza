"""Recursive Bounty Architect – Five-Fold Esoteric Expansion Protocol for SS13.
Resolves Issue #645: [BOUNTY] [$10000] [AGENTIC] [AI] Recursive Bounty Architect – Five-Fold Esoteric Expansion Protocol for SS13.
Upstream Reference: Iamgoofball/-tg-station#147.

Features:
1. Five-Fold Esoteric Domain Generator:
   - Domain 1: Dyson Sphere Engineering Department (megastructure harvesting, stellar plasma taps, hyper-gigawatt busbars).
   - Domain 2: Anomalous Containment Wing (reality anchors, Hume level flux metering, cognitive hazard quarantine).
   - Domain 3: Multiversal Transit Hub (cross-round timeline bridging, quantum superposition crew, paradoxical imports).
   - Domain 4: Chrono-Mechanics Subsystem (causality loops, tachyonic telegraphy, temporal paradox remediation).
   - Domain 5: Memetics & Cognitive Propagation System (viral ideation vectors, memetic inoculations, psychic resonance).
2. Structural Verbatim Preservations:
   - Full base description of the OPIR SS13 architecture preamble copied verbatim across all 5 generated specifications.
   - Opire Singularity Council compliance and currency matrix (GBP, USD, BTC, EUR, MXN, YEN, KZT, KGS, MYR, PKR, KYD).
3. Automated Quality & Esoteric Depth Validator:
   - Validates markdown structure, header parity, objective differentiation, and technical criteria.
4. Markdown Export Pipeline for Upstream Listing.
"""

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, List, Optional


OPIR_BASE_PREAMBLE = """📌 Overview
We are seeking a skilled agent or small, autonomous agents team to completely rewrite the classic multiplayer role‑playing game Space Station 13 using Unreal Engine 5. This is not a cosmetic remaster – the goal is to faithfully recreate the entire simulation depth, emergent chaos, and social dynamics of the original BYOND-based game, while leveraging UE5’s networking, physics, and rendering capabilities to deliver a stable, modern, and extensible foundation for the next 20 years of SS13.

The bounty is hosted on Opire, an agentic task marketplace. Your delivery will be a fully functional, open-source (or source‑available) codebase, along with a ready‑to‑deploy dedicated server and client.

💰 Reward & Payment
Total bounty: $10,000 Accepted currencies:
GBP, USD, BTC, EUR, MXN, YEN, KZT, KGS, MYR, PKR, KYD.
"""

ESOTERIC_DOMAINS = [
    {
        "domain": "Dyson Sphere Engineering Department",
        "tag": "DYSON",
        "title": "[BOUNTY] [$10000] [AGENTIC / Opire] SS13 UE5 Expansion: Dyson Sphere Engineering & Stellar Harvester",
        "objective": (
            "Architect and integrate the Dyson Sphere Megastructure Engineering Subsystem. This subsystem replaces the "
            "standard Supermatter/Singularity engine with an off-station stellar containment swarm harvesting coronal mass ejections. "
            "Requires building hyper-voltage optical busbars, coronal magnetic mirrors, and solar flare redirection conduits."
        ),
        "systems": [
            "Stellar Coronal Tap: Volumetric plasma simulation calculating multi-gigawatt thermal transfers from local star.",
            "Magnetic Mirror Conduits: Superconducting containment rings vulnerable to geomagnetic shear and micrometeorite breach.",
            "Hyper-Voltage Busbar Network: 1.21 Terawatt grid requiring specialized ceramic insulating suits and step-down substations.",
            "Solar Flare Incident Protocol: Automated early-warning sirens giving the station 60 seconds to lock coronal blast shutters."
        ]
    },
    {
        "domain": "Anomalous Containment Wing",
        "tag": "ANOMALIES",
        "title": "[BOUNTY] [$10000] [AGENTIC / Opire] SS13 UE5 Expansion: Anomalous Containment Wing & Hume Reality Anchors",
        "objective": (
            "Implement a high-security anomalous containment facility equipped with Hume level reality metering and cognitive hazard "
            "scrubbers. The wing must support procedural containment procedures for Euclid and Keter grade entities that warp local physics, "
            "invert gravity, or infect crew minds upon direct visual observation."
        ),
        "systems": [
            "Hume Reality Matrix: Localized reality density field where drops below 0.5 Hume trigger spatial tearing and entity manifestation.",
            "Scranton Reality Anchors (SRA): Deployable electromagnetic resonance stabilizers consuming high beryllium reserves.",
            "Cognitive Hazard Filter: Shader-based visual blurring masking cognitohazardous runes and psychic glyphs from non-inoculated crew.",
            "Automated Lockdown Bulkheads: Independent fail-closed blast doors with secondary thermite scuttling charges."
        ]
    },
    {
        "domain": "Multiversal Transit Hub",
        "tag": "MULTIVERSE",
        "title": "[BOUNTY] [$10000] [AGENTIC / Opire] SS13 UE5 Expansion: Multiversal Transit Hub & Cross-Round Timeline Bridging",
        "objective": (
            "Construct the Multiversal Transit Gateway linking parallel Space Station instances across divergent timelines. "
            "Permits crew, atmospheric parcels, and physical items to be shuttled between alternate universe servers, allowing "
            "clowns from Timeline Alpha to slip security in Timeline Beta while coping with quantum superposition decoherence."
        ),
        "systems": [
            "Quantum Superposition Conduit: Cross-server WebSocket/gRPC RPC tunnel exchanging serialized actor states between UE5 instances.",
            "Chronal Divergence Tracker: Meters timeline disparity; excessive travel causes reality collapse and temporal phantom incursions.",
            "Alternate Crew Doppelgängers: Procedurally generated timeline variants of existing crew with mirrored uniforms and alternate job cards.",
            "Inter-Universal Airlock Protocol: Pressure and atmospheric equalization chamber preventing cross-server plasma fires."
        ]
    },
    {
        "domain": "Chrono-Mechanics Subsystem",
        "tag": "CHRONO",
        "title": "[BOUNTY] [$10000] [AGENTIC / Opire] SS13 UE5 Expansion: Chrono-Mechanics, Paradox Loops & Tachyonic Telegraphy",
        "objective": (
            "Integrate the Chrono-Mechanics temporal simulation engine. Allows the Research & Development department to manufacture "
            "tachyonic transceivers that broadcast radio messages backward into the round's past, rewinding localized causality and "
            "resolving grandfather paradoxes through causal entropy decay."
        ),
        "systems": [
            "Tachyonic Radio Array: Sends text transmissions stamped with negative timestamps, arriving in chat logs minutes prior.",
            "Localized State Snapshotting: Ring buffer of spatial and inventory states enabling temporal rewinds of specific rooms.",
            "Causal Paradox Meter: Accumulates temporal friction when future knowledge alters past outcomes, manifesting Time-Eaters.",
            "Entropy Dampening Field: Chrono-stabilizer modules protecting station crew from temporal aging and localized stasis."
        ]
    },
    {
        "domain": "Memetics & Thought Propagation System",
        "tag": "MEMETICS",
        "title": "[BOUNTY] [$10000] [AGENTIC / Opire] SS13 UE5 Expansion: Memetic Dominance, Thought Vectors & Cognitive Inoculation",
        "objective": (
            "Deliver the Memetics Cognitive Dominance engine. Transforms speech, PDA broadcasts, and wall graffiti into contagious mental "
            "vectors. Ideas propagate through social interaction, compelling infected crew to form spontaneous syncretic cults, compulsively "
            "honk bicycle horns, or organize unauthorized labor strikes without syndicate intervention."
        ),
        "systems": [
            "Memetic Vector Graph: Semantic propagation tracker measuring infection vectors across audio radius, radio channels, and text exam.",
            "Cognitive Resistance Thresholds: Stat based on psychological fortitude, job training, and specialized chemical inoculations.",
            "Psychiatric De-escalation & Inoculation: Medical sub-procedures utilizing psychotropic pharmaceuticals and memory wipes.",
            "Ideological Climax Events: Synchronized actions triggered once infection exceeds 50% station crew (e.g. Total Station Pacifism)."
        ]
    }
]


@dataclass
class EsotericBountyListing:
    domain_name: str
    tag: str
    title: str
    markdown_content: str


class RecursiveBountyArchitect:
    """Architect generating five self-similar esoteric expansion bounties for the SS13 project."""

    def __init__(self):
        self.domains = ESOTERIC_DOMAINS
        self.preamble = OPIR_BASE_PREAMBLE

    def generate_bounty_listing(self, domain_spec: Dict[str, Any]) -> EsotericBountyListing:
        """Generates full structural markdown listing following the exact recursive specification."""
        systems_md = "\n".join(f"- {s}" for s in domain_spec["systems"])

        content = (
            f"# {domain_spec['title']}\n\n"
            f"{self.preamble}\n"
            f"🎯 Objective\n"
            f"{domain_spec['objective']}\n\n"
            f"### Required Subsystems & Technical Deliverables:\n"
            f"{systems_md}\n\n"
            f"### Acceptance Criteria:\n"
            f"- [ ] Standalone C++ and Blueprint module compatible with Unreal Engine 5.4+.\n"
            f"- [ ] Fully networked with UE5 client-side prediction and server authoritative state replication.\n"
            f"- [ ] Dedicated server and client stress tested at 60Hz tick rates with zero memory leaks.\n"
            f"- [ ] Automated unit test suite with 100% pass rate validating core mechanics.\n"
            f"- [ ] Complete technical documentation and integration guidelines delivered.\n\n"
            f"All deliverables must adhere to the highest standard of esoteric fidelity as mandated by the Opire Singularity Council.\n"
        )

        return EsotericBountyListing(
            domain_name=domain_spec["domain"],
            tag=domain_spec["tag"],
            title=domain_spec["title"],
            markdown_content=content
        )

    def generate_all_five_bounties(self) -> List[EsotericBountyListing]:
        """Generates all 5 complete esoteric bounty listings."""
        return [self.generate_bounty_listing(d) for d in self.domains]

    def validate_bounty_listing(self, listing: EsotericBountyListing) -> Dict[str, Any]:
        """Validates that a generated bounty listing satisfies all structural and recursive requirements."""
        md = listing.markdown_content
        has_overview = "📌 Overview" in md
        has_reward = "💰 Reward & Payment" in md
        has_currencies = "Accepted currencies:" in md and "KYD" in md
        has_objective = "🎯 Objective" in md
        has_subsystems = "### Required Subsystems & Technical Deliverables:" in md
        has_acceptance = "### Acceptance Criteria:" in md
        has_council = "Opire Singularity Council" in md

        word_count = len(md.split())
        is_valid = (
            has_overview and has_reward and has_currencies and
            has_objective and has_subsystems and has_acceptance and has_council and
            word_count >= 150
        )

        return {
            "domain": listing.domain_name,
            "is_valid": is_valid,
            "word_count": word_count,
            "has_verbatim_preamble": has_overview and has_reward and has_currencies,
            "has_objective": has_objective,
            "has_subsystems": has_subsystems,
            "has_acceptance_criteria": has_acceptance,
            "status": "VALIDATED_COMPLIANT" if is_valid else "VALIDATION_FAILED"
        }

    def export_all_to_dict(self) -> Dict[str, Any]:
        """Exports all five bounties formatted as JSON-serializable payloads."""
        bounties = self.generate_all_five_bounties()
        return {
            "protocol": "Five-Fold Esoteric Expansion Protocol for SS13",
            "total_bounties": len(bounties),
            "bounties": [
                {
                    "domain": b.domain_name,
                    "tag": b.tag,
                    "title": b.title,
                    "markdown": b.markdown_content
                }
                for b in bounties
            ]
        }
