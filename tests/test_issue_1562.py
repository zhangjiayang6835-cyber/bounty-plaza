"""Pytest verification suite for OmniBlocks SASS mode (Issue #1562)."""

from decimal import Decimal
import pytest
from packages.omni_sass import (
    EscrowCalculation,
    OmniBlocksThemeEngine,
    OmniSaasManager,
    OmniSassManager,
    OutputStyle,
    SassCompiler,
    StyleSanitizer,
    ThemeConfig,
    WorkspaceMode,
)


class TestSassCompiler:
    """Validates SCSS lexing, parsing, and CSS compilation behaviors."""

    def test_variable_resolution(self):
        """Verify variable substitution and override precedence."""
        compiler = SassCompiler()
        source = """
        $primary-color: #3b82f6;
        .banner {
          background-color: $primary-color;
        }
        """
        output = compiler.compile(source)
        assert ".banner {" in output
        assert "background-color: #3b82f6;" in output

    def test_default_variable_precedence(self):
        """Verify that !default does not overwrite existing variable declarations."""
        compiler = SassCompiler()
        source = """
        $theme-font: Helvetica;
        $theme-font: Arial !default;
        body {
          font-family: $theme-font;
        }
        """
        output = compiler.compile(source)
        assert "font-family: Helvetica;" in output

    def test_nested_selector_expansion(self):
        """Verify recursive nesting and parent reference resolution with &."""
        compiler = SassCompiler()
        source = """
        .card {
          padding: 16px;
          &:hover {
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
          }
          .title {
            font-size: 1.25rem;
          }
        }
        """
        output = compiler.compile(source)
        assert ".card {" in output
        assert ".card:hover {" in output
        assert ".card .title {" in output

    def test_comma_separated_selector_nesting(self):
        """Verify combinator permutation across multiple selectors."""
        compiler = SassCompiler()
        source = """
        h1, h2 {
          color: #111827;
          &:hover {
            color: #2563eb;
          }
        }
        """
        output = compiler.compile(source)
        assert "h1:hover, h2:hover {" in output

    def test_mixin_definition_and_inclusion(self):
        """Verify reusable mixins with argument defaults."""
        compiler = SassCompiler()
        source = """
        @mixin flex-center($direction: row) {
          display: flex;
          align-items: center;
          justify-content: center;
          flex-direction: $direction;
        }
        .container {
          @include flex-center(column);
        }
        """
        output = compiler.compile(source)
        assert "display: flex;" in output
        assert "align-items: center;" in output
        assert "flex-direction: column;" in output

    def test_built_in_color_lighten_and_darken(self):
        """Verify lighten and darken color functions."""
        compiler = SassCompiler()
        source = """
        .theme {
          color: lighten(#000000, 20%);
          background: darken(#ffffff, 20%);
        }
        """
        output = compiler.compile(source)
        assert "color: #333333;" in output
        assert "background: #cccccc;" in output

    def test_built_in_color_mix(self):
        """Verify color mixing calculation."""
        compiler = SassCompiler()
        source = """
        .badge {
          background-color: mix(#000000, #ffffff, 50%);
        }
        """
        output = compiler.compile(source)
        assert "background-color: #7f7f7f;" in output

    def test_compressed_output_style(self):
        """Verify minified CSS generation under COMPRESSED style."""
        compiler = SassCompiler()
        source = """
        .widget {
          margin: 0;
          padding: 0;
        }
        """
        output = compiler.compile(source, style=OutputStyle.COMPRESSED)
        assert output == ".widget{margin:0;padding:0}"


class TestStyleSanitizer:
    """Validates detection and elimination of dangerous CSS injection vectors."""

    def test_detect_expression_injection(self):
        """Ensure CSS expression execution is detected."""
        sanitizer = StyleSanitizer()
        payload = ".exploit { width: expression(alert('xss')); }"
        violations = sanitizer.findViolations(payload) if hasattr(sanitizer, 'findViolations') else sanitizer.find_violations(payload)
        assert len(violations) > 0
        assert not sanitizer.is_safe(payload)

    def test_detect_javascript_pseudo_protocol(self):
        """Ensure javascript: pseudo-protocol is flagged."""
        sanitizer = StyleSanitizer()
        payload = "a { background-image: url('javascript:alert(1)'); }"
        violations = sanitizer.find_violations(payload)
        assert any("Inline JavaScript" in v for v in violations)

    def test_detect_unauthorized_external_urls(self):
        """Ensure external URLs outside whitelist are identified."""
        sanitizer = StyleSanitizer(allowed_domains=["https://cdn.omniblocks.io"])
        payload = "div { background: url('https://attacker.com/leak.png'); }"
        violations = sanitizer.find_violations(payload)
        assert any("Unauthorized external URL" in v for v in violations)

    def test_sanitize_neutralizes_vectors(self):
        """Ensure sanitize transforms dangerous patterns into blocked comments."""
        sanitizer = StyleSanitizer()
        payload = ".box { width: expression(doEvil()); }"
        cleaned = sanitizer.sanitize(payload)
        assert "expression(" not in cleaned
        assert "/* blocked_vector */" in cleaned


