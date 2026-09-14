"""Unit tests for Bedrock JSON UI dynamic text slicing and invariants (Issue #1319)."""

import pytest
from packages.json_ui_text_slicing.text_slicer import (
    BedrockJsonUiEngine,
    FormatSpecifier,
    GuiScaleMode,
)
from packages.json_ui_text_slicing.verifier import BedrockJsonUiVerifier


def test_ascii_truncation_over_16():
    """Verify strings longer than 16 characters truncate to 16 characters."""
    raw = "Enchanted_Netherite_Sword"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert len(res.sliced_text) == 16
    assert res.sliced_text == "Enchanted_Nether"
    assert res.was_truncated is True
    assert res.is_preserved is False
    assert res.utf8_safe is True
    assert len(res.warnings) == 0


def test_ascii_preservation_under_16():
    """Verify strings under 16 characters are preserved without modification."""
    raw = "Iron Ingot"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert res.sliced_text == "Iron Ingot"
    assert res.was_truncated is False
    assert res.is_preserved is True
    assert res.char_length == 10
    assert len(res.warnings) == 0


def test_ascii_preservation_exact_16():
    """Verify strings of exactly 16 characters are preserved without truncation."""
    raw = "1234567890123456"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert res.sliced_text == raw
    assert res.was_truncated is False
    assert res.is_preserved is True


def test_multibyte_utf8_cjk_preservation():
    """Verify multi-byte Chinese and Japanese characters are safely preserved and sliced."""
    raw = "钻石剑附加锋利五级耐久三级"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert res.utf8_safe is True
    assert len(res.sliced_text) <= 16
    assert res.sliced_text.encode("utf-8").decode("utf-8") == res.sliced_text


def test_accented_characters_utf8():
    """Verify accented European characters maintain UTF-8 integrity."""
    raw = "Épée_en_diamant_tranchante"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert res.utf8_safe is True
    assert len(res.sliced_text) == 16
    assert res.was_truncated is True


def test_bedrock_formatting_codes_preservation():
    """Verify section symbol formatting codes are preserved and visible text limited."""
    raw = "§aRare§r_§6Golden_Apple_Super"
    res = BedrockJsonUiEngine.slice_text(raw, max_chars=16)
    assert "§a" in res.sliced_text
    assert "§6" in res.sliced_text
    clean = BedrockJsonUiEngine.clean_format_codes(res.sliced_text)
    assert len(clean) == 16


def test_format_specifier_precision():
    """Verify format specifier precision truncation."""
    text = "abcdefghijklmnopq"
    formatted, warnings = FormatSpecifier.apply_format("%.16s", text)
    assert len(warnings) == 0
    assert len(formatted) == 16
    assert formatted == "abcdefghijklmnop"


def test_format_specifier_zero_check():
    """Verify format specifier zero-check for minimum length."""
    long_text = "1234567890123456"
    res_pass, _ = FormatSpecifier.apply_format("%016s", long_text)
    assert res_pass == long_text

    short_text = "short"
    res_fail, _ = FormatSpecifier.apply_format("%016s", short_text)
    assert res_fail == "0"


def test_format_specifier_padding():
    """Verify format specifier left-aligned space padding."""
    text = "item"
    padded, _ = FormatSpecifier.apply_format("%-8s", text)
    assert padded == "item    "
    assert len(padded) == 8


def test_binding_expression_evaluation_success():
    """Verify valid Bedrock JSON UI format expression resolution."""
    context = {"#inventory_text_raw": "Diamond_Chestplate_Protection_IV"}
    resolved, warnings = BedrockJsonUiEngine.evaluate_binding_expression(
        "('%.16s' * #inventory_text_raw)", context
    )
    assert len(warnings) == 0
    assert len(resolved) == 16
    assert resolved == "Diamond_Chestpla"


def test_invalid_format_specifier_error_caught():
    """Verify bare format specifier triggers diagnostic errors matching the engine."""
    context = {"#inventory_text": "Sample"}
    _, warnings = BedrockJsonUiEngine.evaluate_binding_expression("%.16s", context)
    assert len(warnings) == 2
    assert "Expression '%.16s' failed: invalid binding format specifier." in warnings[1]
    assert "Binding resolution failed for #inventory_text_slice" in warnings[0]


def test_hud_panel_validation_across_gui_scales():
    """Verify panel validation passes with zero client warnings on desktop, pocket, and console."""
    panel_schema = BedrockJsonUiVerifier.create_sample_panel()
    for mode in (GuiScaleMode.DESKTOP, GuiScaleMode.POCKET, GuiScaleMode.CONSOLE):
        viewport = BedrockJsonUiEngine.get_default_viewport(mode)
        valid, warnings = BedrockJsonUiEngine.validate_hud_container_panel(
            panel_schema, viewport
        )
        assert valid is True
        assert len(warnings) == 0


def test_verifier_report_all_invariants_pass():
    """Verify full suite of invariants through BedrockJsonUiVerifier."""
    panel_schema = BedrockJsonUiVerifier.create_sample_panel()
    report = BedrockJsonUiVerifier.run_all_checks(panel_schema)
    assert report.is_successful is True
    assert report.failed_checks == 0
    assert report.passed_checks == 6
    assert len(report.invariants_verified) == 6
