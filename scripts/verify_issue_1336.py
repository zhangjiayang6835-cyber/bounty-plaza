"""Standalone verification executable for issue #1336 topological isomorphism solver."""

from __future__ import annotations

import os
import sys

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from packages.subgraph_isomorphism.verifier import (
    verify_1wl_coloring,
    verify_bipartite_rejection,
    verify_cyclic_invariants,
    verify_empty_query,
    verify_isomorphism_discovery,
)


def main() -> int:
    """Execute formal verification suite and report results."""
    checks = [
        ("Cyclic Topological Invariants", verify_cyclic_invariants),
        ("Weisfeiler-Lehman 1-WL Partitioning", verify_1wl_coloring),
        ("Triangle Subgraph Discovery", verify_isomorphism_discovery),
        ("Bipartite Negative Rejection", verify_bipartite_rejection),
        ("Empty Query Handling", verify_empty_query),
    ]

    for name, check_fn in checks:
        if not check_fn():
            sys.stdout.write(f"[FAIL] {name}\n")
            return 1
        sys.stdout.write(f"[PASS] {name}\n")

    sys.stdout.write("All formal verification checks completed successfully.\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