class TestOmniBlocksThemeEngine:
    """Validates Blockly SVG theme construction and preset compilation."""

    def test_get_all_standard_presets(self):
        """Verify standard presets exist and have valid structure."""
        engine = OmniBlocksThemeEngine()
        for name in ("default", "dark", "high_contrast", "cyber_neon"):
            preset = engine.get_preset(name)
            assert isinstance(preset, ThemeConfig)
            assert preset.primary_color.startswith("#")

    def test_unknown_preset_raises_key_error(self):
        """Verify unknown preset names raise KeyError."""
        engine = OmniBlocksThemeEngine()
        with pytest.raises(KeyError):
            engine.get_preset("non_existent_preset")

    def test_compile_theme_targets_blockly_svg(self):
        """Verify compiled theme generates classes for Blockly components."""
        engine = OmniBlocksThemeEngine()
        preset = engine.get_preset("dark")
        compiled = engine.compile_theme(preset)
        assert ".blocklySvg {" in compiled
        assert ".blocklySvg .blocklyFlyoutBackground {" in compiled
        assert ".blocklySvg .blocklyScrollbarHandle {" in compiled
        assert ".blocklyToolboxDiv {" in compiled
        assert ".omni-block-selected {" in compiled


class TestOmniSaasManager:
    """Validates multi-tenant isolation, project quotas, and escrow calculations."""

    def test_standalone_mode_unconstrained(self):
        """Verify standalone mode allows project creation without tenant registration."""
        manager = OmniSaasManager(initial_mode=WorkspaceMode.STANDALONE)
        project = manager.add_project("none", "proj_1", "Local Game", 5000)
        assert project.tenant_id == "local"

    def test_saas_mode_enforces_project_quota(self):
        """Verify cloud mode restricts projects beyond tier quota."""
        manager = OmniSaasManager(initial_mode=WorkspaceMode.OMNI_SAAS)
        manager.create_tenant("tenant_123", "Acme Academy", tier="free")
        manager.add_project("tenant_123", "p1", "Project 1", 1024)
        manager.add_project("tenant_123", "p2", "Project 2", 1024)
        manager.add_project("tenant_123", "p3", "Project 3", 1024)

        with pytest.raises(ValueError, match="Tenant project quota exceeded"):
            manager.add_project("tenant_123", "p4", "Project 4", 1024)

    def test_saas_mode_storage_reclamation(self):
        """Verify storage capacity is properly reclaimed on deletion."""
        manager = OmniSaasManager(initial_mode=WorkspaceMode.OMNI_SAAS)
        tenant = manager.create_tenant("tenant_abc", "Studio Alpha", tier="free")
        manager.add_project("tenant_abc", "p1", "Asset Heavy", 50 * 1024 * 1024)
        assert tenant.current_storage_bytes == 50 * 1024 * 1024

        manager.delete_project("tenant_abc", "p1")
        assert tenant.current_storage_bytes == 0

    def test_cloud_variable_isolation(self):
        """Verify cloud variables are isolated per tenant and project."""
        manager = OmniSaasManager(initial_mode=WorkspaceMode.OMNI_SAAS)
        manager.set_cloud_variable("t1", "p1", "score", "100")
        manager.set_cloud_variable("t2", "p1", "score", "250")

        assert manager.get_cloud_variable("t1", "p1", "score") == "100"
        assert manager.get_cloud_variable("t2", "p1", "score") == "250"
        assert manager.get_cloud_variable("t1", "p2", "score") is None

    def test_exact_bounty_escrow_settlement(self):
        """Verify financial calculation matching REWARD_POLICY formulas."""
        manager = OmniSaasManager()
        escrow = manager.calculate_bounty_escrow(9828150.0)
        assert isinstance(escrow, EscrowCalculation)
        assert escrow.bounty_usd == Decimal("9828150.0")
        assert escrow.coin_reward == Decimal("12285187.50")
        assert escrow.contributor_ratio == Decimal("0.85")
        assert escrow.cash_payout_usd == Decimal("7518534.7500")
        assert escrow.platform_fee_usd == Decimal("2309615.2500")


class TestOmniSassManagerFacade:
    """Validates integrated facade methods and safety checks."""

    def test_compile_safe_stylesheet(self):
        """Verify compilation through facade with built-in sanitization."""
        facade = OmniSassManager()
        source = "$color: #10b981;\n.status { color: $color; }"
        css = facade.compile_stylesheet(source)
        assert "color: #10b981;" in css

    def test_compile_unsafe_stylesheet_raises_error(self):
        """Verify unsafe stylesheet triggers error during compilation."""
        facade = OmniSassManager()
        source = ".danger { -moz-binding: url('malicious.xml'); }"
        with pytest.raises(ValueError, match="Security validation failed"):
            facade.compile_stylesheet(source)

    def test_generate_preset_theme(self):
        """Verify theme generation from preset name."""
        facade = OmniSassManager()
        css = facade.generate_theme_css("cyber_neon")
        assert ".blocklySvg" in css
        assert "#06b6d4" in css
