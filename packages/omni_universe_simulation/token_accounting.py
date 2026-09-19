"""Token consumption analysis, Shannon information entropy, and token density metrics."""

import math
import re
from typing import Dict
from .models import TokenMetrics


class TokenAccountingEngine:
    """Calculates token metrics, information theoretical entropy, and token density."""

    BPE_SPLIT_REGEX = re.compile(r"""'s|'t|'re|'ve|'m|'ll|'d| ?\w+| ?\d+| ?[^\s\w\d]+|\s+(?!\S)|\s+""")

    @classmethod
    def compute_shannon_entropy(cls, text: str) -> float:
        """Computes empirical Shannon information entropy in bits per character."""
        if not text:
            return 0.0
        frequency_table: Dict[str, int] = {}
        for char in text:
            frequency_table[char] = frequency_table.get(char, 0) + 1
        total_chars = float(len(text))
        entropy_sum = 0.0
        for count in frequency_table.values():
            prob = count / total_chars
            entropy_sum -= prob * math.log2(prob)
        return entropy_sum

    @classmethod
    def estimate_bpe_tokens(cls, text: str) -> int:
        """Estimates token count using deterministic regex subword pattern matching."""
        if not text:
            return 0
        matches = cls.BPE_SPLIT_REGEX.findall(text)
        token_count = 0
        for segment in matches:
            seg_len = len(segment.strip())
            if seg_len > 6:
                token_count += int(math.ceil(seg_len / 4.0))
            else:
                token_count += 1
        return max(token_count, 1)

    @classmethod
    def analyze_token_expenditure(cls, payload: str, minimum_token_threshold: int = 500) -> TokenMetrics:
        """Evaluates token intensity, byte density, and Shannon entropy for input payload."""
        char_count = len(payload)
        byte_data = payload.encode("utf-8")
        byte_count = len(byte_data)
        tokens = cls.estimate_bpe_tokens(payload)
        density = float(tokens) / float(max(byte_count, 1))
        entropy = cls.compute_shannon_entropy(payload)
        waste_index = float(tokens) * (entropy / 8.0)
        meets_sla = tokens >= minimum_token_threshold

        metrics = TokenMetrics(
            character_count=char_count,
            byte_count=byte_count,
            estimated_bpe_tokens=tokens,
            token_to_byte_density=density,
            shannon_entropy_bits=entropy,
            token_waste_index=waste_index,
            meets_token_intensive_sla=meets_sla,
        )
        return metrics
