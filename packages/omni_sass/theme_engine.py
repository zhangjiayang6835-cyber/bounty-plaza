"""Visual theme generator and SCSS builder for OmniBlocks block workspace."""

from typing import Optional
from packages.omni_sass.compiler import SassCompiler
from packages.omni_sass.models import OutputStyle, ThemeConfig


class OmniBlocksThemeEngine:
    """Generates and compiles custom SCSS themes for OmniBlocks Blockly workspace."""

    PRESETS = {
        "default": ThemeConfig(
            name="default",
            primary_color="#4c97ff",
            secondary_color="#4280d7",
            workspace_background="#ffffff",
            toolbox_background="#f9f9f9",
            text_color="#575e75",
            accent_color="#ffab19",
        ),
        "dark": ThemeConfig(
            name="dark",
            primary_color="#6366f1",
            secondary_color="#4f46e5",
            workspace_background="#1e1e2e",
            toolbox_background="#181825",
            text_color="#cdd6f4",
            accent_color="#f59e0b",
        ),
        "high_contrast": ThemeConfig(
            name="high_contrast",
            primary_color="#000000",
            secondary_color="#1a1a1a",
            workspace_background="#ffffff",
            toolbox_background="#e5e7eb",
            text_color="#000000",
            accent_color="#dc2626",
        ),
        "cyber_neon": ThemeConfig(
            name="cyber_neon",
            primary_color="#06b6d4",
            secondary_color="#0891b2",
            workspace_background="#0f172a",
            toolbox_background="#020617",
            text_color="#38bdf8",
            accent_color="#ec4899",
        ),
    }

    def __init__(self, compiler: Optional[SassCompiler] = None) -> None:
        """Initialize the theme engine with a SassCompiler instance."""
        self.compiler = compiler or SassCompiler()

    def get_preset(self, name: str) -> ThemeConfig:
        """Retrieve a preset theme configuration by name."""
        key = name.lower().strip()
        if key not in self.PRESETS:
            raise KeyError(f"Theme preset not found: {name}")
        return self.PRESETS[key]

    def build_theme_scss(self, theme: ThemeConfig) -> str:
        """Generate SCSS stylesheet source code tailored to OmniBlocks workspace elements."""
        template = [
            f"$theme-primary: {theme.primary_color};",
            f"$theme-secondary: {theme.secondary_color};",
            f"$workspace-bg: {theme.workspace_background};",
            f"$toolbox-bg: {theme.toolbox_background};",
            f"$text-main: {theme.text_color};",
            f"$accent-btn: {theme.accent_color};",
            f"$radius: {theme.border_radius};",
            "",
            "@mixin block-glow($glow-color) {",
            "  filter: drop-shadow(0 2px 6px rgba($glow-color, 0.4));",
            "}",
            "",
            ".blocklySvg {",
            "  background-color: $workspace-bg;",
            "  font-family: inherit;",
            "  .blocklyFlyoutBackground {",
            "    fill: $toolbox-bg;",
            "    fill-opacity: 0.95;",
            "  }",
            "  .blocklyScrollbarHandle {",
            "    fill: lighten($theme-primary, 15%);",
            "    &:hover {",
            "      fill: $theme-primary;",
            "    }",
            "  }",
            "}",
            "",
            ".blocklyToolboxDiv {",
            "  background-color: $toolbox-bg;",
            "  color: $text-main;",
            "  border-right: 1px solid darken($toolbox-bg, 10%);",
            "  .blocklyTreeLabel {",
            "    font-weight: 600;",
            "  }",
            "}",
            "",
            ".omni-block-selected {",
            "  @include block-glow($theme-primary);",
            "  stroke: $accent-btn;",
            "  stroke-width: 2px;",
            "}",
            "",
            ".omni-toolbar-button {",
            "  background-color: $theme-primary;",
            "  color: #ffffff;",
            "  border-radius: $radius;",
            "  &:hover {",
            "    background-color: darken($theme-primary, 10%);",
            "  }",
            "}",
        ]
        return "\n".join(template)

    def compile_theme(self, theme: ThemeConfig, style: OutputStyle = OutputStyle.EXPANDED) -> str:
        """Compile a ThemeConfig into standard CSS."""
        scss_source = self.build_theme_scss(theme)
        return self.compiler.compile(scss_source, style=style)
