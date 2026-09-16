"""AST security analyzer and static code sanitizer for OmniBlocks."""

import ast
from typing import List


class BlockSanitizer:
    """Validates block configurations and generated source code against security policies."""

    FORBIDDEN_CALLS = {"eval", "exec", "compile", "open"}
    FORBIDDEN_MODULES = {
        "pickle",
        "marshal",
        "shelve",
        "ctypes",
        "imp",
        "importlib",
        "subprocess",
        "os",
    }

    @classmethod
    def validate_code(cls, source_code: str) -> List[str]:
        """Inspect source code AST and return detected security policy violations."""
        violations = []
        try:
            tree = ast.parse(source_code)
        except SyntaxError as err:
            violations.append(f"Syntax error in code: {err}")
            return violations

        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_CALLS:
                    violations.append(f"Prohibited call detected: {node.func.id}")
                if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                    if node.func.value.id in ("os", "subprocess", "sys"):
                        violations.append(f"Prohibited system call: {node.func.value.id}.{node.func.attr}")

            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    base_module = alias.name.split(".")[0]
                    if base_module in cls.FORBIDDEN_MODULES:
                        violations.append(f"Prohibited module import: {base_module}")

        return violations

    @classmethod
    def sanitize_condition_string(cls, expr: str) -> str:
        """Strip dangerous punctuation and normalize expression text."""
        cleaned = expr.replace(";", "").replace("\n", " ").strip()
        return cleaned
