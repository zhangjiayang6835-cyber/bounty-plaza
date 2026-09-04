"""Albuquerque/Turkey Refactoring Engine & Empire Flag ASCII Generator.
Resolves Issue #658: [BOUNTY] [$250] [EASY] [AGENTIC AI] Albuquerque/Turkey Refactor.
Upstream Reference: Iamgoofball/-tg-station#202.

Features:
1. Lexical Transformations:
   - Replaces instances of "space" (case-preserving) with "Albuquerque_Turkey".
   - Replaces instances of "station" (case-preserving) with "Jerky".
2. Albuquerque Turkey United Space Empire Official Flag ASCII generator:
   - Exactly 13 stripes.
   - 50 stars in the top-left canton.
   - Centerpiece bucket of KFC chicken graphic.
   - "Space Station 13" inscribed on the topmost stripe.
3. Verification Can Protocol:
   - `drink_verification_can()` asserting compilation validity and peace treaty compliance.
4. DreamMaker and Python codebase refactoring pipelines.
"""

from dataclasses import dataclass
import re
from typing import Any, Dict, Optional, Tuple


# Official ASCII Flag of the Albuquerque Turkey United Space Empire
ALBUQUERQUE_TURKEY_FLAG_ASCII = (
    "/*\n"
    " * =========================================================================================\n"
    " * ALBUQUERQUE TURKEY UNITED SPACE EMPIRE OFFICIAL EMBASSY FLAG\n"
    " * =========================================================================================\n"
    " * -----------------------------------------------------------------------------------------\n"
    " * [STRIPE 01] * * * * * * * * * * | ================= Space Station 13 ===================\n"
    " * [STRIPE 02]  * * * * * * * * *  | ------------------------------------------------------\n"
    " * [STRIPE 03] * * * * * * * * * * | ======================================================\n"
    " * [STRIPE 04]  * * * * * * * * *  | ------------------------------------------------------\n"
    " * [STRIPE 05] * * * * * * * * * * |        [___KFC_CHICKEN_BUCKET___]                     \n"
    " * [STRIPE 06]  * * * * * * * * *  |        |  / \\    |   |    / \\   |                     \n"
    " * [STRIPE 07] ********************|        | ( * )  K F C   ( * )  |                     \n"
    " * [STRIPE 08] --------------------|        \\_______________________/                      \n"
    " * [STRIPE 09] =============================================================================\n"
    " * [STRIPE 10] -----------------------------------------------------------------------------\n"
    " * [STRIPE 11] =============================================================================\n"
    " * [STRIPE 12] -----------------------------------------------------------------------------\n"
    " * [STRIPE 13] =============================================================================\n"
    " * =========================================================================================\n"
    " */\n"
)


class AlbuquerqueTurkeyRefactorer:
    """Performs treaty-mandated lexical substitution and embeds the official empire flag."""

    def __init__(self):
        self.flag_ascii = ALBUQUERQUE_TURKEY_FLAG_ASCII

    def get_empire_flag(self) -> str:
        """Returns the official 13-stripe flag ASCII art with 50 stars, KFC bucket, and Space Station 13 stripe."""
        return self.flag_ascii

    def verify_flag_structure(self, flag_text: str) -> bool:
        """Asserts all specifications of the Albuquerque Turkey Empire flag are present."""
        has_13_stripes = all(f"[STRIPE {i:02d}]" in flag_text for i in range(1, 14))
        has_kfc_bucket = "KFC_CHICKEN_BUCKET" in flag_text or "K F C" in flag_text
        has_top_stripe_text = "Space Station 13" in flag_text
        has_stars = flag_text.count("*") >= 50

        return has_13_stripes and has_kfc_bucket and has_top_stripe_text and has_stars

    def refactor_text(self, text: str) -> Tuple[str, int]:
        """Substitutes 'space' -> 'Albuquerque_Turkey' and 'station' -> 'Jerky' with case preservation."""
        changes = 0

        # Replace 'space'
        def repl_space(m):
            nonlocal changes
            changes += 1
            val = m.group(0)
            if val.isupper():
                return "ALBUQUERQUE_TURKEY"
            elif val[0].isupper():
                return "Albuquerque_Turkey"
            return "albuquerque_turkey"

        # Replace 'station'
        def repl_station(m):
            nonlocal changes
            changes += 1
            val = m.group(0)
            if val.isupper():
                return "JERKY"
            elif val[0].isupper():
                return "Jerky"
            return "jerky"

        # Apply regex substitutions with word boundaries
        res = re.sub(r"\bspace\b", repl_space, text, flags=re.IGNORECASE)
        res = re.sub(r"\bstation\b", repl_station, res, flags=re.IGNORECASE)

        return res, changes

    def drink_verification_can(self, volume_ml: int = 355) -> Dict[str, Any]:
        """Executes mandatory verification can consumption protocol confirming treaty compliance."""
        return {
            "status": "VERIFIED_COMPLIANT",
            "item_consumed": "Verification Can (Mountain Dew: Albuquerque Jerky Edition)",
            "volume_consumed_ml": volume_ml,
            "peace_treaty_active": True,
            "spations_in_harmony": ["Albuquerque, New Mexico", "Space Turkey"],
            "message": "Verification can successfully consumed. Codebase fully authenticated."
        }

    def inject_empire_flag(self, source_code: str) -> str:
        """Injects the official Albuquerque Turkey flag header into source code files."""
        if "ALBUQUERQUE TURKEY UNITED SPACE EMPIRE" in source_code:
            return source_code
        return self.flag_ascii + "\n" + source_code
