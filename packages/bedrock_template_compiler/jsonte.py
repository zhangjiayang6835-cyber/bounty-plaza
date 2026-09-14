"""JsonTE template compiler and expander for Minecraft Bedrock addons."""

import json
import os
import re
from typing import Any, Callable, Dict, List, Optional, Set, Union


class JsonteCompilationError(Exception):
    """Raised when JsonTE compilation or syntax expansion fails."""


def strip_json_comments(text: str) -> str:
    """Strip single-line and multi-line comments from JSON/JSONTE text.

    Args:
        text: Raw text content containing JSON with comments.

    Returns:
        Clean JSON text with comments stripped and trailing commas removed.
    """
    result: List[str] = []
    in_string = False
    escape = False
    index = 0
    length = len(text)

    while index < length:
        char = text[index]

        if in_string:
            result.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue

        if char == '"':
            in_string = True
            result.append(char)
            index += 1
            continue

        if char == "/" and index + 1 < length:
            next_char = text[index + 1]
            if next_char == "/":
                index += 2
                while index < length and text[index] not in ("\n", "\r"):
                    index += 1
                continue
            if next_char == "*":
                index += 2
                while index + 1 < length and not (text[index] == "*" and text[index + 1] == "/"):
                    index += 1
                index += 2
                continue

        result.append(char)
        index += 1

    clean_text = "".join(result)
    clean_text = re.sub(r",\s*([\]}])", r"\1", clean_text)
    return clean_text


def deep_merge(target: Any, source: Any) -> Any:
    """Deep merge source object onto target object recursively.

    Args:
        target: Destination base object.
        source: Source object providing overrides.

    Returns:
        Merged result.
    """
    if isinstance(target, dict) and isinstance(source, dict):
        merged = dict(target)
        for key, source_value in source.items():
            if key in merged and isinstance(merged[key], dict) and isinstance(source_value, dict):
                merged[key] = deep_merge(merged[key], source_value)
            else:
                merged[key] = source_value
        return merged

    if isinstance(target, list) and isinstance(source, list):
        return list(source)

    return source


