"""
Comprehensive test suite for Issue #1560: Hello World multilingual engine.
"""

import json
import subprocess
import sys
from decimal import Decimal
from pathlib import Path
import pytest

from packages.omni_hello_world import (
    DEFAULT_LANGUAGE,
    DEFAULT_PUNCTUATION,
    DEFAULT_TARGET,
    FORMATS,
    FormatType,
    HelloWorld,
    calculate_settlement,
    greet,
)
from packages.omni_hello_world.settlement import (
    EVM_PAYOUT_ADDRESS,
    STELLAR_PAYOUT_ADDRESS,
    determine_contributor_ratio,
    format_settlement_summary,
)


class TestHelloWorldEngine:
    """Tests covering greeting creation, customization, and formatting."""

    def test_default_greeting(self) -> None:
        """Verify default greeting returns standard text."""
        engine = HelloWorld()
        result = engine.greet()
        assert result == "Hello, World!"

    def test_top_level_convenience_function(self) -> None:
        """Verify top-level greet helper behaves identically."""
        result = greet()
        assert result == "Hello, World!"

    def test_custom_target(self) -> None:
        """Verify personalized target interpolation."""
        result = greet(target="OmniBlocks")
        assert result == "Hello, OmniBlocks!"

    def test_shout_mode(self) -> None:
        """Verify uppercase transformation under shout mode."""
        result = greet(target="BountyPlaza", shout=True)
        assert result == "HELLO, BOUNTYPLAZA!"

    def test_custom_punctuation(self) -> None:
        """Verify custom punctuation mark replacement."""
        result = greet(target="Builder", punctuation="?")
        assert result == "Hello, Builder?"

    def test_multilingual_chinese(self) -> None:
        """Verify Chinese greeting generation."""
        result = greet(language="zh", target="世界")
        assert result == "你好, 世界!"

    def test_multilingual_spanish(self) -> None:
        """Verify Spanish greeting generation."""
        result = greet(language="es", target="Mundo")
        assert result == "Hola, Mundo!"

    def test_multilingual_french(self) -> None:
        """Verify French greeting generation."""
        result = greet(language="fr", target="Monde")
        assert result == "Bonjour, Monde!"

    def test_multilingual_japanese(self) -> None:
        """Verify Japanese greeting generation."""
        result = greet(language="ja", target="世界")
        assert result == "こんにちは, 世界!"

    def test_multilingual_german(self) -> None:
        """Verify German greeting generation."""
        result = greet(language="de", target="Welt")
        assert result == "Hallo, Welt!"

    def test_fallback_unknown_language(self) -> None:
        """Verify fallback to English when code is unrecognized."""
        result = greet(language="unknown_xyz")
        assert result == "Hello, World!"

    def test_language_registration(self) -> None:
        """Verify dynamic addition of unsupported languages."""
        engine = HelloWorld()
        engine.register_language("eo", "Saluton")
        result = engine.greet(language="eo", target="Mondo")
        assert result == "Saluton, Mondo!"

    def test_register_language_validation(self) -> None:
        """Verify rejection of invalid language codes and greetings."""
        engine = HelloWorld()
        with pytest.raises(TypeError):
            engine.register_language("", "Test")
        with pytest.raises(TypeError):
            engine.register_language("eo", "")

    def test_supported_languages_list(self) -> None:
        """Verify supported languages catalog."""
        engine = HelloWorld()
        langs = engine.get_supported_languages()
        assert "en" in langs
        assert "zh" in langs
        assert "es" in langs
        assert "fr" in langs
        assert "ja" in langs

    def test_json_format_output(self) -> None:
        """Verify structured JSON serialization."""
        raw = greet(target="Developer", format_type=FormatType.JSON.value)
        parsed = json.loads(raw)
        assert parsed["greeting"] == "Hello"
        assert parsed["target"] == "Developer"
        assert parsed["message"] == "Hello, Developer!"
        assert parsed["language"] == "en"
        assert parsed["shout"] is False

    def test_markdown_format_output(self) -> None:
        """Verify Markdown header serialization."""
        result = greet(target="GitHub", format_type=FormatType.MARKDOWN.value)
        assert result == "# Hello, GitHub!"

    def test_html_format_output(self) -> None:
        """Verify HTML element serialization."""
        result = greet(target="Web", format_type=FormatType.HTML.value)
        assert result == '<div class="greeting"><h1>Hello, Web!</h1></div>'

    def test_ansi_format_output(self) -> None:
        """Verify ANSI color codes in output."""
        result = greet(target="Terminal", format_type=FormatType.ANSI.value)
        assert result.startswith("\x1b[1;32m")
        assert result.endswith("\x1b[0m")

    def test_ascii_banner_output(self) -> None:
        """Verify ASCII box banner layout."""
        banner = greet(target="Banner", format_type=FormatType.ASCII_BANNER.value)
        lines = banner.split("\n")
        assert len(lines) == 5
        assert lines[0].startswith("+")
        assert lines[0].endswith("+")
        assert "Hello, Banner!" in lines[2]

    def test_greeting_result_dataclass_methods(self) -> None:
        """Verify GreetingResult helper serialization methods."""
        engine = HelloWorld()
        res = engine.generate(target="Unit")
        d = res.to_dict()
        assert d["target"] == "Unit"
        parsed = json.loads(res.to_json())
        assert parsed["message"] == "Hello, Unit!"


