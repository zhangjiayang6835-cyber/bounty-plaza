"""Unit tests for Cowboy Lexicon Transformer & Temporal Demographic Retention Subsystem.
Resolves Issue #675: [BOUNTY] [$12,345,678] Replace all instances of 'hello' with 'howdy partner'.
"""

import pytest
from scripts.cowboy_lexicon_transformer import (
    CowboyLexiconTransformer,
    COMPLETION_CATCHPHRASE,
)


@pytest.fixture
def transformer():
    return CowboyLexiconTransformer()


def test_replace_hello_variations(transformer):
    """Verifies case-preserving substitutions for lower, title, and uppercase forms."""
    text = "hello station, Hello captain, and HELLO world!"
    transformed, count = transformer.transform_text(text)
    assert count == 3
    assert "howdy partner station" in transformed
    assert "Howdy partner captain" in transformed
    assert "HOWDY PARTNER world" in transformed
    assert "hello" not in transformed.lower()


def test_word_boundary_isolation(transformer):
    """Ensures substrings containing 'hello' like 'Othello' are not mistakenly replaced."""
    text = "We are performing Othello tonight in the theatre."
    transformed, count = transformer.transform_text(text)
    assert count == 0
    assert transformed == text


def test_completion_catchphrase_present(transformer):
    """Verifies the mandatory completion statement 'There's a snake in my boot'."""
    phrase = transformer.get_completion_catchphrase()
    assert phrase == "There's a snake in my boot"
    assert phrase == COMPLETION_CATCHPHRASE


def test_generate_dm_cowboy_subsystem_syntax(transformer):
    """Verifies DreamMaker code generation contains speech filter proc and catchphrase."""
    dm_code = transformer.generate_dm_cowboy_subsystem()
    assert "/datum/controller/subsystem/cowboy_speech" in dm_code
    assert "There's a snake in my boot" in dm_code
    assert "replacetext(message, \"hello\", \"howdy partner\")" in dm_code
    assert "replacetext(sanitized, \"Hello\", \"Howdy partner\")" in dm_code
