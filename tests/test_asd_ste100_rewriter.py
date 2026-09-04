"""Unit tests for ASD-STE100 Simplified Technical English Comment Rewriting Engine.
Resolves Issue #668: [BOUNTY] [100$] Re-write every comment in ASD-STE100 Simplified Technical English.
"""

import pytest
from scripts.asd_ste100_rewriter import (
    ASDSTE100Rewriter,
    MAX_WORDS_INSTRUCTION,
    MAX_WORDS_DESCRIPTIVE,
    STE100SentenceReport,
)


@pytest.fixture
def rewriter():
    return ASDSTE100Rewriter()


def test_controlled_lexicon_substitutions(rewriter):
    """Verifies unapproved colloquialisms, ambiguous verbs, and informal phrases are replaced with approved STE100 terms."""
    # Test verb substitutions
    report1 = rewriter.rewrite_text("run this subsystem prior to start")
    assert "execute this subsystem before start." in report1.rewritten_sentence.lower()

    # Test informal / colloquial replacement
    report2 = rewriter.rewrite_text("this is a hacky workaround because the hardware craps out")
    assert "temporary" in report2.rewritten_sentence
    assert "fails unexpectedly" in report2.rewritten_sentence

    # Test modal substitutions
    report3 = rewriter.rewrite_text("you should make sure all variables are clean")
    assert "must" in report3.rewritten_sentence
    assert "ensure" in report3.rewritten_sentence


def test_sentence_capitalization_and_terminal_punctuation(rewriter):
    """Ensures sentence starts with uppercase and terminates with a period."""
    report = rewriter.rewrite_text("initialize data buffer")
    assert report.rewritten_sentence.startswith("I")
    assert report.rewritten_sentence.endswith(".")


def test_compound_sentence_splitting_for_word_count(rewriter):
    """Ensures overly long compound sentences exceeding word thresholds are cleanly partitioned."""
    long_compound = (
        "execute the primary initialization loop for all station components and subsystems, "
        "and verify that every single data stream is fully synchronized with the controller"
    )
    report = rewriter.rewrite_text(long_compound, is_instruction=True)
    # Checks that compound was split into multiple sentences
    assert "." in report.rewritten_sentence
    sentences = [s.strip() for s in report.rewritten_sentence.split(".") if s.strip()]
    assert len(sentences) >= 2
    for s in sentences:
        assert len(s.split()) <= MAX_WORDS_INSTRUCTION + 2


def test_format_comment_dm_and_python(rewriter):
    """Tests language comment wrapper generation for DM and Python."""
    dm_out = rewriter.format_comment("run memory check", language="dm")
    assert "/* [STE100] Execute memory check. */" in dm_out

    py_out = rewriter.format_comment("run memory check", language="py")
    assert "# [STE100] Execute memory check." in py_out


def test_process_source_code_batch(rewriter):
    """Tests full source code file rewriting and reporting."""
    sample_code = (
        "// run setup prior to round start\n"
        "/datum/controller/subsystem/proc/setup()\n"
        "\t// make sure data buffer is not hacky\n"
        "\treturn 1\n"
    )

    report = rewriter.process_source_code(sample_code, language="dm")
    assert report.total_comments_processed == 2
    assert report.compliant_comments == 2
    assert report.modifications_made >= 2

    rewritten_code = "\n".join(report.rewritten_lines)
    assert "// [STE100] Execute setup before round start." in rewritten_code
    assert "Ensure data buffer is not temporary." in rewritten_code
    assert "/datum/controller/subsystem/proc/setup()" in rewritten_code
