"""Invariant verification harness for Bedrock JSON UI text slicing."""

from dataclasses import dataclass
from typing import Any
from packages.json_ui_text_slicing.text_slicer import (
    BedrockJsonUiEngine,
    GuiScaleMode,
)


@dataclass
class VerificationReport:
    """Detailed invariant verification results for Bedrock JSON UI testing.

    Attributes:
        total_checks: Total number of invariant checks executed.
        passed_checks: Number of invariant checks successfully verified.
        failed_checks: Number of invariant checks failed.
        invariants_verified: List of identifiers for verified invariants.
        details: List of log messages detailing check execution.
    """

    total_checks: int
    passed_checks: int
    failed_checks: int
    invariants_verified: list[str]
    details: list[str]

    @property
    def is_successful(self) -> bool:
        """Indicate whether all invariants passed without error."""
        return self.failed_checks == 0 and self.passed_checks == self.total_checks


class BedrockJsonUiVerifier:
    """Verification suite enforcing strict Bedrock JSON UI runtime invariants."""

    @classmethod
    def create_sample_panel(cls) -> dict[str, Any]:
        """Construct reference Bedrock JSON UI HUD container panel hierarchy.

        Returns:
            Dictionary containing valid JSON UI panel schema.
        """
        panel_dict: dict[str, Any] = {
            "hud_custom_container_root": {
                "type": "panel",
                "allow_clipping": True,
                "clip_children": True,
                "size": ["100%", "100%"],
                "controls": [
                    {
                        "inventory_item_label": {
                            "type": "label",
                            "text": "#inventory_text_slice",
                            "bindings": [
                                {
                                    "binding_name": "#inventory_text",
                                    "binding_name_override": "#inventory_text_raw",
                                },
                                {
                                    "binding_type": "view",
                                    "source_property_name": "('%.16s' * #inventory_text_raw)",
                                    "target_property_name": "#inventory_text_slice",
                                },
                            ],
                        }
                    }
                ],
            }
        }
        return panel_dict

    @classmethod
    def _verify_ascii_truncation(cls, details: list[str]) -> bool:
        """Verify 16-character string truncation for ASCII identifiers.

        Args:
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        raw_name = "Netherite_Pickaxe_Unbreaking_III"
        res = BedrockJsonUiEngine.slice_text(raw_name, max_chars=16)
        if len(res.sliced_text) != 16:
            details.append(f"Invariant 1 failed: Expected length 16, got {len(res.sliced_text)}")
            return False
        if not res.was_truncated:
            details.append("Invariant 1 failed: Truncation flag not set.")
            return False
        details.append("Invariant 1 passed: 16-character ASCII truncation verified.")
        return True

    @classmethod
    def _verify_text_preservation(cls, details: list[str]) -> bool:
        """Verify strings under 16 characters are preserved without modification.

        Args:
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        short_names = ("Iron Sword", "Golden Apple", "Compass", "Bow")
        for name in short_names:
            res = BedrockJsonUiEngine.slice_text(name, max_chars=16)
            if res.sliced_text != name:
                details.append(f"Invariant 2 failed: Mismatch on '{name}'.")
                return False
            if not res.is_preserved or res.was_truncated:
                details.append(f"Invariant 2 failed: Preservation flag error on '{name}'.")
                return False
        details.append("Invariant 2 passed: Text preservation verified for <= 16 chars.")
        return True

    @classmethod
    def _verify_utf8_integrity(cls, details: list[str]) -> bool:
        """Verify multi-byte UTF-8 codepoints are not fragmented during slicing.

        Args:
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        test_strings = (
            "钻石剑附加锋利五级耐久三级",
            "Épée_en_diamant_tranchante",
            "§6Super_Legendary_Blade",
        )
        for text in test_strings:
            res = BedrockJsonUiEngine.slice_text(text, max_chars=16)
            if not res.utf8_safe:
                details.append(f"Invariant 3 failed: UTF-8 split detected in '{text}'.")
                return False
            try:
                res.sliced_text.encode("utf-8").decode("utf-8")
            except UnicodeError:
                details.append(f"Invariant 3 failed: Unicode decode error in '{text}'.")
                return False
        details.append("Invariant 3 passed: Multi-byte UTF-8 integrity verified.")
        return True

    @classmethod
    def _verify_formatting_codes(cls, details: list[str]) -> bool:
        """Verify Bedrock section symbol formatting codes are preserved.

        Args:
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        formatted_name = "§6Golden_Armor_Piece§r"
        res = BedrockJsonUiEngine.slice_text(formatted_name, max_chars=16)
        if "§6" not in res.sliced_text:
            details.append("Invariant 4 failed: Lost initial color code.")
            return False
        clean_len = len(BedrockJsonUiEngine.clean_format_codes(res.sliced_text))
        if clean_len > 16:
            details.append(f"Invariant 4 failed: Visible length {clean_len} > 16.")
            return False
        details.append("Invariant 4 passed: Bedrock formatting codes preserved.")
        return True

    @classmethod
    def _verify_binding_resolution(cls, details: list[str]) -> bool:
        """Verify Bedrock JSON UI format expression evaluation and warning detection.

        Args:
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        ctx = {"#inventory_text_raw": "Enchanted_Golden_Apple_Stack"}
        resolved, warnings = BedrockJsonUiEngine.evaluate_binding_expression(
            "('%.16s' * #inventory_text_raw)", ctx
        )
        if len(warnings) != 0 or len(resolved) > 16:
            details.append("Invariant 5 failed: Binding expression resolution failed.")
            return False

        _, bad_warnings = BedrockJsonUiEngine.evaluate_binding_expression("%.16s", ctx)
        if len(bad_warnings) != 2:
            details.append("Invariant 5 failed: Invalid bare format specifier not caught.")
            return False
        details.append("Invariant 5 passed: JSON UI binding resolution verified.")
        return True

    @classmethod
    def _verify_cross_scale_hud(
        cls, panel_schema: dict[str, Any], details: list[str]
    ) -> bool:
        """Verify zero client warnings across Desktop, Pocket, and Console GUI scales.

        Args:
            panel_schema: Parsed panel dictionary.
            details: List of log messages to append to.

        Returns:
            True if all assertions pass, False otherwise.
        """
        for mode in (GuiScaleMode.DESKTOP, GuiScaleMode.POCKET, GuiScaleMode.CONSOLE):
            vp = BedrockJsonUiEngine.get_default_viewport(mode)
            valid, warnings = BedrockJsonUiEngine.validate_hud_container_panel(panel_schema, vp)
            if not valid or len(warnings) > 0:
                details.append(f"Invariant 6 failed on {mode.value}: {warnings}")
                return False
        details.append("Invariant 6 passed: Zero client warnings across all GUI scales.")
        return True

    @classmethod
    def run_all_checks(cls, sample_panel: dict[str, Any]) -> VerificationReport:
        """Execute full invariant test harness and produce verification report.

        Args:
            sample_panel: JSON UI schema definition for container HUD panel.

        Returns:
            VerificationReport instance.
        """
        details: list[str] = []
        passed = 0
        total = 6

        checks = (
            ("INV_1_ASCII_TRUNCATION", cls._verify_ascii_truncation),
            ("INV_2_TEXT_PRESERVATION", cls._verify_text_preservation),
            ("INV_3_UTF8_INTEGRITY", cls._verify_utf8_integrity),
            ("INV_4_FORMATTING_CODES", cls._verify_formatting_codes),
            ("INV_5_BINDING_RESOLUTION", cls._verify_binding_resolution),
        )

        verified_invariants: list[str] = []
        for inv_name, check_func in checks:
            if check_func(details):
                passed += 1
                verified_invariants.append(inv_name)

        if cls._verify_cross_scale_hud(sample_panel, details):
            passed += 1
            verified_invariants.append("INV_6_CROSS_SCALE_HUD")

        failed = total - passed
        return VerificationReport(
            total_checks=total,
            passed_checks=passed,
            failed_checks=failed,
            invariants_verified=verified_invariants,
            details=details,
        )
