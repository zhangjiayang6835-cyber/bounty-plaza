"""
Bedrock behavior pack validator enforcing schema and template expansion integrity.
"""

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import List, Union


@dataclass
class ValidationReport:
    """Consolidated pack validation report."""

    valid: bool = True
    file_count: int = 0
    block_count: int = 0
    errors: List[str] = field(default_factory=list)


class BedrockPackValidator:
    """Validates Bedrock behavior pack assets and detects unexpanded template expressions."""

    @staticmethod
    def locate_syntax_error(content: str) -> tuple[int, int]:
        """Locate line and column of first template character triggering parser error."""
        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            char_pos = line.find("{")
            if char_pos != -1:
                next_pos = line.find("{{")
                if next_pos != -1:
                    return idx, next_pos + 1
        return 1, 1

    @classmethod
    def validate_file(cls, file_path: Path, rel_path: str, report: ValidationReport) -> None:
        """Validate an individual JSON file within behavior pack."""
        report.file_count += 1
        raw_text = file_path.read_text(encoding="utf-8")

        if "{{" in raw_text or "{%" in raw_text or "$scope" in raw_text:
            line_num, col_num = cls.locate_syntax_error(raw_text)
            err_msg = (
                f"[PackValidator][Error] Failed to parse JSON in '{rel_path}':\n"
                f"Syntax error: unexpected character '{{' at line {line_num} column {col_num}"
            )
            report.errors.append(err_msg)
            report.valid = False
            return

        try:
            data = json.loads(raw_text)
        except json.JSONDecodeError as exc:
            report.errors.append(
                f"[PackValidator][Error] Failed to parse JSON in '{rel_path}': {exc}"
            )
            report.valid = False
            return

        if not isinstance(data, dict):
            report.errors.append(
                f"[PackValidator][Error] Root is not a JSON object in '{rel_path}'"
            )
            report.valid = False
            return

        if "format_version" not in data:
            report.errors.append(f"[PackValidator][Error] Missing 'format_version' in '{rel_path}'")
            report.valid = False

        if "minecraft:block" in data:
            report.block_count += 1
            block_data = data["minecraft:block"]
            desc = block_data.get("description", {})
            identifier = desc.get("identifier", "")
            if ":" not in identifier:
                report.errors.append(
                    f"[PackValidator][Error] Block '{rel_path}' identifier must contain namespace"
                )
                report.valid = False

    @classmethod
    def validate_pack(cls, pack_dir: Union[str, Path]) -> ValidationReport:
        """Scan and validate all JSON files in behavior pack directory."""
        pack_path = Path(pack_dir)
        report = ValidationReport()

        if not pack_path.is_dir():
            report.valid = False
            report.errors.append(f"[PackValidator][Error] Pack directory not found: {pack_path}")
            return report

        json_files = sorted(pack_path.rglob("*.json"))
        for file_path in json_files:
            rel_path = file_path.relative_to(pack_path).as_posix()
            cls.validate_file(file_path, rel_path, report)

        return report
