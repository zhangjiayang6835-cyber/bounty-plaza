"""Token budget estimation, entropy analysis, and context compaction."""

import math
from collections import Counter
from typing import List, Tuple
from .models import FileMetadata, TokenBudget, CompactedContext


class TokenBudgetManager:
    """Manages LLM context window token quotas, entropy scoring, and compaction."""

    def __init__(self, budget: TokenBudget | None = None) -> None:
        """Initialize token budget manager with optional budget configuration."""
        self.budget: TokenBudget = budget if budget is not None else TokenBudget()

    @staticmethod
    def estimate_tokens(text: str) -> int:
        """Estimate token count for text using character and syntax heuristics.

        :param text: Input string to measure.
        :return: Estimated token integer count.
        """
        if not text:
            return 0
        char_count = len(text)
        punctuation_count = sum(1 for c in text if c in "{}[]();:,.<>/?!~@#$%^&*+-=")
        spaces = text.count(" ") + text.count("\n")
        estimated = (char_count / 4.0) + (punctuation_count * 0.25) + (spaces * 0.1)
        return max(1, math.ceil(estimated))

    @staticmethod
    def calculate_entropy(data: bytes | str) -> float:
        """Calculate Shannon entropy of byte or string content.

        :param data: Input data to evaluate.
        :return: Shannon entropy in bits per character/byte.
        """
        if not data:
            return 0.0
        raw_bytes = data.encode("utf-8") if isinstance(data, str) else data
        if not raw_bytes:
            return 0.0
        length = len(raw_bytes)
        frequencies = Counter(raw_bytes)
        entropy = 0.0
        for count in frequencies.values():
            prob = count / length
            entropy -= prob * math.log2(prob)
        return round(entropy, 4)

    def compact(
        self,
        files: List[FileMetadata],
        priority_paths: List[str] | None = None
    ) -> CompactedContext:
        """Compact file list to strictly fit within available context window.

        :param files: List of candidate FileMetadata objects.
        :param priority_paths: Optional list of file path prefixes to prioritize.
        :return: CompactedContext with included and omitted files.
        """
        limit = self.budget.available_context
        prioritized: List[str] = list(priority_paths) if priority_paths else []

        def sort_key(item: FileMetadata) -> Tuple[int, float, int]:
            is_priority = 1 if any(item.path.startswith(p) for p in prioritized) else 0
            return (is_priority, item.entropy, -item.token_estimate)

        sorted_files = sorted(files, key=sort_key, reverse=True)

        included: List[str] = []
        omitted: List[str] = []
        accumulated_tokens = 0

        for file_meta in sorted_files:
            if file_meta.is_empty:
                continue
            if accumulated_tokens + file_meta.token_estimate <= limit:
                included.append(file_meta.path)
                accumulated_tokens += file_meta.token_estimate
            else:
                omitted.append(file_meta.path)

        total_candidate_tokens = sum(f.token_estimate for f in files if not f.is_empty)
        ratio = (
            round(accumulated_tokens / total_candidate_tokens, 4)
            if total_candidate_tokens > 0
            else 1.0
        )

        manifest = (
            f"Compacted Context: {len(included)} included, {len(omitted)} omitted, "
            f"{accumulated_tokens}/{limit} tokens used"
        )

        return CompactedContext(
            included_files=included,
            omitted_files=omitted,
            total_tokens=accumulated_tokens,
            budget_limit=limit,
            compaction_ratio=ratio,
            manifest_summary=manifest,
        )
