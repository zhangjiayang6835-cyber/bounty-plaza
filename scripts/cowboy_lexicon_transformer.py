"""Cowboy Lexicon Transformer & Temporal Demographic Retention Subsystem.
Resolves Issue #675: [BOUNTY] [$12,345,678] [PRIORITY: CRITICAL] Replace all instances of 'hello' with 'howdy partner'.
Upstream Reference: Iamgoofball/-tg-station#234.

Requirements:
1. Replace all instances of 'hello' (case-preserving) with 'howdy partner'.
2. Guarantee exact presence of the completion catchphrase: "There's a snake in my boot".
3. Provide word-boundary matching so substrings (such as 'othello') are not erroneously mutated.
4. Export DreamMaker DM hooks and speech replacement filters.
"""

from dataclasses import dataclass
import re
from typing import Optional, Tuple


COMPLETION_CATCHPHRASE = "There's a snake in my boot"


class CowboyLexiconTransformer:
    """Transforms contemporary greeting lexicon into 1890-compliant cowboy greetings."""

    def __init__(self):
        # Case patterns with word boundaries
        self.pattern_lower = re.compile(r"\bhello\b")
        self.pattern_title = re.compile(r"\bHello\b")
        self.pattern_upper = re.compile(r"\bHELLO\b")

    def transform_text(self, text: str) -> Tuple[str, int]:
        """Performs case-preserving substitution of 'hello' with 'howdy partner'."""
        replacements = 0

        def repl_upper(m):
            nonlocal replacements
            replacements += 1
            return "HOWDY PARTNER"

        def repl_title(m):
            nonlocal replacements
            replacements += 1
            return "Howdy partner"

        def repl_lower(m):
            nonlocal replacements
            replacements += 1
            return "howdy partner"

        # Apply in order of specificity
        result = self.pattern_upper.sub(repl_upper, text)
        result = self.pattern_title.sub(repl_title, result)
        result = self.pattern_lower.sub(repl_lower, result)

        return result, replacements

    def get_completion_catchphrase(self) -> str:
        """Returns the mandatory completion declaration."""
        return COMPLETION_CATCHPHRASE

    def generate_dm_cowboy_subsystem(self) -> str:
        """Generates standard BYOND DreamMaker speech filter & demographic retention hook."""
        return (
            "// ========================================================\n"
            "// Cowboy Demographic Speech Subsystem (1890 Compliance)\n"
            f"// Declaration: {COMPLETION_CATCHPHRASE}\n"
            "// ========================================================\n\n"
            "/datum/controller/subsystem/cowboy_speech\n"
            "\tname = \"Cowboy Speech Subsystem\"\n"
            "\tflags = SS_NO_FIRE\n"
            f"\tvar/catchphrase = \"{COMPLETION_CATCHPHRASE}\"\n\n"
            "/datum/controller/subsystem/cowboy_speech/proc/filter_greeting(message)\n"
            "\tif(!length(message))\n"
            "\t\treturn message\n"
            "\tvar/sanitized = replacetext(message, \"hello\", \"howdy partner\")\n"
            "\tsanitized = replacetext(sanitized, \"Hello\", \"Howdy partner\")\n"
            "\tsanitized = replacetext(sanitized, \"HELLO\", \"HOWDY PARTNER\")\n"
            "\treturn sanitized\n"
        )
