"""Static analysis auditor to ensure total elimination of legacy compatibility tokens.

This module inspects source files and codebase trees to confirm that no
obsolete legacy symbols, headers, or flags remain in active code paths.
"""

import os
import re
from pathlib import Path
from typing import Sequence

FORBIDDEN_PATTERNS: tuple[str, ...] = (
    r"legacy_rsqrt",
    r"legacy_sqrt",
    r"legacy_reciprocal",
    r"SqrtMode::Legacy",
    r"ckernel_sfpu_rsqrt_compat\.h",
    r"recip_legacy",
    r"rsqrt_legacy",
    r"rsqrt_compat",
    r"reciprocal_compat",
)


def scan_source_text(source_content: str, filename: str = "source") -> list[str]:
    """Scan source code text for any forbidden legacy tokens.

    Parameters:
        source_content: Full text of the source file.
        filename: Optional name of the file being scanned for reporting.

    Returns:
        List of violation descriptions identified during the scan.
    """
    violations: list[str] = []
    lines = source_content.splitlines()

    compiled_patterns = [re.compile(p) for p in FORBIDDEN_PATTERNS]

    for line_idx, line in enumerate(lines, start=1):
        for pat in compiled_patterns:
            if pat.search(line):
                violations.append(
                    f"{filename}:{line_idx} - Disallowed legacy symbol detected: '{pat.pattern}'"
                )
    return violations


def scan_codebase_directory(
    root_directory: str,
    allowed_extensions: Sequence[str] = (".py", ".cpp", ".hpp", ".h"),
) -> dict[str, list[str]]:
    """Recursively scan a directory tree for legacy token remnants.

    Parameters:
        root_directory: Root directory path to begin recursive inspection.
        allowed_extensions: Collection of file extensions to include in the scan.

    Returns:
        Dictionary mapping relative file paths to lists of detected violations.
    """
    findings: dict[str, list[str]] = {}
    base_path = Path(root_directory)

    if not base_path.exists():
        return findings

    for root, _, files in os.walk(root_directory):
        for file in files:
            if any(file.endswith(ext) for ext in allowed_extensions):
                full_path = Path(root) / file
                rel_path = str(full_path.relative_to(base_path))
                try:
                    content = full_path.read_text(encoding="utf-8", errors="ignore")
                    file_violations = scan_source_text(content, filename=rel_path)
                    if file_violations:
                        findings[rel_path] = file_violations
                except (OSError, UnicodeDecodeError) as exc:
                    findings[rel_path] = [f"File read error: {exc}"]
    return findings
