"""RuneScape Chat Effects Parser and HTML/CSS Maptext Renderer.
Resolves Issue #741: Add Runescape inspired chat effects ($500 USD).

Implements:
1. Lexing and parsing of RuneScape chat prefix syntax (e.g. 'red:wave:buying gf 10k', 'flash1:shake:hello').
2. Color effects:
   - Static colors: yellow (default), red, green, cyan, purple, white.
   - Dynamic animated flash: flash1 (red/yellow), flash2 (cyan/blue), flash3 (light/dark green).
   - Dynamic animated glow: glow1 (red->orange->yellow->green->cyan), glow2 (red->magenta->blue->dark red), glow3 (white->green->white->cyan).
   - Dynamic animated rainbow: rainbow.
3. Motion effects:
   - wave (vertical oscillation), wave2 (diagonal oscillation), shake (jitter/vibration), slide (vertical scroll in/out), scroll (right-to-left ticker).
4. Compositor generating clean sanitized HTML/CSS maptext payloads for runechat renderers.
"""

import html
import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class ColorEffect(str, Enum):
    YELLOW = "yellow"
    RED = "red"
    GREEN = "green"
    CYAN = "cyan"
    PURPLE = "purple"
    WHITE = "white"
    FLASH1 = "flash1"
    FLASH2 = "flash2"
    FLASH3 = "flash3"
    GLOW1 = "glow1"
    GLOW2 = "glow2"
    GLOW3 = "glow3"
    RAINBOW = "rainbow"


class MotionEffect(str, Enum):
    WAVE = "wave"
    WAVE2 = "wave2"
    SHAKE = "shake"
    SLIDE = "slide"
    SCROLL = "scroll"


COLOR_HEX_MAP: Dict[ColorEffect, str] = {
    ColorEffect.YELLOW: "#FFFF00",
    ColorEffect.RED: "#FF0000",
    ColorEffect.GREEN: "#00FF00",
    ColorEffect.CYAN: "#00FFFF",
    ColorEffect.PURPLE: "#800080",
    ColorEffect.WHITE: "#FFFFFF",
}

CSS_KEYFRAMES: Dict[str, str] = {
    "flash1": "@keyframes flash1 { 0%, 100% { color: #FF0000; } 50% { color: #FFFF00; } }",
    "flash2": "@keyframes flash2 { 0%, 100% { color: #00FFFF; } 50% { color: #0000FF; } }",
    "flash3": "@keyframes flash3 { 0%, 100% { color: #90EE90; } 50% { color: #006400; } }",
    "glow1": "@keyframes glow1 { 0% { color: #FF0000; } 25% { color: #FFA500; } 50% { color: #FFFF00; } 75% { color: #00FF00; } 100% { color: #00FFFF; } }",
    "glow2": "@keyframes glow2 { 0% { color: #FF0000; } 33% { color: #FF00FF; } 66% { color: #0000FF; } 100% { color: #8B0000; } }",
    "glow3": "@keyframes glow3 { 0% { color: #FFFFFF; } 33% { color: #00FF00; } 66% { color: #FFFFFF; } 100% { color: #00FFFF; } }",
    "rainbow": "@keyframes rainbow { 0% { color: #FF0000; } 20% { color: #FFA500; } 40% { color: #FFFF00; } 60% { color: #00FF00; } 80% { color: #0000FF; } 100% { color: #8B00FF; } }",
    "wave": "@keyframes wave { 0%, 100% { transform: translateY(0px); } 50% { transform: translateY(-4px); } }",
    "wave2": "@keyframes wave2 { 0%, 100% { transform: translate(0px, 0px); } 50% { transform: translate(4px, -4px); } }",
    "shake": "@keyframes shake { 0%, 100% { transform: translate(0px, 0px); } 25% { transform: translate(-2px, 1px); } 50% { transform: translate(2px, -1px); } 75% { transform: translate(-1px, -2px); } }",
    "slide": "@keyframes slide { 0% { transform: translateY(-100%); opacity: 0; } 20%, 80% { transform: translateY(0); opacity: 1; } 100% { transform: translateY(100%); opacity: 0; } }",
    "scroll": "@keyframes scroll { 0% { transform: translateX(100%); } 100% { transform: translateX(-100%); } }",
}


