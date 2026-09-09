"""Repository structure normalizer and sparse directory sanitizer."""

import os
from pathlib import Path
from typing import List, Dict, Any


class RepositoryNormalizer:
    """Sanitizes sparse directories without introducing artificial bloatware."""

    @staticmethod
    def identify_empty_directories(target_dir: str | Path) -> List[str]:
        """Identify all empty leaf directories within target hierarchy.

        :param target_dir: Root directory path.
        :return: List of empty directory path strings.
        """
        root = Path(target_dir).resolve()
        empty_dirs: List[str] = []
        if not root.exists():
            return empty_dirs

        for dirpath, dirnames, filenames in os.walk(root, topdown=False):
            if any(part.startswith(".") for part in Path(dirpath).parts):
                continue
            if not dirnames and not filenames:
                empty_dirs.append(dirpath)

        return empty_dirs

    @staticmethod
    def create_gitkeep_placeholders(target_dir: str | Path) -> int:
        """Place lightweight .gitkeep markers in empty directories.

        :param target_dir: Root directory path.
        :return: Integer count of .gitkeep files created.
        """
        empty_dirs = RepositoryNormalizer.identify_empty_directories(target_dir)
        count = 0
        for dirpath in empty_dirs:
            keep_file = Path(dirpath) / ".gitkeep"
            if not keep_file.exists():
                try:
                    keep_file.touch()
                    count += 1
                except OSError:
                    continue
        return count

    @staticmethod
    def generate_manifest(target_dir: str | Path) -> Dict[str, Any]:
        """Generate structured manifest of repository layout and sparsity metrics.

        :param target_dir: Root directory path.
        :return: Dictionary representation of repository structure.
        """
        root = Path(target_dir).resolve()
        empty_dirs = RepositoryNormalizer.identify_empty_directories(root)
        total_subdirs = 0
        total_files = 0

        for _, dirnames, filenames in os.walk(root):
            total_subdirs += len(dirnames)
            total_files += len(filenames)

        manifest: Dict[str, Any] = {
            "root": str(root),
            "total_subdirectories": total_subdirs,
            "total_files": total_files,
            "empty_directories_count": len(empty_dirs),
            "empty_directories": empty_dirs,
            "is_clean": len(empty_dirs) == 0,
        }
        return manifest
