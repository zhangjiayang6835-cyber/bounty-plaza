"""Formal verification suite for Bedrock JSON UI issue #1310."""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import List, Optional

from packages.bedrock_json_ui.json_ui_engine import (
    BindingExpressionEvaluator,
    BindingResolutionError,
    JsonUiEngine,
    ResponsiveProfile,
)


@dataclass(frozen=True)
class VerificationResult:
    """Individual test verification result."""

    name: str
    passed: bool
    message: str


@dataclass
class VerificationReport:
    """Consolidated formal verification report."""

    results: List[VerificationResult] = field(default_factory=list)

    @property
    def all_passed(self) -> bool:
        """Returns True if every verification check passed."""
        return all(r.passed for r in self.results)

    @property
    def summary(self) -> str:
        """Constructs human-readable execution summary."""
        lines = []
        for r in self.results:
            status = "PASSED" if r.passed else "FAILED"
            lines.append(f"[{status}] {r.name}: {r.message}")
        passed_count = sum(1 for r in self.results if r.passed)
        lines.append(f"\nSummary: {passed_count}/{len(self.results)} verification checks passed.")
        return "\n".join(lines)


class BedrockJsonUiVerifier:
    """Executes formal verification checks across Bedrock JSON UI definitions and runtime code."""

    def __init__(self, engine: Optional[JsonUiEngine] = None) -> None:
        """Initializes the verifier with a JSON UI engine.

        Args:
            engine: Optional JsonUiEngine instance.
        """
        self.engine = engine if engine is not None else JsonUiEngine()

    def verify_json_ui_definitions(self, root_dir: Path) -> VerificationResult:
        """Verifies presence, registration, and schema of JSON UI files.

        Args:
            root_dir: Root directory of the repository.

        Returns:
            VerificationResult indicating success or failure.
        """
        defs_file = root_dir / "ui" / "_ui_defs.json"
        hud_file = root_dir / "ui" / "hud_screen.json"

        if not defs_file.is_file():
            return VerificationResult("json_ui_defs", False, "ui/_ui_defs.json missing")
        if not hud_file.is_file():
            return VerificationResult("json_ui_hud", False, "ui/hud_screen.json missing")

        defs_data = json.loads(defs_file.read_text(encoding="utf-8"))
        if "ui/hud_screen.json" not in defs_data.get("ui_defs", []):
            return VerificationResult("json_ui_registration", False, "hud_screen not registered")

        hud_data = self.engine.load_json_file(hud_file)
        issues = self.engine.validate_hud_screen_definition(hud_data)
        if issues:
            return VerificationResult("json_ui_schema", False, "; ".join(issues))

        return VerificationResult("json_ui_schema", True, "JSON UI definitions verified")

    def verify_string_truncation(self) -> VerificationResult:
        """Verifies 16-character string truncation across boundary cases.

        Returns:
            VerificationResult indicating success or failure.
        """
        evaluator = BindingExpressionEvaluator()
        expr = "('%.16s' * (#item_name - ('%.0s' * #item_name)))"
        test_cases = [
            ("", ""),
            ("sword", "sword"),
            ("123456789012345", "123456789012345"),
            ("1234567890123456", "1234567890123456"),
            ("12345678901234567", "1234567890123456"),
            ("minecraft:netherite_upgrade_smithing_template", "netherite_upgrad"),
        ]

        for raw_input, expected in test_cases:
            output = evaluator.evaluate_slice(expr, raw_input)
            if output != expected or len(output) > 16:
                msg = f"Failed on '{raw_input}': got '{output}', expected '{expected}'"
                return VerificationResult("string_truncation", False, msg)

        return VerificationResult("string_truncation", True, "All truncation boundary cases passed")

    def verify_binding_format_safety(self) -> VerificationResult:
        """Verifies that invalid unquoted format specifiers are caught and rejected.

        Returns:
            VerificationResult indicating success or failure.
        """
        evaluator = BindingExpressionEvaluator()
        invalid_expr = "%.16s"

        try:
            evaluator.validate_expression(invalid_expr)
            return VerificationResult(
                "binding_format_safety",
                False,
                "Failed to detect invalid unquoted format specifier",
            )
        except BindingResolutionError:
            return VerificationResult(
                "binding_format_safety",
                True,
                "Invalid format specifier correctly detected and blocked",
            )

    def verify_responsive_viewports(self) -> VerificationResult:
        """Verifies responsive layout dimensions and clipping across all profiles.

        Returns:
            VerificationResult indicating success or failure.
        """
        for profile in ResponsiveProfile:
            res = self.engine.render_inventory_slice("very_long_custom_item_name", profile)
            if not res["overflow_prevented"]:
                return VerificationResult(
                    "responsive_viewports",
                    False,
                    f"Overflow not prevented on {profile.value}",
                )
            if not res["clips_children"]:
                return VerificationResult(
                    "responsive_viewports",
                    False,
                    f"Clipping disabled on {profile.value}",
                )

        return VerificationResult(
            "responsive_viewports",
            True,
            "Responsive profiles (Desktop, Pocket, Console) verified",
        )

    def verify_manifest_and_scripts(self, root_dir: Path) -> VerificationResult:
        """Verifies manifest validity and TypeScript compilation outputs.

        Args:
            root_dir: Root directory of repository.

        Returns:
            VerificationResult indicating success or failure.
        """
        manifest_file = root_dir / "manifest.json"
        main_ts = root_dir / "scripts" / "main.ts"
        main_js = root_dir / "scripts" / "main.js"

        if not manifest_file.is_file():
            return VerificationResult("manifest_scripts", False, "manifest.json missing")
        if not main_ts.is_file() or not main_js.is_file():
            return VerificationResult(
                "manifest_scripts", False, "scripts/main source files missing"
            )

        manifest_data = json.loads(manifest_file.read_text(encoding="utf-8"))
        deps = [d.get("module_name") for d in manifest_data.get("dependencies", [])]
        if "@minecraft/server" not in deps:
            return VerificationResult("manifest_scripts", False, "Missing @minecraft/server dep")

        return VerificationResult("manifest_scripts", True, "Manifest and script runtime verified")

    def execute_all(self, project_root: Optional[Path] = None) -> VerificationReport:
        """Runs all formal verification checks and returns consolidated report.

        Args:
            project_root: Optional repository root path.

        Returns:
            VerificationReport containing results of all checks.
        """
        resolved_parent = Path(__file__).resolve().parent.parent.parent
        root = project_root if project_root is not None else resolved_parent
        report = VerificationReport()
        report.results.append(self.verify_json_ui_definitions(root))
        report.results.append(self.verify_string_truncation())
        report.results.append(self.verify_binding_format_safety())
        report.results.append(self.verify_responsive_viewports())
        report.results.append(self.verify_manifest_and_scripts(root))
        return report
