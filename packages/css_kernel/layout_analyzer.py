"""Layout analyzer and centering verification engine for CSS stylesheets."""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from packages.css_kernel.compiler import CssRule


@dataclass(frozen=True)
class CenteringVerificationResult:
    """Encapsulates centering and zero-allocation containment evaluation."""

    selector: str
    horizontal_centered: bool
    vertical_centered: bool
    layout_isolated: bool
    hardware_composited: bool
    display_model: Optional[str]

    @property
    def fully_centered(self) -> bool:
        """Verify whether both axes are centered."""
        return self.horizontal_centered and self.vertical_centered

    @property
    def zero_allocation_compliant(self) -> bool:
        """Verify whether element eliminates layout thrash reallocations."""
        return self.fully_centered and self.layout_isolated


class LayoutAnalyzer:
    """Analyzes CSS rules for horizontal, vertical, and zero-allocation properties."""

    @staticmethod
    def _check_grid_axes(decls: Dict[str, str]) -> Tuple[bool, bool]:
        """Check horizontal and vertical centering for CSS Grid layouts."""
        place_items = decls.get("place-items")
        place_content = decls.get("place-content")
        justify_items = decls.get("justify-items")
        align_items = decls.get("align-items")

        h_center = False
        v_center = False

        if place_items == "center" or place_content == "center":
            h_center = True
            v_center = True
        if justify_items == "center":
            h_center = True
        if align_items == "center":
            v_center = True

        return h_center, v_center

    @staticmethod
    def _check_flex_axes(decls: Dict[str, str]) -> Tuple[bool, bool]:
        """Check horizontal and vertical centering for CSS Flexbox layouts."""
        justify_content = decls.get("justify-content")
        align_items = decls.get("align-items")
        h_center = justify_content == "center"
        v_center = align_items == "center"
        return h_center, v_center

    @staticmethod
    def _check_positioned_axes(decls: Dict[str, str]) -> Tuple[bool, bool]:
        """Check horizontal and vertical centering for positioned elements."""
        position = decls.get("position")
        if position not in ("absolute", "fixed"):
            return False, False

        inset = decls.get("inset")
        margin = decls.get("margin")
        top = decls.get("top")
        left = decls.get("left")
        transform = decls.get("transform")

        if inset == "0" and margin == "auto":
            return True, True
        if top == "50%" and left == "50%" and transform and "translate" in transform:
            return True, True

        return False, False

    @classmethod
    def evaluate_rule(cls, rule: CssRule) -> CenteringVerificationResult:
        """Evaluate a CSS rule for bidirectional centering and memory containment."""
        decls = rule.declarations
        display = decls.get("display")

        horizontal = False
        vertical = False

        if display == "grid":
            horizontal, vertical = cls._check_grid_axes(decls)
        elif display == "flex":
            horizontal, vertical = cls._check_flex_axes(decls)

        if not (horizontal and vertical):
            pos_h, pos_v = cls._check_positioned_axes(decls)
            horizontal = horizontal or pos_h
            vertical = vertical or pos_v

        contain = decls.get("contain", "")
        layout_isolated = "layout" in contain and "paint" in contain

        will_change = decls.get("will-change", "")
        hardware_composited = "transform" in will_change or "opacity" in will_change

        return CenteringVerificationResult(
            selector=rule.selector,
            horizontal_centered=horizontal,
            vertical_centered=vertical,
            layout_isolated=layout_isolated,
            hardware_composited=hardware_composited,
            display_model=display,
        )

    @classmethod
    def analyze_all(cls, rules: List[CssRule]) -> List[CenteringVerificationResult]:
        """Analyze a collection of CSS rules and return evaluation results."""
        return [cls.evaluate_rule(rule) for rule in rules]
