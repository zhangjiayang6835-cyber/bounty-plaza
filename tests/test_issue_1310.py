"""Unit and integration test suite for Issue #1310."""

import json
from pathlib import Path
import pytest

from packages.bedrock_json_ui.json_ui_engine import (
    BindingExpressionEvaluator,
    BindingResolutionError,
    JsonUiEngine,
    ResponsiveProfile,
)
from packages.bedrock_json_ui.verifier import BedrockJsonUiVerifier


@pytest.fixture
def repo_root() -> Path:
    """Fixture providing the repository root path."""
    return Path(__file__).resolve().parent.parent


def test_binding_expression_evaluation_and_truncation():
    """Verifies that the evaluator enforces a 16-character string truncation bound."""
    evaluator = BindingExpressionEvaluator()
    expr = "('%.16s' * (#item_name - ('%.0s' * #item_name)))"

    assert evaluator.evaluate_slice(expr, "") == ""
    assert evaluator.evaluate_slice(expr, "diamond") == "diamond"
    assert evaluator.evaluate_slice(expr, "1234567890123456") == "1234567890123456"
    assert evaluator.evaluate_slice(expr, "12345678901234567") == "1234567890123456"
    assert evaluator.evaluate_slice(expr, "minecraft:golden_sword") == "golden_sword"

    long_input = "minecraft:netherite_upgrade_smithing_template_edition"
    truncated = evaluator.evaluate_slice(expr, long_input)
    assert len(truncated) == 16
    assert truncated == "netherite_upgrad"


def test_invalid_specifier_detection():
    """Verifies that unquoted format specifiers are detected and rejected."""
    evaluator = BindingExpressionEvaluator()

    with pytest.raises(BindingResolutionError) as exc_info:
        evaluator.validate_expression("%.16s")
    assert "invalid binding format specifier" in str(exc_info.value)

    with pytest.raises(BindingResolutionError):
        evaluator.evaluate_slice("%.16s", "test_item")


def test_json_ui_engine_responsive_layout():
    """Verifies layout dimensions and clipping across Desktop, Pocket, and Console profiles."""
    engine = JsonUiEngine()

    for profile in ResponsiveProfile:
        result = engine.render_inventory_slice("extremely_long_inventory_item_identifier", profile)
        assert result["overflow_prevented"] is True
        assert result["clips_children"] is True
        assert result["char_count"] <= 16
        assert len(result["displayed_text"]) <= 16


def test_json_ui_file_syntax_and_registration(repo_root: Path):
    """Verifies valid JSON structure and registration of hud_screen.json."""
    defs_path = repo_root / "ui" / "_ui_defs.json"
    hud_path = repo_root / "ui" / "hud_screen.json"

    assert defs_path.is_file()
    assert hud_path.is_file()

    defs_data = json.loads(defs_path.read_text(encoding="utf-8"))
    assert "ui/hud_screen.json" in defs_data.get("ui_defs", [])

    hud_data = json.loads(hud_path.read_text(encoding="utf-8"))
    assert hud_data.get("namespace") == "hud"
    assert "inventory_text_label" in hud_data
    assert "hud_custom_container_root" in hud_data

    root_panel = hud_data["hud_custom_container_root"]
    assert root_panel.get("clips_children") is True


def test_behavior_pack_manifest(repo_root: Path):
    """Verifies manifest format version and script module dependencies."""
    manifest_path = repo_root / "manifest.json"
    assert manifest_path.is_file()

    manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert manifest_data.get("format_version") == 2

    modules = manifest_data.get("modules", [])
    assert any(m.get("entry") == "scripts/main.js" for m in modules)

    dependencies = manifest_data.get("dependencies", [])
    assert any(d.get("module_name") == "@minecraft/server" for d in dependencies)


def test_verifier_formal_execution(repo_root: Path):
    """Verifies that all BedrockJsonUiVerifier checks execute successfully."""
    verifier = BedrockJsonUiVerifier()
    report = verifier.execute_all(repo_root)
    assert report.all_passed is True
    assert len(report.results) == 5
