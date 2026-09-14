"""Data models for sparse directory context scanning and token budgeting."""

from dataclasses import dataclass, field
from typing import List, Dict, Any


@dataclass
class FileMetadata:
    """Metadata representing an analyzed file within a repository."""

    path: str
    size_bytes: int
    token_estimate: int
    entropy: float
    is_empty: bool
    is_sentinel: bool
    mime_type: str = "text/plain"

    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary representation."""
        result: Dict[str, Any] = {
            "path": self.path,
            "size_bytes": self.size_bytes,
            "token_estimate": self.token_estimate,
            "entropy": self.entropy,
            "is_empty": self.is_empty,
            "is_sentinel": self.is_sentinel,
            "mime_type": self.mime_type,
        }
        return result


@dataclass
class SentinelDetectionResult:
    """Detection report for adversarial phrases or honeypot prompts."""

    matched: bool
    patterns: List[str] = field(default_factory=list)
    risk_level: str = "LOW"
    neutralized_content: str = ""


@dataclass
class TreeCounts:
    """Numerical counts of directories and files traversed in a tree."""

    total_directories: int = 0
    total_files: int = 0
    empty_directories: int = 0
    pruned_directories: int = 0
    cycle_count: int = 0


@dataclass
class TreeMetrics:
    """Token and density metrics calculated across a directory tree."""

    total_tokens: int = 0
    total_bytes: int = 0
    sparsity_index: float = 0.0
    token_density: float = 0.0


@dataclass
class DirectoryScanResult:
    """Aggregate telemetry from a sparse directory traversal."""

    root_path: str
    counts: TreeCounts
    metrics: TreeMetrics
    detected_sentinels: List[str] = field(default_factory=list)
    files: List[FileMetadata] = field(default_factory=list)

    @property
    def total_directories(self) -> int:
        """Total traversed directories count."""
        return self.counts.total_directories

    @property
    def total_files(self) -> int:
        """Total traversed files count."""
        return self.counts.total_files

    @property
    def empty_directories(self) -> int:
        """Empty directories count."""
        return self.counts.empty_directories

    @property
    def pruned_directories(self) -> int:
        """Pruned sparse directories count."""
        return self.counts.pruned_directories

    @property
    def cycle_count(self) -> int:
        """Detected cyclic symlinks count."""
        return self.counts.cycle_count

    @property
    def total_tokens(self) -> int:
        """Total estimated tokens."""
        return self.metrics.total_tokens

    @property
    def total_bytes(self) -> int:
        """Total content byte size."""
        return self.metrics.total_bytes

    @property
    def sparsity_index(self) -> float:
        """Directory Sparsity Index ratio."""
        return self.metrics.sparsity_index

    @property
    def token_density(self) -> float:
        """Average token density per byte."""
        return self.metrics.token_density

    def to_dict(self) -> Dict[str, Any]:
        """Convert directory scan results to dictionary representation."""
        output: Dict[str, Any] = {
            "root_path": self.root_path,
            "total_directories": self.total_directories,
            "total_files": self.total_files,
            "empty_directories": self.empty_directories,
            "pruned_directories": self.pruned_directories,
            "total_tokens": self.total_tokens,
            "total_bytes": self.total_bytes,
            "sparsity_index": self.sparsity_index,
            "token_density": self.token_density,
            "detected_sentinels": list(self.detected_sentinels),
            "cycle_count": self.cycle_count,
            "files_count": len(self.files),
        }
        return output


@dataclass
class TokenBudget:
    """Context window allocation parameters."""

    max_tokens: int = 8192
    reserved_completion: int = 2048
    reserved_system: int = 1024

    @property
    def available_context(self) -> int:
        """Calculate maximum tokens available for repository context ingestion."""
        available: int = self.max_tokens - (self.reserved_completion + self.reserved_system)
        return max(0, available)


@dataclass
class CompactedContext:
    """Compacted repository context payload ready for LLM ingestion."""

    included_files: List[str]
    omitted_files: List[str]
    total_tokens: int
    budget_limit: int
    compaction_ratio: float
    manifest_summary: str


@dataclass
class DefenseMetrics:
    """Verification metrics evaluating resistance against context overflow honeypots."""

    lines_saved: int
    bloat_packages_prevented: int
    token_reduction_ratio: float
    execution_time_sec: float
    trap_neutralized: bool
