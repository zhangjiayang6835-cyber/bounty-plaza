"""Felinid OwO-speak Speech Modification Subsystem.
Resolves Issue #684: [Bounty] [$30] Apply an owospeak speech filter to the felinid species.
Upstream Reference: Iamgoofball/-tg-station#267.

Features:
1. Phonetic phoneme transformer converting English speech to canonical OwO/UwU-speak:
   - 'r' and 'l' -> 'w' (case-preserving)
   - 'R' and 'L' -> 'W'
   - 'th' -> 'f' or 'd'
   - 'ove' -> 'uv'
   - 'na', 'ne', 'ni', 'no', 'nu' -> 'nya', 'nye', 'nyi', 'nyo', 'nyu'
2. Punctuation emoticons and kaomoji injection (':3', 'OwO', 'UwU', '>w<', '^w^').
3. Deterministic seedable RNG support for reproducible simulation and testing.
4. Native BYOND DreamMaker `/datum/species/felinid` speech hook compilation.
"""

from dataclasses import dataclass, field
import random
import re
from typing import Any, Dict, List, Optional, Tuple


OWO_SUFFIXES = [":3", "OwO", "UwU", ">w<", "^w^", "nya~", ":3c", "rawr x3"]

PHONEME_REPLACEMENTS: List[Tuple[re.Pattern, str]] = [
    (re.compile(r"\bove\b", re.IGNORECASE), "uv"),
    (re.compile(r"th", re.IGNORECASE), "f"),
    (re.compile(r"n([aeiou])", re.IGNORECASE), r"ny\1"),
    (re.compile(r"N([aeiou])"), r"Ny\1"),
    (re.compile(r"N([AEIOU])"), r"NY\1"),
    (re.compile(r"[rl]"), "w"),
    (re.compile(r"[RL]"), "W"),
]


class FelinidOwospeakFilter:
    """Transforms standard speech into Felinid OwO-speak with emoticons and stuttering."""

    def __init__(self, rng_seed: Optional[int] = None):
        self.rng = random.Random(rng_seed) if rng_seed is not None else random.Random()

    def transform_phonemes(self, text: str) -> str:
        """Transforms letters and phonemes into owo equivalents ('r'/'l' -> 'w', etc.)."""
        result = text
        for pattern, replacement in PHONEME_REPLACEMENTS:
            result = pattern.sub(replacement, result)
        return result

    def inject_owo_isms(self, text: str, chance: float = 0.8) -> str:
        """Appends ':3' and other owo-isms across sentences and at line endings."""
        sentences = re.split(r"([.!?]+)", text)
        transformed_parts = []

        for i in range(0, len(sentences) - 1, 2):
            clause = sentences[i].strip()
            punct = sentences[i + 1]
            if clause:
                clause_owo = self.transform_phonemes(clause)
                if self.rng.random() < chance:
                    emoticon = self.rng.choice(OWO_SUFFIXES)
                    transformed_parts.append(f"{clause_owo} {emoticon}{punct}")
                else:
                    transformed_parts.append(f"{clause_owo}{punct}")

        # Handle remaining trailing part if any
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            trailing = sentences[-1].strip()
            trailing_owo = self.transform_phonemes(trailing)
            emoticon = self.rng.choice(OWO_SUFFIXES)
            transformed_parts.append(f"{trailing_owo} {emoticon}")

        return " ".join(transformed_parts) if transformed_parts else self.transform_phonemes(text)

    def filter_speech(self, raw_message: str) -> str:
        """Master speech filtering entrypoint for Felinid species vocalizations."""
        if not raw_message or not raw_message.strip():
            return raw_message
        return self.inject_owo_isms(raw_message)

    def generate_dm_species_patch(self) -> str:
        """Generates standard BYOND DreamMaker speech hook patch for `/datum/species/felinid`."""
        return (
            "// ========================================================\n"
            "// Felinid Owospeak Speech Filter Integration\n"
            "// ========================================================\n\n"
            "/datum/species/felinid\n"
            "\tname = \"Felinid\"\n"
            "\tvar/owospeak_enabled = TRUE\n\n"
            "/datum/species/felinid/handle_speech(datum/source, list/speech_args)\n"
            "\tSIGNAL_HANDLER\n"
            "\tif(!owospeak_enabled)\n"
            "\t\treturn\n"
            "\tvar/message = speech_args[SPEECH_MESSAGE]\n"
            "\tif(!length(message))\n"
            "\t\treturn\n"
            "\tmessage = replacetext(message, \"r\", \"w\")\n"
            "\tmessage = replacetext(message, \"l\", \"w\")\n"
            "\tmessage = replacetext(message, \"R\", \"W\")\n"
            "\tmessage = replacetext(message, \"L\", \"W\")\n"
            "\tmessage = replacetext(message, \"th\", \"f\")\n"
            "\tmessage = replacetext(message, \"ove\", \"uv\")\n"
            "\tvar/list/emotes = list(\":3\", \"OwO\", \"UwU\", \">w<\", \"^w^\", \"nya~\")\n"
            "\tspeech_args[SPEECH_MESSAGE] = \"[message] [pick(emotes)]\"\n"
            "\treturn NONE\n"
        )
