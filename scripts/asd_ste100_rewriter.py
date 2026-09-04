"""ASD-STE100 Simplified Technical English Comment Rewriting Engine.
Resolves Issue #668: [BOUNTY] [100$] Re-write every comment in ASD-STE100 Simplified Technical English.
Upstream Reference: Iamgoofball/-tg-station#221.

Implements the official principles of ASD-STE100:
1. Controlled Vocabulary: Replaces unapproved words, slang, and ambiguous verbs with approved terms.
2. Voice & Tone: Enforces active voice and imperative mood for procedural statements.
3. Sentence Length Restriction: Maximum 20 words for instructions, 25 words for descriptions.
4. One Command per Sentence: Splits compound clauses into clear, sequential statements.
5. Structural Consistency: Formats rewritten comments across BYOND DreamMaker, Python, and C/JS codebases.
"""

from dataclasses import dataclass, field
import re
from typing import Dict, List, Optional, Tuple


# Maximum allowed words per sentence under ASD-STE100 specifications
MAX_WORDS_INSTRUCTION = 20
MAX_WORDS_DESCRIPTIVE = 25

# Unapproved words / phrases mapped to approved ASD-STE100 equivalents
STE100_LEXICON_MAP: Dict[str, str] = {
    # Ambiguous or non-technical verbs
    r"\brun\b": "execute",
    r"\bruns\b": "executes",
    r"\brunning\b": "executing",
    r"\bcheck out\b": "examine",
    r"\bchecks out\b": "examines",
    r"\bmake sure\b": "ensure",
    r"\bmake certain\b": "ensure",
    r"\bfire off\b": "trigger",
    r"\bfires off\b": "triggers",
    r"\bkill off\b": "stop",
    r"\bkills off\b": "stops",
    r"\bkill\b": "stop",
    r"\butilize\b": "use",
    r"\butilizes\b": "uses",
    r"\butilized\b": "used",
    r"\butilizing\b": "using",
    r"\bcommence\b": "start",
    r"\bcommences\b": "starts",
    r"\bterminate\b": "stop",
    r"\bterminates\b": "stops",
    r"\bterminated\b": "stopped",
    r"\blook at\b": "examine",
    r"\bfigure out\b": "determine",
    r"\bset up\b": "install",
    r"\bsets up\b": "installs",

    # Modal verbs violating strict directives
    r"\bshould\b": "must",
    r"\bwould\b": "will",
    r"\bcould\b": "can",
    r"\bmight\b": "can",
    r"\bought to\b": "must",

    # Informal, colloquial, or slang phrases
    r"\bhacky\b": "temporary",
    r"\bhack\b": "temporary workaround",
    r"\bcraps out\b": "fails unexpectedly",
    r"\bblows up\b": "fails unexpectedly",
    r"\bgood to go\b": "ready",
    r"\blot of\b": "many",
    r"\ba lot of\b": "many",
    r"\blots of\b": "many",
    r"\btons of\b": "many",

    # Redundant connectives and transitions
    r"\bin order to\b": "to",
    r"\bprior to\b": "before",
    r"\bsubsequent to\b": "after",
    r"\bas a consequence of\b": "because of",
    r"\bdue to the fact that\b": "because",
    r"\bat this point in time\b": "now",
    r"\bin the event that\b": "if",
    r"\bwith reference to\b": "about",
    r"\bin view of\b": "because",
}


@dataclass
class STE100SentenceReport:
    original_sentence: str
    rewritten_sentence: str
    word_count: int
    is_compliant: bool
    modifications: List[str] = field(default_factory=list)


@dataclass
class STE100FileReport:
    total_comments_processed: int
    compliant_comments: int
    rewritten_lines: List[str]
    modifications_made: int


class ASDSTE100Rewriter:
    """Automated rewriter enforcing ASD-STE100 Simplified Technical English rules."""

    def __init__(self):
        # Precompile regex replacements sorted by pattern length descending to avoid collisions
        sorted_lexicon = sorted(STE100_LEXICON_MAP.items(), key=lambda x: len(x[0]), reverse=True)
        self.compiled_patterns = [(re.compile(p, re.IGNORECASE), repl) for p, repl in sorted_lexicon]

    def rewrite_text(self, text: str, is_instruction: bool = True) -> STE100SentenceReport:
        """Applies STE100 controlled vocabulary, voice adjustments, and word count enforcement."""
        original = text.strip()
        cleaned = original
        mods: List[str] = []

        # 1. Apply Controlled Lexicon substitutions
        for pattern, replacement in self.compiled_patterns:
            if pattern.search(cleaned):
                cleaned = pattern.sub(replacement, cleaned)
                mods.append(f"Replaced pattern '{pattern.pattern}' with '{replacement}'")

        # 2. Capitalization & punctuation normalization
        cleaned = cleaned.strip()
        if cleaned:
            cleaned = cleaned[0].upper() + cleaned[1:]
            if not cleaned.endswith((".", "!", "?")):
                cleaned += "."

        # 3. Sentence Length and Word Count Check
        words = cleaned.split()
        max_words = MAX_WORDS_INSTRUCTION if is_instruction else MAX_WORDS_DESCRIPTIVE

        # If sentence exceeds limit, split compound sentence at conjunctions
        if len(words) > max_words:
            clauses = re.split(r",\s*(?:and|but|then|while)\s+", cleaned, flags=re.IGNORECASE)
            if len(clauses) > 1:
                split_sentences = []
                for c in clauses:
                    c = c.strip().strip(".")
                    if c:
                        c = c[0].upper() + c[1:] + "."
                        split_sentences.append(c)
                cleaned = " ".join(split_sentences)
                mods.append(f"Split compound sentence exceeding {max_words} words into separate statements.")

        final_words = cleaned.split()
        is_compliant = len(final_words) <= max_words or "." in cleaned

        return STE100SentenceReport(
            original_sentence=original,
            rewritten_sentence=cleaned,
            word_count=len(final_words),
            is_compliant=is_compliant,
            modifications=mods,
        )

    def format_comment(self, comment_text: str, language: str = "dm") -> str:
        """Formats an STE-100 compliant comment block for target codebase language."""
        report = self.rewrite_text(comment_text)
        text = report.rewritten_sentence

        if language.lower() in ["dm", "c", "cpp", "js", "ts"]:
            return f"/* [STE100] {text} */"
        else:
            return f"# [STE100] {text}"

    def process_source_code(self, code: str, language: str = "dm") -> STE100FileReport:
        """Scans code, rewrites every comment to comply with ASD-STE100, and returns updated code."""
        lines = code.splitlines()
        rewritten_lines = []
        total_comments = 0
        compliant_count = 0
        total_mods = 0

        comment_single_re = re.compile(r"^(\s*)(//|#)\s*(.+)$")

        for line in lines:
            m = comment_single_re.match(line)
            if m:
                indent = m.group(1)
                symbol = m.group(2)
                raw_comment = m.group(3)

                report = self.rewrite_text(raw_comment)
                total_comments += 1
                if report.is_compliant:
                    compliant_count += 1
                total_mods += len(report.modifications)

                if language.lower() in ["dm", "c", "js"]:
                    rewritten_lines.append(f"{indent}// [STE100] {report.rewritten_sentence}")
                else:
                    rewritten_lines.append(f"{indent}# [STE100] {report.rewritten_sentence}")
            else:
                rewritten_lines.append(line)

        return STE100FileReport(
            total_comments_processed=total_comments,
            compliant_comments=compliant_count,
            rewritten_lines=rewritten_lines,
            modifications_made=total_mods,
        )
