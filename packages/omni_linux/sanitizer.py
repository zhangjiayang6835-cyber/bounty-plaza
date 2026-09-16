"""Security sandbox boundaries and AST verification for OmniBlocks Linux."""

import ast
from typing import List, Set


class SecuritySanitizer:
    """Enforces strict containment and AST verification for sandboxed guest execution."""

    FORBIDDEN_FUNCTIONS: Set[str] = {
        "eval",
        "exec",
        "compile",
        "__import__",
        "open",
        "input",
    }

    FORBIDDEN_MODULES: Set[str] = {
        "os",
        "sys",
        "subprocess",
        "ctypes",
        "socket",
        "requests",
        "urllib",
        "posix",
        "shutil",
    }

    @classmethod
    def validate_guest_code(cls, source_code: str) -> bool:
        """Inspect source AST to ensure guest code complies with sandbox isolation."""
        try:
            tree = ast.parse(source_code)
        except SyntaxError as err:
            raise ValueError(f"Guest code syntax invalid: {err}") from err

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_mod = alias.name.split(".")[0]
                    if root_mod in cls.FORBIDDEN_MODULES:
                        msg = f"Host module import forbidden in sandbox: {root_mod}"
                        raise PermissionError(msg)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_mod = node.module.split(".")[0]
                    if root_mod in cls.FORBIDDEN_MODULES:
                        msg = f"Host module import forbidden in sandbox: {root_mod}"
                        raise PermissionError(msg)
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in cls.FORBIDDEN_FUNCTIONS:
                    msg = f"Host function call forbidden in sandbox: {node.func.id}"
                    raise PermissionError(msg)
        return True

    @classmethod
    def sanitize_path(cls, path: str) -> str:
        """Sanitize virtual path to prevent escaping root jail."""
        parts = [p for p in path.replace("\\", "/").split("/") if p and p != "."]
        stack: List[str] = []
        for part in parts:
            if part == "..":
                if stack:
                    stack.pop()
            else:
                stack.append(part)
        return "/" + "/".join(stack)
