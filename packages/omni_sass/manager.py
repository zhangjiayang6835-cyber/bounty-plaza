"""Unified manager coordinating SASS compilation, theming, security, and cloud modes."""

from typing import List, Tuple
from packages.omni_sass.cloud_manager import OmniSaasManager
from packages.omni_sass.compiler import SassCompiler
from packages.omni_sass.models import EscrowCalculation, OutputStyle, WorkspaceMode
from packages.omni_sass.sanitizer import StyleSanitizer
from packages.omni_sass.theme_engine import OmniBlocksThemeEngine


class OmniSassManager:
    """Unified entry point and coordinator for OmniBlocks SASS mode capabilities."""

    def __init__(self, mode: WorkspaceMode = WorkspaceMode.STANDALONE) -> None:
        """Initialize all sub-engines within the unified manager."""
        self.compiler = SassCompiler()
        self.sanitizer = StyleSanitizer()
        self.theme_engine = OmniBlocksThemeEngine(compiler=self.compiler)
        self.cloud_manager = OmniSaasManager(initial_mode=mode)

    def compile_stylesheet(
        self,
        source_code: str,
        style: OutputStyle = OutputStyle.EXPANDED,
        sanitize: bool = True,
    ) -> str:
        """Validate, compile, and optionally sanitize SASS/SCSS source code."""
        if sanitize:
            violations = self.sanitizer.find_violations(source_code)
            if violations:
                raise ValueError(f"Security validation failed: {'; '.join(violations)}")

        compiled = self.compiler.compile(source_code, style=style)
        if sanitize:
            compiled = self.sanitizer.sanitize(compiled)
        return compiled

    def generate_theme_css(
        self,
        theme_name: str,
        style: OutputStyle = OutputStyle.EXPANDED,
    ) -> str:
        """Generate and compile a named preset theme into CSS."""
        preset = self.theme_engine.get_preset(theme_name)
        return self.theme_engine.compile_theme(preset, style=style)

    def validate_stylesheet(self, source_code: str) -> Tuple[bool, List[str]]:
        """Validate safety of stylesheet without compilation."""
        violations = self.sanitizer.find_violations(source_code)
        return (len(violations) == 0, violations)

    def get_escrow_settlement(self, bounty_usd: float = 9828150.0) -> EscrowCalculation:
        """Retrieve bounty escrow calculations for this task."""
        return self.cloud_manager.calculate_bounty_escrow(bounty_usd)
