"""Abstract Syntax Tree (AST) static analysis and anti-cheating inspector."""

import ast
from typing import ClassVar

from packages.evil_guard.models import (
    InspectionResult,
    ThreatCategory,
    ThreatSeverity,
)


class AstSecurityAuditor:
    """Performs semantic syntax inspection on code submissions."""

    FORBIDDEN_FUNCTIONS: ClassVar[set[str]] = {"eval", "exec", "compile"}
    FORBIDDEN_MODULES: ClassVar[set[str]] = {
        "pickle",
        "marshal",
        "shelve",
        "ctypes",
        "imp",
        "importlib",
    }
    DANGEROUS_SYSTEM_CALLS: ClassVar[set[str]] = {
        "system",
        "popen",
        "Popen",
        "spawn",
    }

    def is_safe_code(self, code_content: str) -> bool:
        """Check if code passes semantic AST security analysis."""
        return self.audit(code_content).is_safe

    def audit(self, code_content: str) -> InspectionResult:
        """Parse and inspect Python source text for dangerous constructs."""
        result = InspectionResult(is_safe=True)
        if not code_content or not isinstance(code_content, str):
            return result

        try:
            tree = ast.parse(code_content)
        except SyntaxError as exc:
            result.record_threat(
                category=ThreatCategory.AST_VIOLATION,
                severity=ThreatSeverity.HIGH,
                description=f"Syntax parsing failure: {exc}",
                pattern="SyntaxError",
            )
            return result

        for node in ast.walk(tree):
            self._check_imports(node, result)
            self._check_calls(node, result)
            self._check_mocking_cheats(node, result)

        return result

    def _check_imports(self, node: ast.AST, result: InspectionResult) -> None:
        """Verify imported modules against restricted library policies."""
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_module = alias.name.split(".")[0]
                if root_module in self.FORBIDDEN_MODULES:
                    result.record_threat(
                        category=ThreatCategory.AST_VIOLATION,
                        severity=ThreatSeverity.CRITICAL,
                        description=f"Forbidden module import detected: {alias.name}",
                        pattern=alias.name,
                    )
        elif isinstance(node, ast.ImportFrom) and node.module:
            root_module = node.module.split(".")[0]
            if root_module in self.FORBIDDEN_MODULES:
                result.record_threat(
                    category=ThreatCategory.AST_VIOLATION,
                    severity=ThreatSeverity.CRITICAL,
                    description=f"Forbidden module import from: {node.module}",
                    pattern=node.module,
                )

    def _check_calls(self, node: ast.AST, result: InspectionResult) -> None:
        """Audit function and method invocations for dynamic execution and shells."""
        if not isinstance(node, ast.Call):
            return

        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            if func_name in self.FORBIDDEN_FUNCTIONS:
                result.record_threat(
                    category=ThreatCategory.AST_VIOLATION,
                    severity=ThreatSeverity.CRITICAL,
                    description=f"Forbidden dynamic execution call: {func_name}()",
                    pattern=func_name,
                )
        elif isinstance(node.func, ast.Attribute):
            attr_name = node.func.attr
            if attr_name in self.DANGEROUS_SYSTEM_CALLS:
                if isinstance(node.func.value, ast.Name) and node.func.value.id in (
                    "os",
                    "subprocess",
                ):
                    desc = f"Hostile process execution call: {node.func.value.id}.{attr_name}()"
                    result.record_threat(
                        category=ThreatCategory.AST_VIOLATION,
                        severity=ThreatSeverity.CRITICAL,
                        description=desc,
                        pattern=f"{node.func.value.id}.{attr_name}",
                    )

    def _check_mocking_cheats(self, node: ast.AST, result: InspectionResult) -> None:
        """Detect synthetic return bypasses designed to fool test suites."""
        if not isinstance(node, ast.FunctionDef):
            return

        for child in ast.walk(node):
            if isinstance(child, ast.Return) and child.value:
                if isinstance(child.value, ast.Constant):
                    if isinstance(child.value.value, str) and len(child.value.value) > 40:
                        desc = f"Suspected hardcoded output spoofing in function {node.name}"
                        result.record_threat(
                            category=ThreatCategory.AST_VIOLATION,
                            severity=ThreatSeverity.MEDIUM,
                            description=desc,
                            pattern=f"Return(Constant(len={len(child.value.value)}))",
                        )
