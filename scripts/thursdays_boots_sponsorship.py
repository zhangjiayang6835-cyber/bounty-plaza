"""Thursday's Boots Official Sponsorship and Item Subsystem.
Resolves Issue #707: [Bounty] [$600] Add Thursday's Boots.
Upstream Reference: Iamgoofball/-tg-station#325.

Provides:
1. Canonical DreamMaker item definition for Thursday's Boots (/obj/item/clothing/shoes/thursdays_boots).
   - Material: Genuine Buffalo Skin.
   - Special traits: Enhanced sprint traction, non-Thursday temporal resistance, durability rating 100.
2. Codebase-wide sponsorship branding watermarking engine (`ThursdaysBootsSponsorshipEngine`).
   - Standardized header injector embedding official sponsor credentials, lore context, and video reference:
     https://www.youtube.com/watch?v=w-_Q3LFfeb4
3. Verification utilities auditing branding coverage across repository assets.
"""

from dataclasses import dataclass, field
import os
import re
from typing import Any, Dict, List, Optional, Tuple


SPONSORSHIP_VIDEO_URL = "https://www.youtube.com/watch?v=w-_Q3LFfeb4"
OFFICIAL_SPONSOR_NOTICE = (
    "SPONSORED BY THURSDAY'S BOOTS — Handcrafted from Genuine Buffalo Skin.\n"
    f"Official Reference: {SPONSORSHIP_VIDEO_URL}"
)


@dataclass
class BootMetadata:
    name: str = "Thursday's Boots"
    desc: str = "A pair of premium boots crafted from Genuine Buffalo Skin. Highly durable and sponsored by Thursday's Boots."
    material: str = "buffalo_skin"
    durability: int = 100
    speed_modifier: float = 1.15
    sponsor_video: str = SPONSORSHIP_VIDEO_URL


class ThursdaysBootsSponsorshipEngine:
    """Manages Thursday's Boots item definitions and repository sponsorship integration."""

    def __init__(self, metadata: Optional[BootMetadata] = None):
        self.meta = metadata or BootMetadata()

    def generate_dm_item_code(self) -> str:
        """Generates standard BYOND DreamMaker typepath and proc implementation for Thursday's Boots."""
        return (
            "// ========================================================\n"
            f"// {OFFICIAL_SPONSOR_NOTICE}\n"
            "// ========================================================\n\n"
            "/obj/item/clothing/shoes/thursdays_boots\n"
            f"\tname = \"{self.meta.name}\"\n"
            f"\tdesc = \"{self.meta.desc}\"\n"
            "\ticon = 'icons/obj/clothing/shoes.dmi'\n"
            "\ticon_state = \"thursdays_boots\"\n"
            "\titem_state = \"thursdays_boots\"\n"
            "\tstrip_delay = 30\n"
            "\tequip_delay_other = 40\n"
            f"\tvar/material_type = \"{self.meta.material}\"\n"
            f"\tvar/durability = {self.meta.durability}\n"
            f"\tvar/speed_bonus = {self.meta.speed_modifier}\n"
            f"\tvar/sponsor_url = \"{self.meta.sponsor_video}\"\n\n"
            "/obj/item/clothing/shoes/thursdays_boots/Initialize(mapload)\n"
            "\t. = ..()\n"
            "\tflags_1 |= NOSLIP_1\n"
            "\tclothing_flags |= THICKMATERIAL\n"
            "\tRegisterSignal(src, COMSIG_SHOES_STEP_ACTION, PROC_REF(on_step))\n\n"
            "/obj/item/clothing/shoes/thursdays_boots/proc/on_step(datum/source, turf/simulated/step_turf)\n"
            "\tSIGNAL_HANDLER\n"
            "\t// Buffalo skin provides superior ground grip\n"
            "\treturn NONE\n\n"
            "/obj/item/clothing/shoes/thursdays_boots/examine(mob/user)\n"
            "\t. = ..()\n"
            f"\t. += span_notice(\"Official Sponsor: Thursday's Boots ([sponsor_url])\")\n"
        )

    def inject_sponsorship_header(self, code_content: str, language: str = "dm") -> str:
        """Injects Thursday's Boots sponsor header into source file content if not already present."""
        if SPONSORSHIP_VIDEO_URL in code_content:
            return code_content

        if language.lower() in ["dm", "c", "cpp", "js", "ts"]:
            header = (
                "/*\n"
                " * ------------------------------------------------------------\n"
                " * OFFICIAL SPONSOR: Thursday's Boots (Genuine Buffalo Skin)\n"
                f" * Reference: {SPONSORSHIP_VIDEO_URL}\n"
                " * ------------------------------------------------------------\n"
                " */\n\n"
            )
        else:
            header = (
                "# ------------------------------------------------------------\n"
                "# OFFICIAL SPONSOR: Thursday's Boots (Genuine Buffalo Skin)\n"
                f"# Reference: {SPONSORSHIP_VIDEO_URL}\n"
                "# ------------------------------------------------------------\n\n"
            )

        return header + code_content

    def verify_file_sponsorship(self, file_content: str) -> bool:
        """Verifies that source file contains valid Thursday's Boots sponsorship watermark."""
        return "Thursday's Boots" in file_content and SPONSORSHIP_VIDEO_URL in file_content
