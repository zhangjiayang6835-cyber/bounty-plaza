"""Unit tests for Felinid Owospeak Speech Filter.
Resolves Issue #684: Apply an owospeak speech filter to the felinid species ($30 USD).
"""

import pytest
from scripts.owospeak_filter import FelinidOwospeakFilter, OWO_EMOTICONS


@pytest.fixture
def filter_engine():
    # Fixed seed for deterministic testing
    return FelinidOwospeakFilter(emoticon_chance=1.0, rng_seed=42)


def test_felinid_species_detection(filter_engine):
    assert filter_engine.is_felinid("felinid") is True
    assert filter_engine.is_felinid("FELINID") is True
    assert filter_engine.is_felinid("cat") is True
    assert filter_engine.is_felinid("species_felinid") is True
    assert filter_engine.is_felinid("human") is False
    assert filter_engine.is_felinid("lizard") is False
    assert filter_engine.is_felinid(None) is False


def test_non_felinid_speech_unmodified(filter_engine):
    human_msg = "Hello security officer, please open the airlock."
    res = filter_engine.filter_speech(human_msg, speaker_species="human")
    assert res == human_msg


def test_phonetic_transformations(filter_engine):
    test_cases = [
        ("Hello world", "Hewwo wowwd"),
        ("I love nuclear physics", "I wuv nyucweaw physics"),
        ("Look at this little rat", "Wook at this wittwe wat"),
        ("Never gonna give you up", "Nyevew gonnya give you up"),
    ]
    for original, expected in test_cases:
        transformed = filter_engine.transform_text(original)
        assert transformed == expected


def test_felinid_speech_transformation_with_owoism():
    engine = FelinidOwospeakFilter(emoticon_chance=1.0, rng_seed=123)
    msg = "I love this station!"
    res = engine.filter_speech(msg, speaker_species="felinid")
    assert "wuv" in res
    # Must contain one of the recognized emoticons
    assert any(emo in res for emo in OWO_EMOTICONS)


def test_url_preservation(filter_engine):
    msg = "Look at this https://tgstation13.org/wiki/Felinid please"
    res = filter_engine.transform_text(msg)
    assert "https://tgstation13.org/wiki/Felinid" in res
    assert "Wook at this" in res


def test_empty_or_whitespace_speech(filter_engine):
    assert filter_engine.filter_speech("", speaker_species="felinid") == ""
    assert filter_engine.filter_speech("   ", speaker_species="felinid") == "   "
