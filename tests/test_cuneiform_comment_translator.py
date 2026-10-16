"""Unit tests for Cuneiform Comment Translation Engine.
Resolves Issue #672: [BOUNTY] [$2500] Translate comments into cuneiform for further accessibility.
"""

import pytest
from scripts.cuneiform_comment_translator import (
    CuneiformTranslator,
    CUNEIFORM_UNICODE_MIN,
    CUNEIFORM_UNICODE_MAX,
    SUMERIAN_SEMANTIC_MAP,
)


@pytest.fixture
def translator():
    return CuneiformTranslator()


def test_cuneiform_unicode_range_validity(translator):
    """Verifies that all mapped characters and ideograms fall strictly within U+12000 to U+123FF."""
    for word, glyph in SUMERIAN_SEMANTIC_MAP.items():
        for char in glyph:
            assert translator.is_valid_cuneiform_char(char), (
                f"Glyph for '{word}' ({hex(ord(char))}) outside U+12000-U+123FF range"
            )


def test_translate_semantic_keywords(translator):
    """Tests that high-level technical keywords are mapped to correct Sumerian ideograms."""
    assert translator.translate_word("system") == "\U00012174"
    assert translator.translate_word("controller") == "\U00012217"
    assert translator.translate_word("memory") == "\U000122A0"
    assert translator.translate_word("error") == "\U00012150"
    assert translator.translate_word("validate") == "\U000122F0"


def test_translate_sentence_produces_valid_cuneiform_stream(translator):
    """Tests sentence-level translation and checks that all generated characters are within the Cuneiform block."""
    sentence = "Initialize subsystem memory controller and validate data"
    translated = translator.translate_sentence(sentence)
    assert len(translated) > 0

    tokens = translated.split()
    assert len(tokens) == len(sentence.split())
    for token in tokens:
        for ch in token:
            assert CUNEIFORM_UNICODE_MIN <= ord(ch) <= CUNEIFORM_UNICODE_MAX


def test_format_comment_dm_and_python(translator):
    """Tests multilingual formatting for DreamMaker and Python comments."""
    dm_comment = translator.format_comment("Initialize memory controller", language="dm")
    assert "/*" in dm_comment
    assert "[EN] Initialize memory controller" in dm_comment
    assert "[CUNEIFORM: U+12000-U+123FF]" in dm_comment
    assert "*/" in dm_comment

    py_comment = translator.format_comment("Verify clean data flow", language="py")
    assert "# [EN] Verify clean data flow" in py_comment
    assert "# [CUNEIFORM: U+12000-U+123FF]" in py_comment


def test_process_source_code_injection(translator):
    """Verifies scanning and replacing source code comments with paired cuneiform blocks."""
    sample_dm_code = (
        "// Initialize controller memory\n"
        "/datum/controller/subsystem/proc/setup()\n"
        "\t// Clean data buffer\n"
        "\treturn 1\n"
    )

    result = translator.process_source_code(sample_dm_code, language="dm")
    assert "/* [EN] Initialize controller memory */" in result
    assert "/* [CUNEIFORM]" in result
    assert "/* [EN] Clean data buffer */" in result
    assert "/datum/controller/subsystem/proc/setup()" in result
