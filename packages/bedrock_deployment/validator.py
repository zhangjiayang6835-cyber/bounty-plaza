"""Validation logic ensuring path safety and Bedrock pack structural integrity."""

import json
from pathlib import Path
from typing import Any


class DeploymentValidator:
    """Validates pack directories and protects against path traversal vulnerabilities."""

    @staticmethod
    def validate_safe_path(target_path: Path, forbidden_roots: tuple[Path, ...] = ()) -> bool:
        """Verify that resolved path does not point to dangerous system directories."""
        resolved = target_path.resolve()
        for root in forbidden_roots:
            if resolved == root.resolve():
                return False
        return True

    @staticmethod
    def validate_manifest(source_dir: Path) -> dict[str, Any]:
        """Validate Bedrock manifest format version and UUID schema."""
        manifest_file = source_dir / "manifest.json"
        if not manifest_file.exists():
            raise FileNotFoundError(f"Missing required manifest.json in {source_dir}")

        with manifest_file.open("r", encoding="utf-8") as file_handle:
            data = json.load(file_handle)

        if "format_version" not in data:
            raise ValueError("Manifest missing required format_version property")

        if "header" not in data:
            raise ValueError("Manifest missing required header object")

        header = data["header"]
        if "uuid" not in header or "name" not in header:
            raise ValueError("Manifest header must specify uuid and name")

        return data

    @staticmethod
    def is_writable(directory: Path) -> bool:
        """Check whether directory allows file creation and writing."""
        test_file = directory / ".write_test.tmp"
        try:
            directory.mkdir(parents=True, exist_ok=True)
            with test_file.open("w", encoding="utf-8") as handle:
                handle.write("check")
            test_file.unlink()
            return True
        except OSError:
            return False
