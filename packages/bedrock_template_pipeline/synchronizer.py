"""
Directory synchronization and differential asset staging engine.
"""

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import List, Set, Union


@dataclass
class SyncStats:
    """Statistics recorded during directory synchronization pass."""

    copied: int = 0
    removed: int = 0
    unchanged: int = 0


class DirectorySynchronizer:
    """Synchronizes staging assets to target directory with differential updates and cleanup."""

    @staticmethod
    def collect_all_files(directory: Path) -> List[Path]:
        """Recursively enumerate all regular files inside a directory tree."""
        if not directory.is_dir():
            return []
        return sorted([p for p in directory.rglob("*") if p.is_file()])

    @staticmethod
    def prune_empty_directories(directory: Path) -> None:
        """Recursively prune empty folders bottom-up."""
        if not directory.is_dir():
            return
        subdirs = sorted([d for d in directory.rglob("*") if d.is_dir()], reverse=True)
        for subdir in subdirs:
            if not any(subdir.iterdir()):
                try:
                    subdir.rmdir()
                except OSError:
                    pass

    @classmethod
    def synchronize(
        cls,
        src_dir: Union[str, Path],
        dest_dir: Union[str, Path],
        clean: bool = True,
    ) -> SyncStats:
        """Synchronize files from src_dir to dest_dir with optional cleanup of orphaned targets."""
        src_path = Path(src_dir).resolve()
        dest_path = Path(dest_dir).resolve()
        stats = SyncStats()

        if not src_path.is_dir():
            raise FileNotFoundError(f"Source directory does not exist: {src_path}")

        dest_path.mkdir(parents=True, exist_ok=True)
        src_files = cls.collect_all_files(src_path)
        source_rel_paths: Set[str] = set()

        for s_file in src_files:
            rel = s_file.relative_to(src_path).as_posix()
            source_rel_paths.add(rel)
            t_file = dest_path / rel

            needs_copy = True
            if t_file.is_file():
                if s_file.read_bytes() == t_file.read_bytes():
                    needs_copy = False
                    stats.unchanged += 1

            if needs_copy:
                t_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(s_file, t_file)
                stats.copied += 1

        if clean and dest_path.is_dir():
            dest_files = cls.collect_all_files(dest_path)
            for d_file in dest_files:
                rel = d_file.relative_to(dest_path).as_posix()
                if rel not in source_rel_paths:
                    d_file.unlink()
                    stats.removed += 1
            cls.prune_empty_directories(dest_path)

        return stats
