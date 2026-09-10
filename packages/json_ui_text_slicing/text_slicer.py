"""Bedrock JSON UI dynamic container inventory text slicing engine.

Implements native Bedrock JSON UI string-slicing arithmetic, text preservation
bindings, UTF-8 boundary integrity, formatting code preservation, and multi-scale
viewport validation across Desktop, Pocket, and Console GUI scales.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Optional


class GuiScaleMode(str, Enum):
    """Supported GUI scale environments in Bedrock Edition."""

    DESKTOP = "desktop"
    POCKET = "pocket"
    CONSOLE = "console"


@dataclass(frozen=True)
class ViewportConfig:
    """Configuration representing GUI viewport constraints and scaling.

    Attributes:
        mode: Target GUI scale environment.
        screen_width: Width of display in virtual pixels.
        screen_height: Height of display in virtual pixels.
        gui_scale: Integer GUI scale multiplier.
        max_container_label_width: Maximum allowed width for container item text in pixels.
        max_characters: Maximum characters permitted before truncation.
    """

    mode: GuiScaleMode
    screen_width: int
    screen_height: int
    gui_scale: int
    max_container_label_width: int
    max_characters: int = 16


@dataclass
class TextSliceResult:
    """Result of string slicing and text preservation operations.

    Attributes:
        original_text: Raw incoming text before processing.
        sliced_text: Text resulting from slicing and preservation rules.
        byte_length: Byte count of the resulting sliced text in UTF-8.
        char_length: Codepoint count of visible characters.
        was_truncated: Flag indicating if input exceeded length constraint.
        utf8_safe: Flag indicating no multi-byte sequence was fragmented.
        warnings: List of diagnostic warnings generated during evaluation.
    """

    original_text: str
    sliced_text: str
    byte_length: int
    char_length: int
    was_truncated: bool
    utf8_safe: bool
    warnings: list[str] = field(default_factory=list)

    @property
    def is_preserved(self) -> bool:
        """Indicate whether the original string was preserved unchanged."""
        return not self.was_truncated


class FormatSpecifier:
    """Evaluator for native Bedrock JSON UI format specifier expressions."""

    SPECIFIER_PATTERN = re.compile(r"^%(-)?(0)?(\d+)?(?:\.(\d+))?s$")
    EXPRESSION_PATTERN = re.compile(
        r"^\(\s*'([%a-zA-Z0-9_.-]+)'\s*([*+-])\s*([#$a-zA-Z0-9_.-]+)\s*\)$"
    )

    @classmethod
    def parse_specifier(cls, specifier: str) -> Optional[dict[str, Any]]:
        """Parse Bedrock JSON UI format specifier into component attributes.

        Args:
            specifier: Format string such as '%.16s', '%016s', or '%-16s'.

        Returns:
            Dictionary with parsed flags, width, and precision, or None if invalid.
        """
        match = cls.SPECIFIER_PATTERN.match(specifier)
        if not match:
            return None
        left_align = match.group(1) is not None
        zero_check = match.group(2) is not None
        width_str = match.group(3)
        precision_str = match.group(4)

        result_dict = {
            "left_align": left_align,
            "zero_check": zero_check,
            "width": int(width_str) if width_str else None,
            "precision": int(precision_str) if precision_str else None,
            "raw": specifier,
        }
        return result_dict

    @classmethod
    def _apply_precision(cls, text: str, precision: Optional[int]) -> str:
        """Truncate text to specified byte length without breaking UTF-8 codepoints.

        Args:
            text: String to truncate.
            precision: Maximum byte length.

        Returns:
            Truncated string.
        """
        if precision is None:
            return text
        encoded = text.encode("utf-8")
        if len(encoded) <= precision:
            return text
        trimmed = encoded[:precision]
        while trimmed:
            try:
                return trimmed.decode("utf-8")
            except UnicodeDecodeError:
                trimmed = trimmed[:-1]
        return ""

    @classmethod
    def _apply_padding(cls, text: str, left_align: bool, width: Optional[int]) -> str:
        """Pad string on right with spaces if width constraint requires.

        Args:
            text: String to pad.
            left_align: True if left-aligned flag was parsed.
            width: Minimum required byte width.

        Returns:
            Padded string.
        """
        if not left_align or width is None:
            return text
        encoded = text.encode("utf-8")
        if len(encoded) >= width:
            return text
        pad = " " * (width - len(encoded))
        return f"{text}{pad}"

    @classmethod
    def apply_format(cls, specifier: str, text: str) -> tuple[str, list[str]]:
        """Apply a parsed format specifier to an input text value.

        Args:
            specifier: Format specifier string.
            text: Input string value to format.

        Returns:
            Tuple containing the formatted text and any generated warnings.
        """
        parsed = cls.parse_specifier(specifier)
        if not parsed:
            warning_msg = f"Invalid format specifier '{specifier}'"
            return text, [warning_msg]

        if parsed["zero_check"] and parsed["width"] is not None:
            min_len = parsed["width"]
            if len(text.encode("utf-8")) >= min_len:
                return text, []
            return "0", []

        result = cls._apply_precision(text, parsed["precision"])
        result = cls._apply_padding(result, parsed["left_align"], parsed["width"])
        return result, []


class BedrockJsonUiEngine:
    """Core simulation and validation engine for Bedrock JSON UI systems."""

    DEFAULT_MAX_CHARS: int = 16
    FORMAT_CODE_CHAR: str = "§"

    @classmethod
    def get_default_viewport(cls, mode: GuiScaleMode) -> ViewportConfig:
        """Derive standard viewport configuration for a target platform.

        Args:
            mode: GUI scale environment enum value.

        Returns:
            Configured ViewportConfig instance.
        """
        if mode == GuiScaleMode.POCKET:
            return ViewportConfig(
                mode=mode,
                screen_width=480,
                screen_height=320,
                gui_scale=2,
                max_container_label_width=96,
                max_characters=16,
            )
        if mode == GuiScaleMode.CONSOLE:
            return ViewportConfig(
                mode=mode,
                screen_width=1920,
                screen_height=1080,
                gui_scale=3,
                max_container_label_width=140,
                max_characters=16,
            )
        return ViewportConfig(
            mode=mode,
            screen_width=1280,
            screen_height=720,
            gui_scale=2,
            max_container_label_width=160,
            max_characters=16,
        )

    @classmethod
    def clean_format_codes(cls, text: str) -> str:
        """Strip Bedrock section symbol formatting codes for length measurement.

        Args:
            text: Input string with potential formatting codes.

        Returns:
            String with formatting codes removed.
        """
        pattern = re.compile(r"§[0-9a-fk-or]")
        return pattern.sub("", text)

    @classmethod
    def _slice_preserving_formatting(cls, text: str, max_chars: int) -> str:
        """Extract visible characters up to limit while preserving formatting codes.

        Args:
            text: Source string.
            max_chars: Maximum visible characters.

        Returns:
            Truncated string with formatting codes intact.
        """
        chars: list[str] = []
        visible = 0
        idx = 0
        text_len = len(text)
        while idx < text_len and visible < max_chars:
            ch = text[idx]
            if ch == cls.FORMAT_CODE_CHAR and (idx + 1) < text_len:
                chars.append(ch)
                chars.append(text[idx + 1])
                idx += 2
                continue
            chars.append(ch)
            visible += 1
            idx += 1
        return "".join(chars)

    @classmethod
    def slice_text(
        cls,
        text: str,
        max_chars: int = DEFAULT_MAX_CHARS,
        preserve_formatting: bool = True,
        utf8_safe: bool = True,
    ) -> TextSliceResult:
        """Perform 16-character string truncation utilizing native Bedrock JSON UI bindings.

        Args:
            text: Source item name or inventory container text.
            max_chars: Maximum visible character limit (default 16).
            preserve_formatting: Whether to maintain Bedrock formatting codes.
            utf8_safe: Whether to prevent multi-byte UTF-8 split errors.

        Returns:
            TextSliceResult with processed text and validation metrics.
        """
        clean_text = cls.clean_format_codes(text) if preserve_formatting else text
        visible_len = len(clean_text)

        if visible_len <= max_chars:
            return TextSliceResult(
                original_text=text,
                sliced_text=text,
                byte_length=len(text.encode("utf-8")),
                char_length=visible_len,
                was_truncated=False,
                utf8_safe=True,
                warnings=[],
            )

        if preserve_formatting:
            sliced = cls._slice_preserving_formatting(text, max_chars)
        else:
            sliced = text[:max_chars]

        is_safe = True
        if utf8_safe:
            try:
                is_safe = sliced.encode("utf-8").decode("utf-8") == sliced
            except UnicodeError:
                is_safe = False

        res_bytes = sliced.encode("utf-8")
        clean_sliced = (
            cls.clean_format_codes(sliced) if preserve_formatting else sliced
        )

        return TextSliceResult(
            original_text=text,
            sliced_text=sliced,
            byte_length=len(res_bytes),
            char_length=len(clean_sliced),
            was_truncated=True,
            utf8_safe=is_safe,
            warnings=[],
        )

    @classmethod
    def evaluate_binding_expression(
        cls,
        expression: str,
        context_bindings: dict[str, str],
    ) -> tuple[str, list[str]]:
        """Evaluate a Bedrock JSON UI binding expression against available variables.

        Args:
            expression: Expression string to evaluate.
            context_bindings: Mapping of variable names to string values.

        Returns:
            Tuple of resolved string and diagnostic warnings or errors.
        """
        warnings: list[str] = []

        if expression.startswith("%") and ("*" not in expression and "-" not in expression):
            warnings.append(
                "Binding resolution failed for #inventory_text_slice "
                "in panel 'hud_custom_container_root'."
            )
            warnings.append(
                f"Expression '{expression}' failed: invalid binding format specifier."
            )
            return "", warnings

        match = FormatSpecifier.EXPRESSION_PATTERN.match(expression)
        if not match:
            if expression in context_bindings:
                return context_bindings[expression], warnings
            warnings.append(f"Binding resolution failed for {expression}.")
            return "", warnings

        spec_str, op, operand = match.group(1), match.group(2), match.group(3)
        if operand not in context_bindings:
            warnings.append(f"Binding variable {operand} not found in scope.")
            return "", warnings

        source = context_bindings[operand]
        resolved = source
        if op == "*":
            res, fmt_warns = FormatSpecifier.apply_format(spec_str, source)
            warnings.extend(fmt_warns)
            resolved = res
        elif op == "-" and source.startswith(spec_str):
            resolved = source[len(spec_str) :]

        return resolved, warnings

    @classmethod
    def _inspect_panel_controls(
        cls, controls: list[dict[str, Any]]
    ) -> tuple[bool, bool]:
        """Inspect panel controls hierarchy for item name label and valid bindings.

        Args:
            controls: List of control descriptor dictionaries.

        Returns:
            Tuple of booleans indicating presence of label and valid binding.
        """
        has_label = False
        has_binding = False
        for wrapper in controls:
            for _, defn in wrapper.items():
                if defn.get("type") == "label":
                    has_label = True
                    for b in defn.get("bindings", []):
                        name = b.get("binding_name", "")
                        src = b.get("source_property_name", "")
                        if name == "#inventory_text_slice":
                            has_binding = True
                        elif "%.16s" in src and "*" in src:
                            has_binding = True
        return has_label, has_binding

    @classmethod
    def validate_hud_container_panel(
        cls,
        panel_schema: dict[str, Any],
        viewport: ViewportConfig,
    ) -> tuple[bool, list[str]]:
        """Validate JSON UI panel structure and bindings across target viewport.

        Args:
            panel_schema: Parsed dictionary of JSON UI panel hierarchy.
            viewport: Viewport scale constraints to check against.

        Returns:
            Tuple of boolean validity status and list of warning diagnostics.
        """
        warnings: list[str] = []
        if "hud_custom_container_root" not in panel_schema:
            warnings.append("Missing root control 'hud_custom_container_root'.")
            return False, warnings

        panel = panel_schema["hud_custom_container_root"]
        clipped = panel.get("allow_clipping", False) or panel.get("clip_children", False)

        if not clipped and viewport.mode == GuiScaleMode.POCKET:
            warnings.append(
                "Pocket scale requires 'clip_children: true' or "
                "'allow_clipping: true' to prevent viewport overflow."
            )

        controls = panel.get("controls", [])
        has_label, has_binding = cls._inspect_panel_controls(controls)

        if not has_label:
            warnings.append("Panel lacks item name label control.")
        if not has_binding:
            warnings.append("Panel lacks valid #inventory_text_slice binding.")

        return len(warnings) == 0, warnings
