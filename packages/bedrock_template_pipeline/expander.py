"""
Bedrock JSONTE and Jinja template expander engine.
"""

import json
from pathlib import Path
import re
from typing import Any, Dict, Optional, Union


class BedrockTemplateExpander:
    """Resolves template fragments, scopes, and variable interpolation expressions."""

    def __init__(
        self,
        template_dir: Union[str, Path] = "templates",
        default_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize expander with template directory and baseline context."""
        self.template_dir = Path(template_dir)
        base_ctx: Dict[str, Any] = {
            "namespace": "tank",
            "block_name": "custom_block",
            "texture": "default_texture",
            "sound": "wood",
            "geometry": "geometry.custom_block",
        }
        if default_context:
            base_ctx.update(default_context)
        self.default_context = base_ctx

    def load_fragment(self, template_name: str) -> str:
        """Load a reusable template fragment from disk by identifier or path."""
        clean_name = template_name.replace('"', "").replace("'", "").strip()
        json_suffix = clean_name if clean_name.endswith(".json") else f"{clean_name}.json"
        candidates = [
            self.template_dir / json_suffix,
            self.template_dir / clean_name,
            Path(clean_name),
        ]
        for candidate in candidates:
            if candidate.is_file():
                return candidate.read_text(encoding="utf-8")
        raise FileNotFoundError(f"Template fragment not found: {clean_name}")

    def expand_string(self, raw_text: str, context: Dict[str, Any]) -> str:
        """Expand includes, variables, and jinja directives in raw template text."""
        result = raw_text

        def _replace_include(match: re.Match) -> str:
            frag_name = match.group(1)
            fragment = self.load_fragment(frag_name)
            trimmed = fragment.strip()
            if trimmed.startswith("{") and trimmed.endswith("}"):
                trimmed = trimmed[1:-1].strip()
            return trimmed

        include_pattern = re.compile(
            r"^[ \t]*\{\{(?:#template|>)\s+[\"']?([^\"'}]+)[\"']?\}\}[ \t]*$",
            re.MULTILINE,
        )
        result = include_pattern.sub(_replace_include, result)

        def _extract_set(match: re.Match) -> str:
            var_name = match.group(1).strip()
            var_value = match.group(2).strip()
            context[var_name] = var_value
            return ""

        jinja_pattern = re.compile(r"\{%\s*set\s+(\w+)\s*=\s*[\"']?([^\"']+)[\"']?\s*%\}")
        result = jinja_pattern.sub(_extract_set, result)

        def _replace_var(match: re.Match) -> str:
            key = match.group(1).strip()
            if key in context:
                return str(context[key])
            return match.group(0)

        variable_pattern = re.compile(r"\{\{\s*([\w:.-]+)\s*\}\}")
        result = variable_pattern.sub(_replace_var, result)

        return result

    @classmethod
    def clean_metadata(cls, node: Any) -> Any:
        """Recursively purge internal metadata properties beginning with dollar sign."""
        if isinstance(node, list):
            return [cls.clean_metadata(item) for item in node]
        if isinstance(node, dict):
            return {
                key: cls.clean_metadata(value)
                for key, value in node.items()
                if not key.startswith("$")
            }
        return node

    @staticmethod
    def is_template(content: str) -> bool:
        """Determine whether file content contains template directives or Jinja expressions."""
        markers = ("{{", "}}", "{%", "%}", '"$scope"')
        return any(marker in content for marker in markers)

    def expand(self, content: str, filename: str = "") -> str:
        """Expand template content into valid Bedrock JSON format."""
        file_context = dict(self.default_context)
        if filename:
            stem = Path(filename).stem
            file_context["block_name"] = stem

        preliminary_scope: Dict[str, Any] = {}
        try:
            parsed = json.loads(content)
            if isinstance(parsed, dict) and "$scope" in parsed:
                preliminary_scope = parsed["$scope"]
        except (json.JSONDecodeError, TypeError):
            scope_match = re.search(r'"\$scope"\s*:\s*\{([^}]+)\}', content)
            if scope_match:
                try:
                    preliminary_scope = json.loads(f"{{{scope_match.group(1)}}}")
                except json.JSONDecodeError:
                    pass

        merged_context = {**file_context, **preliminary_scope}
        expanded_text = self.expand_string(content, merged_context)

        try:
            parsed_output = json.loads(expanded_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"Failed to parse expanded JSON for {filename or 'input'}: {exc}\n"
                f"Expanded content:\n{expanded_text}"
            ) from exc

        cleaned = self.clean_metadata(parsed_output)
        return json.dumps(cleaned, indent=2) + "\n"
