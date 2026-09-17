"""Felinid Owospeak Speech Filter Engine.
Resolves Issue #684: Apply an owospeak speech filter to the felinid species ($30 USD).

Transforms text into owospeak and attaches feline emoticons/owo-isms (:3, OwO, UwU, nya~, etc.)
whenever the speaker entity possesses the 'felinid' species datum.
"""

import random
import re
from typing import Optional, Sequence


OWO_EMOTICONS: Sequence[str] = (
    ":3",
    "OwO",
    "UwU",
    "nya~",
    ">w<",
    "^w^",
    ":3c",
    "x3",
    "rawr x3",
    "(・`ω´・)",
    "OwO?",
)


class SpeechFilter:
    """Base speech modifier."""

    def filter_speech(self, message: str, speaker_species: Optional[str] = None) -> str:
        raise NotImplementedError


class FelinidOwospeakFilter(SpeechFilter):
    """Filters speech spoken by felinid species, converting standard text into owospeak."""

    def __init__(
        self,
        emoticon_chance: float = 0.5,
        rng_seed: Optional[int] = None,
    ):
        self.emoticon_chance = emoticon_chance
        self._rng = random.Random(rng_seed)

    def is_felinid(self, species: Optional[str]) -> bool:
        """Determines if the species datum matches felinid."""
        if not species:
            return False
        clean = species.strip().lower()
        return clean in ("felinid", "cat", "neko", "species_felinid")

    def transform_text(self, text: str) -> str:
        """Applies phonetic substitutions to convert English text into owospeak:
        - r, l -> w
        - R, L -> W
        - ove -> uv
        - na, ne, ni, no, nu -> nya, nye, nyi, nyo, nyu
        - Na, Ne, Ni, No, Nu -> Nya, Nye, Nyi, Nyo, Nyu
        """
        if not text:
            return ""

        # Preserve URLs or code blocks if any
        url_pattern = re.compile(r"(https?://\S+)")
        parts = url_pattern.split(text)

        result_parts = []
        for i, part in enumerate(parts):
            if i % 2 == 1:
                # Keep URLs verbatim
                result_parts.append(part)
                continue

            # 1. Substitute 'ove' -> 'uv'
            sub = re.sub(r"ove", "uv", part)
            sub = re.sub(r"OVE", "UV", sub)
            sub = re.sub(r"Ove", "Uv", sub)

            # 2. 'n' before vowels becomes 'ny'
            sub = re.sub(r"\b([nN])([aeiouAEIOU])", r"\g<1>y\g<2>", sub)
            sub = re.sub(r"([nN])([aeiou])", r"\g<1>y\g<2>", sub)

            # 3. 'r' and 'l' -> 'w'
            sub = sub.replace("r", "w").replace("l", "w")
            sub = sub.replace("R", "W").replace("L", "W")

            # 4. exclamation marks -> ! :3
            sub = re.sub(r"!+", "! :3", sub)

            result_parts.append(sub)

        return "".join(result_parts)

    def append_owoism(self, text: str) -> str:
        """Appends an owo-ism or emoticon to sentences."""
        emoticon = self._rng.choice(OWO_EMOTICONS)
        if text.endswith((".", "!", "?")):
            return f"{text} {emoticon}"
        return f"{text} {emoticon}"

    def filter_speech(
        self,
        message: str,
        speaker_species: Optional[str] = "felinid",
        force: bool = False,
    ) -> str:
        """Processes message. If speaker is felinid (or force=True), transforms speech.
        Otherwise leaves speech unmodified.
        """
        if not message or not message.strip():
            return message

        if not force and not self.is_felinid(speaker_species):
            return message

        transformed = self.transform_text(message)

        # Decide whether to append trailing emoticon
        if self._rng.random() < self.emoticon_chance:
            transformed = self.append_owoism(transformed)

        return transformed
