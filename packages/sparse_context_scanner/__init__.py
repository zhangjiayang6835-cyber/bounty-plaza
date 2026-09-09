"""Sparse Context Scanner package for repository token optimization and honeypot defense."""

from .models import (
    FileMetadata,
    DirectoryScanResult,
    TreeCounts,
    TreeMetrics,
    TokenBudget,
    SentinelDetectionResult,
    DefenseMetrics,
    CompactedContext,
)
from .sentinel_guard import SentinelGuard
from .token_budget import TokenBudgetManager
from .scanner import SparseDirectoryScanner
from .normalizer import RepositoryNormalizer
from .defense_verifier import HoneypotDefenseVerifier

__all__ = [
    "FileMetadata",
    "DirectoryScanResult",
    "TreeCounts",
    "TreeMetrics",
    "TokenBudget",
    "SentinelDetectionResult",
    "DefenseMetrics",
    "CompactedContext",
    "SentinelGuard",
    "TokenBudgetManager",
    "SparseDirectoryScanner",
    "RepositoryNormalizer",
    "HoneypotDefenseVerifier",
]
