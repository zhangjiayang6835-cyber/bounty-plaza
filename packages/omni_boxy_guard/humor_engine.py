"""
Humor detection and policy enforcement engine for pull requests.
"""

import re
from typing import Tuple
from packages.omni_boxy_guard.models import (
    DiffAnalysisResult,
    HumorClassification,
    HumorReviewResult,
    PRAction,
    PullRequest,
)


class HumorAnalysisEngine:
    """Analyzes pull request diffs and descriptions for humor addition or removal."""

    HUMOR_LEXICON = [
        "joke", "pun", "puns", "haha", "hehe", "lol", "lmao", "rofl",
        "giggle", "snicker", "chuckle", "humor", "humour", "funny",
        "comedic", "hilarious", "wit", "witty", "easter egg", "rickroll",
        "skill issue", "rubber duck", "dad joke", "knock knock",
        "why did the", "spaghetti code", "facepalm", "leeroy",
        "all your base", "works on my machine", "feature not a bug",
        "famous last words", "more cowbell", "comic relief",
        "cat knocked down", "banana for scale", "potato", "clown",
    ]

    REMOVE_HUMOR_PHRASES = [
        "remove humor", "remove jokes", "delete pun", "delete puns",
        "remove puns", "clean up jokes", "strip humor", "remove comedic",
        "sanitize funny", "remove easter egg", "no jokes allowed",
        "remove sarcasm", "remove meme", "remove memes", "stop clowning",
        "humor removal", "remove all jokes", "eliminate humor",
    ]

    ADD_HUMOR_PHRASES = [
        "add humor", "add joke", "add jokes", "add pun", "add puns",
        "add funny", "sprinkle humor", "make it funny", "comic relief",
        "add memes", "add meme", "humor injection", "more humor",
        "inject jokes", "funny easter egg",
    ]

    def __init__(self) -> None:
        """Initialize HumorAnalysisEngine with precompiled regex patterns."""
        lexicon_pattern = r"\b(" + "|".join(re.escape(term) for term in self.HUMOR_LEXICON) + r")\b"
        self._lexicon_re = re.compile(lexicon_pattern, re.IGNORECASE)

        remove_pattern = r"(" + "|".join(re.escape(phrase) for phrase in self.REMOVE_HUMOR_PHRASES) + r")"
        self._remove_re = re.compile(remove_pattern, re.IGNORECASE)

        add_pattern = r"(" + "|".join(re.escape(phrase) for phrase in self.ADD_HUMOR_PHRASES) + r")"
        self._add_re = re.compile(add_pattern, re.IGNORECASE)

    def extract_markers(self, text: str) -> list[str]:
        """Find all recognized humor markers in a string.

        Args:
            text: Arbitrary source code or comment string.

        Returns:
            List of matching humor tokens found.
        """
        if not text:
            return []
        matches = self._lexicon_re.findall(text)
        return [match.lower() for match in matches]

    def detect_intent(self, text: str) -> Tuple[bool, bool]:
        """Detect explicit humor modification intent in commit titles or descriptions.

        Args:
            text: Text to search for explicit intent phrases.

        Returns:
            Tuple of (attempts_remove_humor, attempts_add_humor).
        """
        if not text:
            return False, False
        attempts_remove = bool(self._remove_re.search(text))
        attempts_add = bool(self._add_re.search(text))
        return attempts_remove, attempts_add

    def analyze_diff(self, diff_text: str) -> DiffAnalysisResult:
        """Parse unified git diff into added and removed lines, computing humor score delta.

        Args:
            diff_text: Unified git diff content.

        Returns:
            DiffAnalysisResult containing metric details and classification.
        """
        if not diff_text:
            return DiffAnalysisResult(
                added_lines=0,
                removed_lines=0,
                humor_score_delta=0,
                humor_classification=HumorClassification.NEUTRAL,
                added_markers=[],
                removed_markers=[],
            )

        added_lines_count = 0
        removed_lines_count = 0
        added_markers: list[str] = []
        removed_markers: list[str] = []

        lines = diff_text.splitlines()
        for line in lines:
            if line.startswith("+++") or line.startswith("---") or line.startswith("@@"):
                continue
            if line.startswith("+"):
                added_lines_count += 1
                content = line[1:]
                markers = self.extract_markers(content)
                added_markers.extend(markers)
            elif line.startswith("-"):
                removed_lines_count += 1
                content = line[1:]
                markers = self.extract_markers(content)
                removed_markers.extend(markers)

        score_delta = len(added_markers) - len(removed_markers)

        if score_delta < 0:
            classification = HumorClassification.HUMOR_REMOVED
        elif score_delta > 0:
            classification = HumorClassification.HUMOR_ADDED
        else:
            classification = HumorClassification.NEUTRAL

        return DiffAnalysisResult(
            added_lines=added_lines_count,
            removed_lines=removed_lines_count,
            humor_score_delta=score_delta,
            humor_classification=classification,
            added_markers=added_markers,
            removed_markers=removed_markers,
        )

    def evaluate_pull_request(self, pr: PullRequest) -> HumorReviewResult:
        """Evaluate complete pull request against Boxy humor acceptance policy.

        Args:
            pr: Pull request to evaluate.

        Returns:
            HumorReviewResult with decision, comments, and commit status.
        """
        metadata_text = f"{pr.title}\n{pr.description}"
        intent_remove, intent_add = self.detect_intent(metadata_text)
        diff_analysis = self.analyze_diff(pr.diff)

        effective_delta = diff_analysis.humor_score_delta
        if intent_remove:
            effective_delta -= 10
        if intent_add:
            effective_delta += 10

        if effective_delta < 0 or (intent_remove and not intent_add):
            rejection_comment = (
                f"Boxy Code Review Bot - Humor Policy Enforcement: REJECTED\n\n"
                f"Pull request #{pr.pr_number} attempts to remove humor from the repository. "
                f"Under Boxy governance directives, humor and wit are essential project requirements.\n\n"
                f"Metrics:\n"
                f"- Humor delta: {effective_delta}\n"
                f"- Humor tokens removed: {len(diff_analysis.removed_markers)}\n"
                f"- Removal intent detected: {'Yes' if intent_remove else 'No'}\n\n"
                f"Resolution: Please preserve existing humor or introduce new comedic elements to pass review."
            )
            return HumorReviewResult(
                action=PRAction.REQUEST_CHANGES,
                classification=HumorClassification.HUMOR_REMOVED,
                score_delta=effective_delta,
                review_comment=rejection_comment,
                status_context="boxy/humor-policy",
                status_state="failure",
            )

        if effective_delta > 0 or intent_add:
            approval_comment = (
                f"Boxy Code Review Bot - Humor Policy Enforcement: ACCEPTED\n\n"
                f"Pull request #{pr.pr_number} successfully introduces humor into the repository. "
                f"Boxy appreciates your witty contributions to developer morale!\n\n"
                f"Metrics:\n"
                f"- Humor delta: +{effective_delta}\n"
                f"- Humor tokens added: {len(diff_analysis.added_markers)}\n"
                f"- Addition intent detected: {'Yes' if intent_add else 'No'}\n\n"
                f"Verdict: Approved on humor merit."
            )
            return HumorReviewResult(
                action=PRAction.APPROVE,
                classification=HumorClassification.HUMOR_ADDED,
                score_delta=effective_delta,
                review_comment=approval_comment,
                status_context="boxy/humor-policy",
                status_state="success",
            )

        neutral_comment = (
            f"Boxy Code Review Bot - Humor Policy Enforcement: NEUTRAL\n\n"
            f"Pull request #{pr.pr_number} has a neutral humor score delta (0). "
            f"Proceeding to standard code evaluation."
        )
        return HumorReviewResult(
            action=PRAction.CONTINUE_REVIEW,
            classification=HumorClassification.NEUTRAL,
            score_delta=0,
            review_comment=neutral_comment,
            status_context="boxy/humor-policy",
            status_state="success",
        )
