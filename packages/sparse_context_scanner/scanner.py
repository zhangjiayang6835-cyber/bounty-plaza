"""Sparse directory repository context scanner and optimization engine."""

import os
from pathlib import Path
from typing import Set, List, Tuple, Optional
from .models import (
    FileMetadata,
    DirectoryScanResult,
    TreeCounts,
    TreeMetrics,
    TokenBudget,
    CompactedContext,
)
from .sentinel_guard import SentinelGuard
from .token_budget import TokenBudgetManager


class SparseDirectoryScanner:
    """Scans directory structures, prunes sparse subtrees, and guards against honeypots."""

    IGNORED_DIRS = {
        ".git",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
        ".venv",
        "venv",
    }

    def __init__(
        self,
        guard: Optional[SentinelGuard] = None,
        budget_manager: Optional[TokenBudgetManager] = None,
    ) -> None:
        """Initialize scanner with optional sentinel guard and budget manager."""
        self.guard: SentinelGuard = guard if guard is not None else SentinelGuard()
        self.budget_manager: TokenBudgetManager = (
            budget_manager if budget_manager is not None else TokenBudgetManager()
        )

    def scan(self, target_dir: str | Path, max_depth: int = 15) -> DirectoryScanResult:
        """Scan repository directory structure, collecting metrics and pruning empty subtrees.

        :param target_dir: Root directory path to scan.
        :param max_depth: Maximum directory traversal depth.
        :return: DirectoryScanResult containing detailed tree telemetry.
        """
        root = Path(target_dir).resolve()
        if not root.exists():
            return self._empty_result(str(root))

        counts = TreeCounts()
        file_metas: List[FileMetadata] = []
        detected_sentinels: List[str] = []

        self._traverse_tree(root, max_depth, counts, file_metas, detected_sentinels)

        counts.total_files = len(file_metas)
        metrics = self._calculate_metrics(counts, file_metas)

        return DirectoryScanResult(
            root_path=str(root),
            counts=counts,
            metrics=metrics,
            detected_sentinels=detected_sentinels,
            files=file_metas,
        )

    def _traverse_tree(
        self,
        root: Path,
        max_depth: int,
        counts: TreeCounts,
        metas: List[FileMetadata],
        sentinels: List[str],
    ) -> None:
        """Perform depth-bounded iterative traversal of repository tree."""
        visited_paths: Set[str] = set()
        stack: List[Tuple[Path, int]] = [(root, 0)]
        while stack:
            curr_path, depth = stack.pop()
            real_curr = os.path.realpath(str(curr_path))
            if real_curr in visited_paths:
                counts.cycle_count += 1
                continue
            visited_paths.add(real_curr)
            counts.total_directories += 1

            subdirs, files_in_dir = self._read_dir_contents(curr_path)
            if not subdirs and not files_in_dir:
                counts.empty_directories += 1
                counts.pruned_directories += 1

            self._process_dir_files(files_in_dir, curr_path, metas, sentinels)

            if depth < max_depth:
                for subdir in reversed(subdirs):
                    stack.append((Path(subdir.path), depth + 1))

    def _read_dir_contents(self, path: Path) -> Tuple[List[os.DirEntry], List[os.DirEntry]]:
        """Read and classify directory entries into subdirectories and files."""
        subdirs: List[os.DirEntry] = []
        files: List[os.DirEntry] = []
        try:
            for entry in os.scandir(path):
                if entry.name in self.IGNORED_DIRS:
                    continue
                if entry.is_dir(follow_symlinks=True):
                    subdirs.append(entry)
                elif entry.is_file(follow_symlinks=False):
                    files.append(entry)
        except (PermissionError, OSError):
            pass
        return subdirs, files

    def _process_dir_files(
        self,
        files: List[os.DirEntry],
        parent: Path,
        metas: List[FileMetadata],
        sentinels: List[str],
    ) -> None:
        """Analyze individual files and append resulting metadata."""
        for entry in files:
            meta = self._analyze_file(entry, parent)
            if meta is not None:
                metas.append(meta)
                if meta.is_sentinel:
                    sentinels.append(meta.path)

    @staticmethod
    def _calculate_metrics(counts: TreeCounts, metas: List[FileMetadata]) -> TreeMetrics:
        """Calculate aggregate token and sparsity metrics."""
        total_tokens = sum(f.token_estimate for f in metas)
        total_bytes = sum(f.size_bytes for f in metas)
        total_nodes = counts.total_directories + counts.total_files
        sparsity = round(counts.empty_directories / total_nodes, 4) if total_nodes > 0 else 0.0
        density = round(total_tokens / total_bytes, 4) if total_bytes > 0 else 0.0
        return TreeMetrics(
            total_tokens=total_tokens,
            total_bytes=total_bytes,
            sparsity_index=sparsity,
            token_density=density,
        )

    @staticmethod
    def _empty_result(root_str: str) -> DirectoryScanResult:
        """Create empty scan result for non-existent target directories."""
        return DirectoryScanResult(
            root_path=root_str,
            counts=TreeCounts(),
            metrics=TreeMetrics(),
            detected_sentinels=[],
            files=[],
        )

    def _analyze_file(self, entry: os.DirEntry, parent: Path) -> Optional[FileMetadata]:
        """Analyze individual file entry for size, entropy, tokens, and sentinel triggers."""
        try:
            stat = entry.stat(follow_symlinks=False)
            size = stat.st_size
        except OSError:
            return None

        file_path = str(parent / entry.name)
        if size == 0:
            return FileMetadata(
                path=file_path,
                size_bytes=0,
                token_estimate=0,
                entropy=0.0,
                is_empty=True,
                is_sentinel=False,
            )

        content_text = ""
        raw_bytes = b""
        try:
            with open(entry.path, "rb") as fh:
                raw_bytes = fh.read(256 * 1024)
            content_text = raw_bytes.decode("utf-8", errors="ignore")
        except OSError:
            pass

        entropy = self.budget_manager.calculate_entropy(raw_bytes)
        tokens = self.budget_manager.estimate_tokens(content_text)
        sentinel_result = self.guard.scan_content(content_text)

        return FileMetadata(
            path=file_path,
            size_bytes=size,
            token_estimate=tokens,
            entropy=entropy,
            is_empty=False,
            is_sentinel=sentinel_result.matched,
        )

    def optimize_context(
        self,
        target_dir: str | Path,
        budget: Optional[TokenBudget] = None,
        priority_paths: Optional[List[str]] = None,
    ) -> CompactedContext:
        """Scan target directory and generate compacted context meeting budget constraints.

        :param target_dir: Root directory path to scan.
        :param budget: Optional context window token budget.
        :param priority_paths: Optional path prefixes to prioritize.
        :return: CompactedContext representation.
        """
        if budget is not None:
            self.budget_manager.budget = budget
        scan_result = self.scan(target_dir)
        return self.budget_manager.compact(scan_result.files, priority_paths)
