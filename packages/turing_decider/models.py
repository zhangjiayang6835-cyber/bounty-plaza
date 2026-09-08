"""Data models for computational graph analysis and termination verification."""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass(frozen=True)
class ExecutionBudget:
    """Resource constraints enforcing deterministic termination in consensus environments."""

    max_steps: int = 1000
    max_gas: int = 50000
    max_depth: int = 50
    timeout_seconds: float = 2.0


@dataclass
class ComputationalNode:
    """Represents a computational unit within a dependency graph."""

    node_id: str
    dependencies: List[str] = field(default_factory=list)
    computation: Optional[Callable[[Dict[str, Any]], Any]] = None
    gas_cost: int = 10


@dataclass
class HaltingDecision:
    """Outcome of halting evaluation on a computation or graph."""

    will_halt: bool
    reason: str
    steps_consumed: int
    gas_consumed: int
    tokens_consumed: int = 0
    execution_output: Any = None


@dataclass
class GraphValidationResult:
    """Structural analysis outcome for a computational dependency graph."""

    is_dag: bool
    topological_order: List[str] = field(default_factory=list)
    cycles_detected: List[List[str]] = field(default_factory=list)


@dataclass(frozen=True)
class ProofInvariant:
    """Formal mathematical invariant representing Turing's Undecidability Theorem."""

    theorem_name: str
    undecidable: bool
    diagonal_paradox_verified: bool
    proof_summary: str
    consensus_architecture: str
