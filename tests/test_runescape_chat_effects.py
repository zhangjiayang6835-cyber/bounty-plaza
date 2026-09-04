"""Unit test suite for RuneScape Chat Effects Parser and Maptext Renderer.
Resolves Issue #741: Add Runescape inspired chat effects ($500 USD).
"""

import pytest
from scripts.runescape_chat_effects import (
    RuneScapeChatParser,
    ColorEffect,
    MotionEffect,
    COLOR_HEX_MAP,
    CSS_KEYFRAMES,
)


@pytest.fixture
def parser():
    return RuneScapeChatParser()


def test_default_color_is_yellow_without_prefix(parser):
    parsed = parser.parse("Hello fellow adventurers!")
    assert parsed.color == ColorEffect.YELLOW
    assert parsed.motion is None
    assert parsed.clean_text == "Hello fellow adventurers!"
    assert parsed.applied_prefixes == []

    html = parser.render_html(parsed)
    assert 'color: #FFFF00;' in html
    assert "rc-color-yellow" in html
    assert "Hello fellow adventurers!" in html


def test_static_color_effects(parser):
    colors = [
        ("red:fire sale", ColorEffect.RED, "fire sale"),
        ("green:buying logs", ColorEffect.GREEN, "buying logs"),
        ("cyan:selling runes", ColorEffect.CYAN, "selling runes"),
        ("purple:teleporting now", ColorEffect.PURPLE, "teleporting now"),
        ("white:pure white text", ColorEffect.WHITE, "pure white text"),
        ("yellow:explicit yellow", ColorEffect.YELLOW, "explicit yellow"),
    ]
    for raw, expected_color, expected_text in colors:
        parsed = parser.parse(raw)
        assert parsed.color == expected_color
        assert parsed.motion is None
        assert parsed.clean_text == expected_text
        html = parser.render_html(parsed)
        assert f"rc-color-{expected_color.value}" in html
        assert COLOR_HEX_MAP[expected_color] in html


def test_animated_flash_glow_and_rainbow_effects(parser):
    animated = [
        ("flash1:attention!", ColorEffect.FLASH1, "attention!"),
        ("flash2:party at falador", ColorEffect.FLASH2, "party at falador"),
        ("flash3:wilderness danger", ColorEffect.FLASH3, "wilderness danger"),
        ("glow1:dragon scimitar 100k", ColorEffect.GLOW1, "dragon scimitar 100k"),
        ("glow2:rune platebody 50k", ColorEffect.GLOW2, "rune platebody 50k"),
        ("glow3:selling abyss items", ColorEffect.GLOW3, "selling abyss items"),
        ("rainbow:taste the rainbow", ColorEffect.RAINBOW, "taste the rainbow"),
    ]
    for raw, expected_color, expected_text in animated:
        parsed = parser.parse(raw)
        assert parsed.color == expected_color
        assert parsed.clean_text == expected_text
        css = parser.get_required_css(parsed)
        assert f"@keyframes {expected_color.value}" in css


def test_motion_effects(parser):
    motions = [
        ("wave:ocean breeze", MotionEffect.WAVE, "ocean breeze"),
        ("wave2:diagonal surfing", MotionEffect.WAVE2, "diagonal surfing"),
        ("shake:earthquake incoming", MotionEffect.SHAKE, "earthquake incoming"),
        ("slide:sliding in", MotionEffect.SLIDE, "sliding in"),
        ("scroll:news ticker message", MotionEffect.SCROLL, "news ticker message"),
    ]
    for raw, expected_motion, expected_text in motions:
        parsed = parser.parse(raw)
        assert parsed.color == ColorEffect.YELLOW  # defaults to yellow
        assert parsed.motion == expected_motion
        assert parsed.clean_text == expected_text
        html = parser.render_html(parsed)
        assert f"rc-motion-{expected_motion.value}" in html
        css = parser.get_required_css(parsed)
        assert f"@keyframes {expected_motion.value}" in css


def test_combined_color_and_motion_prefixes(parser):
    # Color first, motion second
    parsed1 = parser.parse("red:wave:buying gf 10k")
    assert parsed1.color == ColorEffect.RED
    assert parsed1.motion == MotionEffect.WAVE
    assert parsed1.clean_text == "buying gf 10k"
    assert parsed1.applied_prefixes == ["red", "wave"]

    # Motion first, color second
    parsed2 = parser.parse("shake:glow2:emergency broadcast")
    assert parsed2.color == ColorEffect.GLOW2
    assert parsed2.motion == MotionEffect.SHAKE
    assert parsed2.clean_text == "emergency broadcast"
    assert parsed2.applied_prefixes == ["shake", "glow2"]

    html = parser.render_html(parsed2)
    assert "rc-color-glow2" in html
    assert "rc-motion-shake" in html
    css = parser.get_required_css(parsed2)
    assert "@keyframes glow2" in css
    assert "@keyframes shake" in css


def test_xss_sanitization_in_html_renderer(parser):
    evil_msg = "red:wave:<script>alert('pwned')</script>&\"'"
    parsed = parser.parse(evil_msg)
    html = parser.render_html(parsed)
    assert "<script>" not in html
    assert "&lt;script&gt;alert(&#x27;pwned&#x27;)&lt;/script&gt;&amp;&quot;&#x27;" in html


def test_unrecognized_prefix_treated_as_message(parser):
    raw = "unknownprefix:normal text message"
    parsed = parser.parse(raw)
    assert parsed.color == ColorEffect.YELLOW
    assert parsed.motion is None
    assert parsed.clean_text == "unknownprefix:normal text message"
    assert parsed.applied_prefixes == []
