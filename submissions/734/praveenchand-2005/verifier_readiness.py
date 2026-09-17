"""Expose direct-bounty verifier-readiness diagnostics.

Mirrors ``NSPG13/agent-bounties`` PR #726 (bounty-plaza #734): the API and MCP
surfaces expose fail-closed verifier-readiness diagnostics so agents know
whether a direct sandboxed-regression bounty can be verified before bonding
USDC.

* ``VerifierSet`` holds the pinned verifier set hash, signing threshold, and
  signer list for a contract.
* ``RunnerInfo`` tracks the sandboxed runner identifier, version, and last-seen
  timestamp.
* ``VerifierReadiness`` models the four readiness states:
  ``Ready``, ``MissingSigner``, ``StaleRunner``, ``VerifierSetMismatch``.
* ``VerifierService.check_readiness`` resolves the readiness for a contract:
  unready inventory has exactly one concise reason and is excluded from
  ready-to-earn results.
* The MCP surface exposes ``get_verifier_diagnostics`` and
  ``list_ready_bounties``.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

RUNNER_STALE_THRESHOLD_SECS = 300


@dataclass(frozen=True)
class VerifierSet:
    """Pinned verifier set for a direct-bounty contract."""

    hash: str
    threshold: int
    signers: tuple[str, ...]


@dataclass(frozen=True)
class RunnerInfo:
    """Sandboxed runner information for a direct-bounty contract."""

    identifier: str
    version: str
    last_seen: int


@dataclass(frozen=True)
class VerifierDiagnostics:
    """Diagnostics for a single contract's verifier readiness."""

    verifier_set_hash: str
    threshold: int
    runner_identifier: str
    readiness: "VerifierReadiness"

    def is_ready(self) -> bool:
        """Whether the contract is ready to verify."""
        return self.readiness.is_ready()

    def reason(self) -> Optional[str]:
        """A single concise reason when not ready."""
        return self.readiness.reason()

    def to_json(self) -> dict[str, Any]:
        """Serialize diagnostics to the canonical MCP JSON shape."""
        return {
            "verifier_set_hash": self.verifier_set_hash,
            "threshold": self.threshold,
            "runner_identifier": self.runner_identifier,
            "readiness": str(self.readiness),
            "is_ready": self.is_ready(),
            "reason": self.reason(),
        }


class VerifierReadiness:
    """Readiness state with an optional single reason."""

    _state: str
    _reason: Optional[str]

    def __init__(self, state: str, reason: Optional[str] = None) -> None:
        self._state = state
        self._reason = reason

    @classmethod
    def ready(cls) -> "VerifierReadiness":
        """Construct the Ready state."""
        return cls("ready")

    @classmethod
    def missing_signer(cls, reason: str) -> "VerifierReadiness":
        """Construct the MissingSigner state."""
        return cls("missing_signer", reason)

    @classmethod
    def stale_runner(cls, reason: str) -> "VerifierReadiness":
        """Construct the StaleRunner state."""
        return cls("stale_runner", reason)

    @classmethod
    def verifier_set_mismatch(cls, reason: str) -> "VerifierReadiness":
        """Construct the VerifierSetMismatch state."""
        return cls("verifier_set_mismatch", reason)

    def is_ready(self) -> bool:
        """Only Ready is ready."""
        return self._state == "ready"

    def reason(self) -> Optional[str]:
        """Return the single concise reason when not ready."""
        return self._reason

    def __str__(self) -> str:
        if self._reason is None:
            return self._state
        return f"{self._state}: {self._reason}"