class TestBountySettlement:
    """Tests covering REWARD_POLICY financial mechanics and address retention."""

    def test_issue_1560_settlement(self) -> None:
        """Verify financial calculation for $100 nominal bounty in Issue #1560."""
        settlement = calculate_settlement(Decimal("100.00"))
        assert settlement.nominal_usd == Decimal("100.00")
        assert settlement.total_coins == Decimal("125.00")
        assert settlement.contributor_ratio == Decimal("0.92")
        assert settlement.contributor_coins == Decimal("115.00")
        assert settlement.cash_payout_usd == Decimal("82.80")
        assert settlement.platform_cut_usd == Decimal("17.20")
        assert settlement.evm_address == EVM_PAYOUT_ADDRESS
        assert settlement.stellar_address == STELLAR_PAYOUT_ADDRESS

    def test_settlement_brackets(self) -> None:
        """Verify tiered contributor ratios across multiple bounty thresholds."""
        assert determine_contributor_ratio(Decimal("30.00")) == Decimal("0.95")
        assert determine_contributor_ratio(Decimal("100.00")) == Decimal("0.92")
        assert determine_contributor_ratio(Decimal("350.00")) == Decimal("0.90")
        assert determine_contributor_ratio(Decimal("750.00")) == Decimal("0.87")
        assert determine_contributor_ratio(Decimal("2000.00")) == Decimal("0.85")

    def test_settlement_summary_format(self) -> None:
        """Verify summary formatting tuple generation."""
        settlement = calculate_settlement(Decimal("100.00"))
        nom, coins, c_coins, cash = format_settlement_summary(settlement)
        assert nom == "$100.00"
        assert coins == "125.00 coins"
        assert c_coins == "115.00 coins"
        assert cash == "$82.80"


class TestNodeParity:
    """Tests ensuring JavaScript runtime outputs match specifications."""

    def test_node_entrypoint_stdout(self) -> None:
        """Verify executing node hello_world.js prints Hello, World!"""
        repo_root = Path(__file__).resolve().parent.parent
        js_file = repo_root / "hello_world.js"
        cmd = ["node", str(js_file)]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert res.stdout.strip() == "Hello, World!"

    def test_node_entrypoint_multilingual(self) -> None:
        """Verify executing node hello_world.js with language arguments."""
        repo_root = Path(__file__).resolve().parent.parent
        js_file = repo_root / "hello_world.js"
        cmd = ["node", str(js_file), "--lang", "zh", "--target", "世界"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        assert res.stdout.strip() == "你好, 世界!"

    def test_node_entrypoint_json_flag(self) -> None:
        """Verify executing node hello_world.js with --json argument."""
        repo_root = Path(__file__).resolve().parent.parent
        js_file = repo_root / "hello_world.js"
        cmd = ["node", str(js_file), "--json"]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        data = json.loads(res.stdout)
        assert data["message"] == "Hello, World!"