@dataclass
class ParsedChatMessage:
    color: ColorEffect
    motion: Optional[MotionEffect]
    raw_text: str
    clean_text: str
    applied_prefixes: List[str]


class RuneScapeChatParser:
    """Parses messages with RuneScape chat effect prefixes and renders them to maptext."""

    def __init__(self):
        self._valid_colors = {e.value: e for e in ColorEffect}
        self._valid_motions = {e.value: e for e in MotionEffect}
        # Prefix pattern: allows up to two chained colon prefixes: e.g. "red:wave:msg" or "wave:red:msg"
        self._prefix_regex = re.compile(r"^([a-zA-Z0-9]+):(?:([a-zA-Z0-9]+):)?\s*(.*)$")

    def parse(self, message: str) -> ParsedChatMessage:
        """Parses a message string, identifying valid color and motion effects."""
        color: ColorEffect = ColorEffect.YELLOW  # default color is yellow
        motion: Optional[MotionEffect] = None
        applied: List[str] = []

        match = self._prefix_regex.match(message)
        if not match:
            return ParsedChatMessage(
                color=color,
                motion=motion,
                raw_text=message,
                clean_text=message,
                applied_prefixes=applied,
            )

        tag1, tag2, remainder = match.groups()
        tag1_lower = tag1.lower() if tag1 else ""
        tag2_lower = tag2.lower() if tag2 else ""

        # Check tag1
        tag1_used = False
        if tag1_lower in self._valid_colors:
            color = self._valid_colors[tag1_lower]
            applied.append(tag1_lower)
            tag1_used = True
        elif tag1_lower in self._valid_motions:
            motion = self._valid_motions[tag1_lower]
            applied.append(tag1_lower)
            tag1_used = True

        # Check tag2 if present and tag1 was valid
        if tag1_used and tag2:
            if tag2_lower in self._valid_colors and color == ColorEffect.YELLOW:
                color = self._valid_colors[tag2_lower]
                applied.append(tag2_lower)
            elif tag2_lower in self._valid_motions and motion is None:
                motion = self._valid_motions[tag2_lower]
                applied.append(tag2_lower)
            else:
                # tag2 is not a secondary effect, treat tag2 + remainder as message text
                remainder = f"{tag2}:{remainder}"
        elif not tag1_used:
            # Neither tag was valid, entire string is message
            return ParsedChatMessage(
                color=ColorEffect.YELLOW,
                motion=None,
                raw_text=message,
                clean_text=message,
                applied_prefixes=[],
            )

        clean_text = remainder.strip()
        return ParsedChatMessage(
            color=color,
            motion=motion,
            raw_text=message,
            clean_text=clean_text,
            applied_prefixes=applied,
        )

    def render_html(self, parsed: ParsedChatMessage) -> str:
        """Renders parsed message to safe, escaped HTML with inline styles and CSS animation classes."""
        escaped_text = html.escape(parsed.clean_text)
        classes = ["runechat-msg", f"rc-color-{parsed.color.value}"]
        styles = []

        if parsed.color in COLOR_HEX_MAP:
            styles.append(f"color: {COLOR_HEX_MAP[parsed.color]};")

        if parsed.motion:
            classes.append(f"rc-motion-{parsed.motion.value}")

        style_attr = f' style="{" ".join(styles)}"' if styles else ""
        class_attr = f' class="{" ".join(classes)}"'

        return f'<span{class_attr}{style_attr}>{escaped_text}</span>'

    def get_required_css(self, parsed: ParsedChatMessage) -> str:
        """Returns the minimal CSS animation definitions needed for the parsed message."""
        css_rules = []
        if parsed.color.value in CSS_KEYFRAMES:
            css_rules.append(CSS_KEYFRAMES[parsed.color.value])
        if parsed.motion and parsed.motion.value in CSS_KEYFRAMES:
            css_rules.append(CSS_KEYFRAMES[parsed.motion.value])
        return "\n".join(css_rules)