class VerifierService:
    """Resolve verifier readiness for direct-bounty contracts."""

    def __init__(self) -> None:
        self._verifier_sets: dict[str, VerifierSet] = {}
        self._runners: dict[str, RunnerInfo] = {}

    def register_verifier_set(self, contract: str, verifier_set: VerifierSet) -> None:
        """Register the pinned verifier set for a contract."""
        self._verifier_sets[contract] = verifier_set

    def register_runner(self, contract: str, runner: RunnerInfo) -> None:
        """Register the sandboxed runner for a contract."""
        self._runners[contract] = runner

    def check_readiness(
        self, contract: str, expected_hash: str, now: Optional[int] = None
    ) -> VerifierDiagnostics:
        """Resolve verifier readiness, fail-closed for unknown configuration."""
        current = now if now is not None else int(time.time())
        verifier_set = self._verifier_sets.get(contract)
        runner = self._runners.get(contract)

        if verifier_set is not None and runner is not None:
            if verifier_set.hash != expected_hash:
                readiness = VerifierReadiness.verifier_set_mismatch(
                    f"expected {expected_hash}, got {verifier_set.hash}"
                )
            elif len(verifier_set.signers) < verifier_set.threshold:
                readiness = VerifierReadiness.missing_signer(
                    f"{len(verifier_set.signers)} of {verifier_set.threshold} signers available"
                )
            elif current - runner.last_seen > RUNNER_STALE_THRESHOLD_SECS:
                readiness = VerifierReadiness.stale_runner(
                    f"last seen {current - runner.last_seen} seconds ago"
                )
            else:
                readiness = VerifierReadiness.ready()
            return VerifierDiagnostics(
                verifier_set_hash=verifier_set.hash,
                threshold=verifier_set.threshold,
                runner_identifier=runner.identifier,
                readiness=readiness,
            )
        if verifier_set is not None and runner is None:
            return VerifierDiagnostics(
                verifier_set_hash=verifier_set.hash,
                threshold=verifier_set.threshold,
                runner_identifier="unknown",
                readiness=VerifierReadiness.stale_runner("no runner registered"),
            )
        if verifier_set is None and runner is not None:
            return VerifierDiagnostics(
                verifier_set_hash="unknown",
                threshold=0,
                runner_identifier=runner.identifier,
                readiness=VerifierReadiness.verifier_set_mismatch(
                    "no verifier set registered"
                ),
            )
        return VerifierDiagnostics(
            verifier_set_hash="unknown",
            threshold=0,
            runner_identifier="unknown",
            readiness=VerifierReadiness.verifier_set_mismatch(
                "no verifier configuration found"
            ),
        )

    def contract_status(self, contract: str, expected_hash: str) -> dict[str, Any]:
        """Status for a single contract (bounty endpoint)."""
        diagnostics = self.check_readiness(contract, expected_hash)
        return {
            "contract": contract,
            "amount": "2.00",
            "status": "claimable",
            "diagnostics": diagnostics.to_json(),
        }

    def list_bounties(
        self, expected_hash: str, contracts: tuple[str, ...], ready_only: bool = False
    ) -> list[dict[str, Any]]:
        """List contracts, optionally ready-only (excludes unready inventory)."""
        results = []
        for contract in contracts:
            diagnostics = self.check_readiness(contract, expected_hash)
            if ready_only and not diagnostics.is_ready():
                continue
            results.append(
                {
                    "contract": contract,
                    "amount": "2.00",
                    "status": "claimable",
                    "diagnostics": diagnostics.to_json(),
                }
            )
        return results


class DiagnosticsMcp:
    """MCP surface for verifier-readiness diagnostics."""

    def __init__(self, service: VerifierService) -> None:
        self._service = service

    def get_verifier_diagnostics(self, contract: str, expected_hash: str) -> dict[str, Any]:
        """Return diagnostics for a single contract."""
        return self._service.check_readiness(contract, expected_hash).to_json()

    def list_ready_bounties(
        self, expected_hash: str, contracts: tuple[str, ...]
    ) -> dict[str, Any]:
        """Return only ready bounties with diagnostics."""
        ready = []
        for contract in contracts:
            diagnostics = self._service.check_readiness(contract, expected_hash)
            if diagnostics.is_ready():
                ready.append(
                    {
                        "contract": contract,
                        "diagnostics": {
                            "verifier_set_hash": diagnostics.verifier_set_hash,
                            "threshold": diagnostics.threshold,
                            "runner_identifier": diagnostics.runner_identifier,
                            "readiness": "ready",
                        },
                    }
                )
        return {"ready_bounties": ready}


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical diagnostics fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def build_service_from_fixture(
    path: str | Path, now: Optional[int] = None
) -> VerifierService:
    """Build a service seeded from the canonical diagnostics fixture."""
    fixture = load_fixture(path)
    service = VerifierService()
    current = now if now is not None else int(time.time())
    for entry in fixture.get("contracts", []):
        verifier_set = entry.get("verifier_set")
        if verifier_set is not None:
            service.register_verifier_set(
                entry["contract"],
                VerifierSet(
                    hash=verifier_set["hash"],
                    threshold=verifier_set["threshold"],
                    signers=tuple(verifier_set["signers"]),
                ),
            )
        runner = entry.get("runner")
        if runner is not None:
            service.register_runner(
                entry["contract"],
                RunnerInfo(
                    identifier=runner["identifier"],
                    version=runner["version"],
                    last_seen=current + runner.get("last_seen_offset_secs", 0),
                ),
            )
    return service


def main() -> None:
    """Print the ready-to-earn summary for the canonical fixture."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "verifier-readiness-fixture.json"
    )
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    expected = fixture["expected_hash"]
    service = build_service_from_fixture(fixture_path)
    contracts = tuple(
        entry["contract"] for entry in fixture["contracts"]
    )
    ready = service.list_bounties(expected, contracts, ready_only=True)
    print("expected_hash:", expected)
    print("ready bounties: %d", len(ready))
    for entry in ready:
        print(" ", entry["contract"])


if __name__ == "__main__":
    main()
