"""Bedrock JSON UI simulation, expression evaluation, and responsive layout engine."""

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional


class ResponsiveProfile(Enum):
    """Supported GUI layout profiles for Bedrock JSON UI."""

    DESKTOP = "desktop"
    POCKET = "pocket"
    CONSOLE = "console"


class BindingResolutionError(Exception):
    """Exception raised when JSON UI engine fails to resolve expression binding."""


@dataclass(frozen=True)
class HudContainerDimensions:
    """Dimensions and positioning bounds for HUD container panels."""

    profile: ResponsiveProfile
    width: int
    height: int
    offset_y: int
    clips_children: bool


class BindingExpressionEvaluator:
    """Evaluates Bedrock JSON UI view binding expressions and text slicing operations."""

    INVALID_SPECIFIER_PATTERN = re.compile(r"(?<!['\"])%\.\d+s(?!['\"])")
    QUOTED_SLICE_PATTERN = re.compile(r"'%\.([0-9]+)s'")

    def validate_expression(self, expression: str) -> None:
        """Validates that expression does not use invalid unquoted format specifiers.

        Args:
            expression: View binding expression string to validate.

        Raises:
            BindingResolutionError: If unquoted format specifiers or syntax errors are detected.
        """
        if not expression:
            raise BindingResolutionError("Empty binding expression")

        match = self.INVALID_SPECIFIER_PATTERN.search(expression)
        if match:
            spec = match.group(0)
            raise BindingResolutionError(
                f"Expression '{spec}' failed: invalid binding format specifier in target namespace"
            )

    def extract_max_slice_length(self, expression: str, default: int = 16) -> int:
        """Extracts the slice length specified in the format binding expression.

        Args:
            expression: Binding source property expression.
            default: Fallback length if pattern not explicitly specified.

        Returns:
            Integer maximum slice length.
        """
        match = self.QUOTED_SLICE_PATTERN.search(expression)
        if match:
            return int(match.group(1))
        return default

    def evaluate_slice(self, expression: str, raw_text: str) -> str:
        """Evaluates string slicing on raw text according to JSON UI binding rules.

        Args:
            expression: Binding source property expression.
            raw_text: Source string from item name or inventory property.

        Returns:
            Sliced string meeting bounds and formatting constraints.
        """
        self.validate_expression(expression)
        max_length = self.extract_max_slice_length(expression)

        clean_text = raw_text
        prefix = "minecraft:"
        if clean_text.startswith(prefix):
            clean_text = clean_text[len(prefix):]

        if len(clean_text) <= max_length:
            return clean_text
        return clean_text[:max_length]


class JsonUiEngine:
    """Engine simulating Bedrock JSON UI panel layouts, responsive bindings, and HUD rendering."""

    def __init__(self, evaluator: Optional[BindingExpressionEvaluator] = None) -> None:
        """Initializes the JSON UI engine.

        Args:
            evaluator: Optional custom binding expression evaluator.
        """
        self.evaluator = evaluator if evaluator is not None else BindingExpressionEvaluator()

    def load_json_file(self, path: Path) -> Dict[str, Any]:
        """Loads and parses a JSON UI document.

        Args:
            path: Path to target JSON file.

        Returns:
            Parsed JSON dictionary.

        Raises:
            FileNotFoundError: If target path does not exist.
            ValueError: If file content is not valid JSON.
        """
        if not path.is_file():
            raise FileNotFoundError(f"JSON UI file not found: {path}")

        raw_content = path.read_text(encoding="utf-8")
        parsed = json.loads(raw_content)
        if not isinstance(parsed, dict):
            raise ValueError(f"Root of JSON UI document must be an object: {path}")
        return parsed

    def get_profile_layout(self, profile: ResponsiveProfile) -> HudContainerDimensions:
        """Resolves container panel dimensions and offsets for a specific GUI profile.

        Args:
            profile: Target responsive GUI profile.

        Returns:
            HudContainerDimensions specifying layout metrics.
        """
        if profile == ResponsiveProfile.DESKTOP:
            return HudContainerDimensions(
                profile=profile,
                width=128,
                height=16,
                offset_y=-42,
                clips_children=True,
            )
        if profile == ResponsiveProfile.POCKET:
            return HudContainerDimensions(
                profile=profile,
                width=96,
                height=14,
                offset_y=-56,
                clips_children=True,
            )
        return HudContainerDimensions(
            profile=profile,
            width=144,
            height=18,
            offset_y=-48,
            clips_children=True,
        )

    def render_inventory_slice(
        self,
        item_name: str,
        profile: ResponsiveProfile,
        expression: str = "('%.16s' * (#item_name - ('%.0s' * #item_name)))",
    ) -> Dict[str, Any]:
        """Renders an inventory item name projection across a specific profile.

        Args:
            item_name: Raw item identifier or custom name tag.
            profile: Target GUI scale profile.
            expression: JSON UI binding expression.

        Returns:
            Dictionary containing rendered text, dimensions, and viewport status.
        """
        sliced_text = self.evaluator.evaluate_slice(expression, item_name)
        layout = self.get_profile_layout(profile)

        return {
            "displayed_text": sliced_text,
            "char_count": len(sliced_text),
            "profile": profile.value,
            "width": layout.width,
            "height": layout.height,
            "offset_y": layout.offset_y,
            "clips_children": layout.clips_children,
            "overflow_prevented": len(sliced_text) <= 16,
        }

    def validate_hud_screen_definition(self, data: Dict[str, Any]) -> List[str]:
        """Validates that a hud_screen.json structure complies with acceptance criteria.

        Args:
            data: Parsed hud_screen.json dictionary.

        Returns:
            List of detected structural or semantic warnings/errors.
        """
        issues: List[str] = []

        if data.get("namespace") != "hud":
            issues.append("Namespace must be 'hud'")

        label = data.get("inventory_text_label")
        if not isinstance(label, dict):
            issues.append("Missing 'inventory_text_label' definition")
        else:
            if not label.get("allow_clipping"):
                issues.append("inventory_text_label must have allow_clipping set to true")
            bindings = label.get("bindings", [])
            has_slice = any(
                isinstance(b, dict) and b.get("target_property_name") == "#inventory_text_slice"
                for b in bindings
            )
            if not has_slice:
                issues.append("Missing binding for target property #inventory_text_slice")

        root = data.get("hud_custom_container_root")
        if not isinstance(root, dict):
            issues.append("Missing 'hud_custom_container_root' definition")
        else:
            if not root.get("clips_children"):
                issues.append("hud_custom_container_root must have clips_children set to true")

        return issues