class JsonteCompiler:
    """Compiler engine that resolves inheritance, variables, loops, and directives."""

    def __init__(self, template_resolver: Optional[Callable[[str, Optional[str]], str]] = None) -> None:
        """Initialize the compiler.

        Args:
            template_resolver: Optional callback to resolve template paths.
        """
        self.template_resolver = template_resolver

    def compile_text(
        self,
        raw_content: str,
        context: Optional[Dict[str, Any]] = None,
        base_dir: Optional[str] = None,
        file_path: Optional[str] = None,
    ) -> str:
        """Compile raw JsonTE text and return formatted valid Bedrock JSON.

        Args:
            raw_content: Raw JSONTE template string.
            context: Optional root evaluation context variables.
            base_dir: Optional base directory for relative template lookups.
            file_path: Optional path to the active template file.

        Returns:
            Formatted 100% valid Bedrock JSON string.
        """
        clean_json = strip_json_comments(raw_content)
        try:
            parsed = json.loads(clean_json)
        except json.JSONDecodeError as exc:
            raise JsonteCompilationError(f"Failed to parse JSONTE source in {file_path or 'anonymous'}: {exc}") from exc

        root_context = dict(context or {})
        expanded = self.expand_template(
            parsed,
            context=root_context,
            base_dir=base_dir,
            file_path=file_path,
            visited_files=set(),
        )

        sanitized = self.sanitize_bedrock_json(expanded)
        return json.dumps(sanitized, indent=2, ensure_ascii=False)

    def expand_template(
        self,
        data: Any,
        context: Dict[str, Any],
        base_dir: Optional[str] = None,
        file_path: Optional[str] = None,
        visited_files: Optional[Set[str]] = None,
    ) -> Any:
        """Recursively expand templates, inheritance, loops, and variable bindings.

        Args:
            data: Parsed JSON data node.
            context: Active evaluation scope variables.
            base_dir: Base directory for relative template references.
            file_path: Path of the active file being expanded.
            visited_files: Set of visited template paths for cycle detection.

        Returns:
            Fully expanded data structure without JsonTE syntax.
        """
        active_visited = set(visited_files or set())
        if file_path:
            norm_path = os.path.normpath(os.path.abspath(file_path))
            if norm_path in active_visited:
                raise JsonteCompilationError(f"Circular template inheritance detected involving {file_path}")
            active_visited.add(norm_path)

        if not isinstance(data, dict):
            return self._expand_node(data, context)

        local_context = dict(context)
        if "$scope" in data and isinstance(data["$scope"], dict):
            local_context.update(data["$scope"])
        if "$variables" in data and isinstance(data["$variables"], dict):
            local_context.update(data["$variables"])

        base_object: Dict[str, Any] = {}
        extend_target = data.get("$extend") or data.get("$template")
        if extend_target:
            targets = [extend_target] if isinstance(extend_target, str) else list(extend_target)
            for target_ref in targets:
                parent_data = self._resolve_and_load_template(target_ref, base_dir, file_path)
                parent_expanded = self.expand_template(
                    parent_data,
                    context=local_context,
                    base_dir=os.path.dirname(self._resolve_template_path(target_ref, base_dir, file_path)),
                    file_path=self._resolve_template_path(target_ref, base_dir, file_path),
                    visited_files=active_visited,
                )
                if isinstance(parent_expanded, dict):
                    base_object = deep_merge(base_object, parent_expanded)

        current_expanded: Dict[str, Any] = {}
        for key, value in data.items():
            if key in ("$extend", "$template", "$scope", "$variables"):
                continue

            if key.startswith("{{#if") and key.endswith("}}"):
                condition_expr = key[5:-2].strip()
                if self._evaluate_condition(condition_expr, local_context):
                    if isinstance(value, dict):
                        expanded_block = self._expand_node(value, local_context)
                        if isinstance(expanded_block, dict):
                            current_expanded.update(expanded_block)
                continue

            if key.startswith("{{#each") and key.endswith("}}"):
                iter_expr = key[7:-2].strip()
                expanded_entries = self._expand_each_object(iter_expr, value, local_context)
                current_expanded.update(expanded_entries)
                continue

            resolved_key = self._interpolate_string(key, local_context)
            resolved_value = self._expand_node(value, local_context)
            current_expanded[resolved_key] = resolved_value

        return deep_merge(base_object, current_expanded)

    def _expand_node(self, node: Any, context: Dict[str, Any]) -> Any:
        """Expand a generic JSON node.

        Args:
            node: Target node to expand.
            context: Current scope variables.

        Returns:
            Expanded node.
        """
        if isinstance(node, dict):
            expanded_dict: Dict[str, Any] = {}
            for key, val in node.items():
                if key.startswith("{{#each") and key.endswith("}}"):
                    iter_expr = key[7:-2].strip()
                    expanded_entries = self._expand_each_object(iter_expr, val, context)
                    expanded_dict.update(expanded_entries)
                    continue
                if key.startswith("{{#if") and key.endswith("}}"):
                    condition_expr = key[5:-2].strip()
                    if self._evaluate_condition(condition_expr, context):
                        if isinstance(val, dict):
                            sub = self._expand_node(val, context)
                            if isinstance(sub, dict):
                                expanded_dict.update(sub)
                    continue
                expanded_dict[self._interpolate_string(key, context)] = self._expand_node(val, context)
            return expanded_dict

        if isinstance(node, list):
            expanded_list: List[Any] = []
            for item in node:
                if isinstance(item, dict) and len(item) == 1:
                    first_key = next(iter(item))
                    if first_key.startswith("{{#each") and first_key.endswith("}}"):
                        iter_expr = first_key[7:-2].strip()
                        expanded_items = self._expand_each_list(iter_expr, item[first_key], context)
                        expanded_list.extend(expanded_items)
                        continue
                expanded_list.append(self._expand_node(item, context))
            return expanded_list

        if isinstance(node, str):
            return self._interpolate_value(node, context)

        return node

    def _expand_each_list(self, expression: str, body: Any, context: Dict[str, Any]) -> List[Any]:
        """Expand an {{#each}} block when embedded inside an array.

        Args:
            expression: Iterable expression name or JSON literal.
            body: Body template for each iteration.
            context: Parent scope context.

        Returns:
            List of expanded items.
        """
        items = self._resolve_iterable(expression, context)
        results: List[Any] = []

        if isinstance(items, list):
            for index, item in enumerate(items):
                iteration_scope = dict(context)
                iteration_scope["$index"] = index
                iteration_scope["$value"] = item
                iteration_scope["this"] = item
                if isinstance(item, dict):
                    iteration_scope.update(item)
                results.append(self._expand_node(body, iteration_scope))
        elif isinstance(items, dict):
            for index, (key, value) in enumerate(items.items()):
                iteration_scope = dict(context)
                iteration_scope["$index"] = index
                iteration_scope["$key"] = key
                iteration_scope["$value"] = value
                iteration_scope["this"] = value
                if isinstance(value, dict):
                    iteration_scope.update(value)
                results.append(self._expand_node(body, iteration_scope))

        return results

    def _expand_each_object(self, expression: str, body: Any, context: Dict[str, Any]) -> Dict[str, Any]:
        """Expand an {{#each}} block when embedded inside an object.

        Args:
            expression: Iterable expression name or JSON literal.
            body: Body template for each iteration.
            context: Parent scope context.

        Returns:
            Dictionary of expanded key-value mappings.
        """
        items = self._resolve_iterable(expression, context)
        results: Dict[str, Any] = {}

        if isinstance(items, list):
            for index, item in enumerate(items):
                iteration_scope = dict(context)
                iteration_scope["$index"] = index
                iteration_scope["$value"] = item
                iteration_scope["this"] = item
                if isinstance(item, dict):
                    iteration_scope.update(item)
                expanded = self._expand_node(body, iteration_scope)
                if isinstance(expanded, dict):
                    results.update(expanded)
        elif isinstance(items, dict):
            for index, (key, value) in enumerate(items.items()):
                iteration_scope = dict(context)
                iteration_scope["$index"] = index
                iteration_scope["$key"] = key
                iteration_scope["$value"] = value
                iteration_scope["this"] = value
                if isinstance(value, dict):
                    iteration_scope.update(value)
                expanded = self._expand_node(body, iteration_scope)
                if isinstance(expanded, dict):
                    results.update(expanded)

        return results

    def _resolve_iterable(self, expression: str, context: Dict[str, Any]) -> Union[List[Any], Dict[str, Any]]:
        """Resolve an iterable expression to a list or dict.

        Args:
            expression: Expression string (e.g. variable name or literal).
            context: Active scope.

        Returns:
            Resolved iterable object.
        """
        expr = expression.strip()
        if (expr.startswith("[") and expr.endswith("]")) or (expr.startswith("{") and expr.endswith("}")):
            try:
                literal_json = expr.replace("'", '"')
                return json.loads(literal_json)
            except json.JSONDecodeError:
                pass

        val = self._lookup_context(expr, context)
        if isinstance(val, (list, dict)):
            return val
        return []

    def _evaluate_condition(self, expression: str, context: Dict[str, Any]) -> bool:
        """Evaluate a boolean condition expression.

        Args:
            expression: Condition expression string.
            context: Active scope variables.

        Returns:
            Truth value of condition.
        """
        expr = expression.strip()
        if expr.startswith("!"):
            return not self._evaluate_condition(expr[1:].strip(), context)

        val = self._lookup_context(expr, context)
        return bool(val)

    def _lookup_context(self, path: str, context: Dict[str, Any]) -> Any:
        """Lookup dotted path in context dictionary.

        Args:
            path: Identifier path (e.g. 'item.damage').
            context: Active scope variables.

        Returns:
            Resolved value or empty string.
        """
        parts = path.strip().split(".")
        current: Any = context
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            elif isinstance(current, list) and part.isdigit():
                idx = int(part)
                if 0 <= idx < len(current):
                    current = current[idx]
                else:
                    return ""
            else:
                return ""
        return current

    def _interpolate_value(self, text: str, context: Dict[str, Any]) -> Any:
        """Interpolate variable expressions into text or preserve native data types.

        Args:
            text: Input string with potential mustache tags.
            context: Active scope variables.

        Returns:
            Interpolated value with types preserved when entire string matches a variable.
        """
        trimmed = text.strip()
        exact_match = re.fullmatch(r"\{\{([^{}]+)\}\}", trimmed)
        if exact_match:
            var_name = exact_match.group(1).strip()
            val = self._lookup_context(var_name, context)
            if val != "":
                return val
            if var_name in context:
                return context[var_name]

        return self._interpolate_string(text, context)

    def _interpolate_string(self, text: str, context: Dict[str, Any]) -> str:
        """Interpolate mustache variables into string.

        Args:
            text: Input string.
            context: Active scope.

        Returns:
            String with variables replaced.
        """
        def replacer(match: re.Match) -> str:
            expr = match.group(1).strip()
            val = self._lookup_context(expr, context)
            if val is not None and val != "":
                return str(val)
            if expr in context:
                return str(context[expr])
            return ""

        return re.sub(r"\{\{([^{}]+)\}\}", replacer, text)

    def _resolve_template_path(self, target_ref: str, base_dir: Optional[str], file_path: Optional[str]) -> str:
        """Resolve filesystem path for an extended template reference.

        Args:
            target_ref: Relative path or identifier referenced in $extend.
            base_dir: Base directory context.
            file_path: Active file context.

        Returns:
            Normalized absolute path to the target template.
        """
        if self.template_resolver:
            resolved = self.template_resolver(target_ref, file_path)
            if resolved:
                return resolved

        candidate_dirs = []
        if file_path:
            candidate_dirs.append(os.path.dirname(os.path.abspath(file_path)))
        if base_dir:
            candidate_dirs.append(os.path.abspath(base_dir))
        candidate_dirs.append(os.getcwd())

        extensions = ["", ".jsonte", ".json"]
        for directory in candidate_dirs:
            for ext in extensions:
                candidate = os.path.normpath(os.path.join(directory, target_ref + ext))
                if os.path.isfile(candidate):
                    return candidate

        return os.path.normpath(target_ref)

    def _resolve_and_load_template(
        self,
        target_ref: str,
        base_dir: Optional[str],
        file_path: Optional[str],
    ) -> Dict[str, Any]:
        """Load and parse parent template referenced by $extend.

        Args:
            target_ref: Relative or resolved reference to template.
            base_dir: Base directory context.
            file_path: Active file context.

        Returns:
            Parsed JSON dictionary of parent template.
        """
        full_path = self._resolve_template_path(target_ref, base_dir, file_path)
        if not os.path.isfile(full_path):
            raise JsonteCompilationError(f"Could not locate parent template referenced in $extend: {target_ref}")

        with open(full_path, "r", encoding="utf-8") as file_handle:
            content = file_handle.read()

        clean_content = strip_json_comments(content)
        try:
            return json.loads(clean_content)
        except json.JSONDecodeError as exc:
            raise JsonteCompilationError(f"Error parsing parent template {full_path}: {exc}") from exc

    def sanitize_bedrock_json(self, node: Any) -> Any:
        """Recursively strip all compile-time directives and validate clean Bedrock JSON.

        Args:
            node: Target node to sanitize.

        Returns:
            Clean node with zero directive keys or comments.
        """
        if isinstance(node, dict):
            clean_dict: Dict[str, Any] = {}
            for key, value in node.items():
                if key.startswith("$") or key.startswith("//"):
                    continue
                clean_dict[key] = self.sanitize_bedrock_json(value)
            return clean_dict

        if isinstance(node, list):
            return [self.sanitize_bedrock_json(elem) for elem in node]

        if isinstance(node, str):
            clean_str = re.sub(r"\{\{[^{}]*\}\}", "", node)
            return clean_str

        return node
