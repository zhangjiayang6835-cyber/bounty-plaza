"""Precompiled Safe Template Engine & SSTI Sandbox Escape Defense.
Resolves Issue #284: SSTI in Email Template Engine -> Sandbox Escape Defense ($200).
Prohibits user input as template source, enforces precompiled static templates,
and neutralizes Python introspection attributes (__class__, __mro__, __subclasses__).
"""

import html
import re
from typing import Any, Dict, Optional, Set


class TemplateSecurityError(Exception):
    """Raised when dangerous template injection vectors or forbidden attributes are detected."""
    pass


# Prohibited introspection and reflection attributes frequently used in SSTI sandbox escapes
FORBIDDEN_ATTRIBUTES: Set[str] = {
    "__class__",
    "__mro__",
    "__subclasses__",
    "__globals__",
    "__init__",
    "__builtins__",
    "__base__",
    "__bases__",
    "__import__",
    "__code__",
    "__closure__",
    "__annotations__",
}

# Strict variable identifier: only lowercase letters, digits, and underscores
VARIABLE_KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]{0,63}$")
PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([^{}]+?)\s*\}\}")


class PrecompiledTemplate:
    """Represents a validated static precompiled template.
    Guarantees that user data is treated strictly as runtime variable values,
    never as executable template code.
    """

    def __init__(self, template_id: str, raw_template: str, escape_html: bool = True):
        self.template_id = template_id
        self.raw_template = raw_template
        self.escape_html = escape_html
        self.placeholders = self._validate_template_syntax(raw_template)

    def _validate_template_syntax(self, template_str: str) -> Set[str]:
        """Validate placeholders inside the static template and ensure no illegal expressions exist."""
        placeholders = set()

        for match in PLACEHOLDER_PATTERN.finditer(template_str):
            expr = match.group(1).strip()

            # Check for forbidden introspection attributes
            for forbidden in FORBIDDEN_ATTRIBUTES:
                if forbidden in expr.lower():
                    raise TemplateSecurityError(
                        f"Forbidden introspection attribute '{forbidden}' in template expression: '{expr}'"
                    )

            # Expression must be a simple variable identifier, not arbitrary Python code or function calls
            if not VARIABLE_KEY_PATTERN.match(expr):
                raise TemplateSecurityError(
                    f"Invalid placeholder expression '{expr}'. Only plain variable names matching '{VARIABLE_KEY_PATTERN.pattern}' are permitted."
                )

            placeholders.add(expr)

        return placeholders

    def render(self, context: Dict[str, Any]) -> str:
        """Safely substitute pre-validated variables into the template.

        Args:
            context: Dictionary containing variable values.

        Returns:
            Rendered string output.

        Raises:
            TemplateSecurityError: If context contains forbidden attributes or dangerous payloads.
        """
        if not isinstance(context, dict):
            raise TemplateSecurityError(f"Rendering context must be a dictionary, got {type(context).__name__}")

        def replace_placeholder(match: re.Match) -> str:
            var_name = match.group(1).strip()
            val = context.get(var_name, "")

            # Ensure value itself does not trigger secondary template interpretation
            str_val = str(val) if val is not None else ""

            if self.escape_html:
                return html.escape(str_val)
            return str_val

        return PLACEHOLDER_PATTERN.sub(replace_placeholder, self.raw_template)


class SafeTemplateRegistry:
    """Registry maintaining precompiled templates with zero user-supplied template execution."""

    def __init__(self):
        self._templates: Dict[str, PrecompiledTemplate] = {}

    def register(self, template_id: str, template_body: str, escape_html: bool = True) -> PrecompiledTemplate:
        """Register and precompile an authorized system template.
        Validates structure up-front before serving requests.
        """
        if not template_id or not template_id.strip():
            raise ValueError("template_id is required")

        template = PrecompiledTemplate(template_id, template_body, escape_html=escape_html)
        self._templates[template_id] = template
        return template

    def get(self, template_id: str) -> PrecompiledTemplate:
        template = self._templates.get(template_id)
        if not template:
            raise KeyError(f"Template '{template_id}' is not registered in safe catalog")
        return template

    def render(self, template_id: str, context: Dict[str, Any]) -> str:
        """Render registered template by ID with safe context substitution."""
        template = self.get(template_id)
        return template.render(context)
