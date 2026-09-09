"""Ruby texture generator package for Issue #1229.

Provides authentic Jappa-style color transformation from vanilla Diamond toolsets
to Ruby toolsets with depth, hue shifting, and specular highlight preservation.
"""

from packages.ruby_texture_generator.palette import (
    DIAMOND_PALETTE,
    RUBY_PALETTE,
    color_distance,
    is_diamond_pixel,
    recolor_pixel,
)
from packages.ruby_texture_generator.recolor import (
    recolor_rgba_buffer,
    recolor_image_bytes,
    recolor_image,
)
from packages.ruby_texture_generator.textures import (
    generate_diamond_tool,
    generate_all_tools,
    TOOL_NAMES,
)
from packages.ruby_texture_generator.validator import (
    validate_ruby_texture,
    ValidationResult,
)

__all__ = [
    "DIAMOND_PALETTE",
    "RUBY_PALETTE",
    "color_distance",
    "is_diamond_pixel",
    "recolor_pixel",
    "recolor_rgba_buffer",
    "recolor_image_bytes",
    "recolor_image",
    "generate_diamond_tool",
    "generate_all_tools",
    "TOOL_NAMES",
    "validate_ruby_texture",
    "ValidationResult",
]
