"""SASS and SCSS parser, evaluator, and CSS compiler engine."""


import colorsys
import re
from typing import Callable, Dict, List, Tuple
from packages.omni_sass.models import MixinDefinition, OutputStyle


class SassCompiler:
    """Parses and compiles SCSS stylesheets into standardized CSS."""

    MIXIN_REGEX = re.compile(r"@mixin\s+([a-zA-Z0-9_-]+)(?:\((.*?)\))?\s*\{")
    VAR_REGEX = re.compile(r"\$([a-zA-Z0-9_-]+)\s*:\s*([^;]+?)(?:\s*!default)?\s*;")
    INCLUDE_REGEX = re.compile(r"@include\s+([a-zA-Z0-9_-]+)(?:\((.*?)\))?\s*;")
    COLOR_FUNC_REGEX = re.compile(r"(lighten|darken|rgba|mix)\s*\((.*?)\)", re.IGNORECASE)

    def __init__(self) -> None:
        """Initialize compiler environment with empty variable and mixin scopes."""
        self.variables: Dict[str, str] = {}
        self.mixins: Dict[str, MixinDefinition] = {}
        self.custom_functions: Dict[str, Callable] = {}
        self._register_default_functions()

    def reset(self) -> None:
        """Clear all registered variables and mixin definitions."""
        self.variables.clear()
        self.mixins.clear()
        self._register_default_functions()

    def register_variable(self, name: str, value: str, overwrite: bool = True) -> None:
        """Register a global variable within the compiler scope."""
        clean_name = name.lstrip("$")
        if overwrite or clean_name not in self.variables:
            self.variables[clean_name] = value

    def register_function(self, name: str, func: Callable) -> None:
        """Register a custom function usable in style declarations."""
        self.custom_functions[name.lower()] = func

    def _register_default_functions(self) -> None:
        """Register built-in SASS color transformation functions."""
        self.custom_functions["lighten"] = self._func_lighten
        self.custom_functions["darken"] = self._func_darken
        self.custom_functions["rgba"] = self._func_rgba
        self.custom_functions["mix"] = self._func_mix

    def compile(self, source_code: str, style: OutputStyle = OutputStyle.EXPANDED) -> str:
        """Compile SASS/SCSS source code into CSS according to the output style."""
        cleaned = self._strip_comments(source_code)
        extracted = self._extract_mixins_and_variables(cleaned)
        expanded_includes = self._expand_includes(extracted)
        blocks = self._parse_blocks(expanded_includes)
        resolved_rules = self._flatten_rules(blocks, parent_selector="")
        rendered = self._render_css(resolved_rules, style)
        return rendered

    def _strip_comments(self, text: str) -> str:
        """Remove single-line and multi-line comments from source."""
        no_multi = re.sub(r"/\*.*?\*/", "", text, flags=re.DOTALL)
        lines = []
        for line in no_multi.splitlines():
            stripped = line.strip()
            if stripped.startswith("//"):
                continue
            if "//" in line:
                parts = line.split("//")
                lines.append(parts[0])
            else:
                lines.append(line)
        return "\n".join(lines)

    def _extract_mixins_and_variables(self, text: str) -> str:
        """Extract mixin definitions and variable declarations from text body."""
        idx = 0
        length = len(text)
        remaining = []

        while idx < length:
            sub = text[idx:]
            mixin_match = self.MIXIN_REGEX.match(sub)
            if mixin_match:
                mixin_name = mixin_match.group(1)
                raw_params = mixin_match.group(2) or ""
                params, defaults = self._parse_mixin_params(raw_params)
                body_start = idx + mixin_match.end()
                body_end = self._find_closing_brace(text, body_start)
                body_content = text[body_start:body_end]
                self.mixins[mixin_name] = MixinDefinition(
                    name=mixin_name,
                    parameters=params,
                    defaults=defaults,
                    body=body_content.strip(),
                )
                idx = body_end + 1
                continue

            var_match = self.VAR_REGEX.match(sub)
            if var_match:
                var_name = var_match.group(1)
                var_val = var_match.group(2).strip()
                is_default = "!default" in var_match.group(0)
                eval_val = self._evaluate_expression(var_val)
                self.register_variable(var_name, eval_val, overwrite=not is_default)
                idx += var_match.end()
                continue

            remaining.append(text[idx])
            idx += 1

        return "".join(remaining)

    def _parse_mixin_params(self, param_str: str) -> Tuple[List[str], Dict[str, str]]:
        """Parse parameter names and optional default values for a mixin."""
        params = []
        defaults = {}
        if not param_str.strip():
            return params, defaults

        for item in param_str.split(","):
            trimmed = item.strip()
            if not trimmed:
                continue
            if ":" in trimmed:
                p_name, p_default = trimmed.split(":", 1)
                clean_name = p_name.strip().lstrip("$")
                params.append(clean_name)
                defaults[clean_name] = self._evaluate_expression(p_default.strip())
            else:
                clean_name = trimmed.lstrip("$")
                params.append(clean_name)

        return params, defaults

    def _find_closing_brace(self, text: str, start_index: int) -> int:
        """Find matching closing brace taking nesting into account."""
        depth = 1
        pos = start_index
        text_len = len(text)
        while pos < text_len:
            char = text[pos]
            if char == "{":
                depth += 1
            elif char == "}":
                depth -= 1
                if depth == 0:
                    return pos
            pos += 1
        return text_len - 1

    def _expand_includes(self, text: str) -> str:
        """Expand @include statements with corresponding mixin bodies."""
        expanded = text
        for _ in range(5):
            match = self.INCLUDE_REGEX.search(expanded)
            if not match:
                break
            mixin_name = match.group(1)
            raw_args = match.group(2) or ""
            args = [self._evaluate_expression(a.strip()) for a in raw_args.split(",") if a.strip()]

            if mixin_name not in self.mixins:
                expanded = expanded[:match.start()] + expanded[match.end():]
                continue

            mixin = self.mixins[mixin_name]
            body_instance = mixin.body
            for i, param_name in enumerate(mixin.parameters):
                arg_val = args[i] if i < len(args) else mixin.defaults.get(param_name, "")
                body_instance = re.sub(rf"\${param_name}\b", arg_val, body_instance)

            expanded = expanded[:match.start()] + "\n" + body_instance + "\n" + expanded[match.end():]

        return expanded

    def _parse_blocks(self, text: str) -> List[Tuple[str, str]]:
        """Parse source text into selector and body pairs."""
        blocks = []
        idx = 0
        text_len = len(text)

        while idx < text_len:
            open_brace = text.find("{", idx)
            if open_brace == -1:
                break
            selector = text[idx:open_brace].strip()
            close_brace = self._find_closing_brace(text, open_brace + 1)
            body = text[open_brace + 1:close_brace]
            if selector:
                blocks.append((selector, body))
            idx = close_brace + 1

        return blocks

    def _flatten_rules(self, blocks: List[Tuple[str, str]], parent_selector: str) -> List[Tuple[str, List[Tuple[str, str]]]]:
        """Recursively flatten nested CSS rule blocks into root-level selectors."""
        results = []

        for selector_raw, body in blocks:
            resolved_selector = self._resolve_selector(parent_selector, selector_raw)
            declarations = []
            nested_blocks = []

            idx = 0
            body_len = len(body)
            while idx < body_len:
                nested_open = body.find("{", idx)
                semi_colon = body.find(";", idx)

                if nested_open != -1 and (semi_colon == -1 or nested_open < semi_colon):
                    sub_selector = body[idx:nested_open].strip()
                    sub_close = self._find_closing_brace(body, nested_open + 1)
                    sub_body = body[nested_open + 1:sub_close]
                    nested_blocks.append((sub_selector, sub_body))
                    idx = sub_close + 1
                elif semi_colon != -1:
                    stmt = body[idx:semi_colon].strip()
                    if ":" in stmt and not stmt.startswith("@"):
                        prop, val = stmt.split(":", 1)
                        eval_val = self._evaluate_expression(val.strip())
                        declarations.append((prop.strip(), eval_val))
                    idx = semi_colon + 1
                else:
                    break

            if declarations:
                results.append((resolved_selector, declarations))

            if nested_blocks:
                flattened_children = self._flatten_rules(nested_blocks, resolved_selector)
                results.extend(flattened_children)

        return results

    def _resolve_selector(self, parent: str, child: str) -> str:
        """Combine parent and child selectors respecting the & reference."""
        if not parent:
            return child.strip()

        parent_list = [p.strip() for p in parent.split(",") if p.strip()]
        child_list = [c.strip() for c in child.split(",") if c.strip()]
        combined = []

        for p in parent_list:
            for c in child_list:
                if "&" in c:
                    combined.append(c.replace("&", p))
                else:
                    combined.append(f"{p} {c}")

        return ", ".join(combined)

    def _evaluate_expression(self, expr: str) -> str:
        """Evaluate SASS variables, math operations, and color functions."""
        result = expr.strip()
        for var_name, var_val in self.variables.items():
            result = re.sub(rf"\${var_name}\b", var_val, result)

        for _ in range(3):
            color_match = self.COLOR_FUNC_REGEX.search(result)
            if not color_match:
                break
            func_name = color_match.group(1).lower()
            args_str = color_match.group(2)
            if func_name in self.custom_functions:
                resolved_color = self.custom_functions[func_name](args_str)
                result = result[:color_match.start()] + resolved_color + result[color_match.end():]

        return result

    def _func_lighten(self, args_str: str) -> str:
        """Lighten a hex color by a specified percentage."""
        parts = [p.strip() for p in args_str.split(",")]
        if len(parts) < 2:
            return parts[0] if parts else "#ffffff"
        color_hex = parts[0]
        amount_str = parts[1].replace("%", "").strip()
        try:
            amount = float(amount_str) / 100.0 if float(amount_str) > 1.0 else float(amount_str)
        except ValueError:
            amount = 0.1
        return self._adjust_lightness(color_hex, amount)

    def _func_darken(self, args_str: str) -> str:
        """Darken a hex color by a specified percentage."""
        parts = [p.strip() for p in args_str.split(",")]
        if len(parts) < 2:
            return parts[0] if parts else "#000000"
        color_hex = parts[0]
        amount_str = parts[1].replace("%", "").strip()
        try:
            amount = -(float(amount_str) / 100.0 if float(amount_str) > 1.0 else float(amount_str))
        except ValueError:
            amount = -0.1
        return self._adjust_lightness(color_hex, amount)

    def _func_rgba(self, args_str: str) -> str:
        """Return rgba CSS functional representation."""
        parts = [p.strip() for p in args_str.split(",")]
        if len(parts) == 2 and parts[0].startswith("#"):
            r, g, b = self._hex_to_rgb(parts[0])
            alpha = parts[1]
            return f"rgba({r}, {g}, {b}, {alpha})"
        if len(parts) == 4:
            return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {parts[3]})"
        return args_str

    def _func_mix(self, args_str: str) -> str:
        """Blend two hex colors with optional weight percentage."""
        parts = [p.strip() for p in args_str.split(",")]
        if len(parts) < 2:
            return parts[0] if parts else "#000000"
        c1, c2 = parts[0], parts[1]
        weight = 0.5
        if len(parts) >= 3:
            try:
                w_str = parts[2].replace("%", "").strip()
                weight = float(w_str) / 100.0 if float(w_str) > 1.0 else float(w_str)
            except ValueError:
                weight = 0.5

        r1, g1, b1 = self._hex_to_rgb(c1)
        r2, g2, b2 = self._hex_to_rgb(c2)
        r = int(r1 * weight + r2 * (1.0 - weight))
        g = int(g1 * weight + g2 * (1.0 - weight))
        b = int(b1 * weight + b2 * (1.0 - weight))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _hex_to_rgb(self, hex_val: str) -> Tuple[int, int, int]:
        """Convert a 3 or 6 digit hex color string into RGB integer tuple."""
        clean = hex_val.lstrip("#")
        if len(clean) == 3:
            clean = "".join([c * 2 for c in clean])
        if len(clean) != 6:
            return (0, 0, 0)
        try:
            return (int(clean[0:2], 16), int(clean[2:4], 16), int(clean[4:6], 16))
        except ValueError:
            return (0, 0, 0)

    def _adjust_lightness(self, hex_val: str, delta: float) -> str:
        """Adjust the HLS lightness component of a color by delta."""
        r, g, b = self._hex_to_rgb(hex_val)
        h, l, s = colorsys.rgb_to_hls(r / 255.0, g / 255.0, b / 255.0)
        new_l = max(0.0, min(1.0, l + delta))
        nr, ng, nb = colorsys.hls_to_rgb(h, new_l, s)
        ir, ig, ib = int(nr * 255.0), int(ng * 255.0), int(nb * 255.0)
        return f"#{ir:02x}{ig:02x}{ib:02x}"

    def _render_css(self, rules: List[Tuple[str, List[Tuple[str, str]]]], style: OutputStyle) -> str:
        """Format resolved rules into final CSS string."""
        if not rules:
            return ""

        if style == OutputStyle.COMPRESSED:
            compact_rules = []
            for sel, decls in rules:
                decl_str = ";".join([f"{k}:{v}" for k, v in decls])
                compact_rules.append(f"{sel}{{{decl_str}}}")
            return "".join(compact_rules)

        lines = []
        for sel, decls in rules:
            lines.append(f"{sel} {{")
            for k, v in decls:
                lines.append(f"  {k}: {v};")
            lines.append("}")
            lines.append("")

        return "\n".join(lines).strip()
