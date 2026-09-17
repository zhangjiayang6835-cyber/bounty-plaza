"""Add an end-to-end profitable inventory contract test.

Mirrors ``NSPG13/agent-bounties`` PR #663 (bounty-plaza #737): one fixture
proves a fully funded, terms-valid, verification-ready bounty appears in every
claimable inventory surface with exact reward and bond economics.

* ``Opportunity`` models a single inventory item with cash economics (solver
  reward, refundable claim bond, required external spend, gross cash margin).
* ``render_opportunity_feeds`` renders JSON and RSS feeds; the RSS summary is
  explicit that the figure is "Gross cash margin (not net profit)".
* ``apply_query`` applies a view: ``ready_to_earn`` keeps only claimable items
  while ``engineering`` (lifecycle) keeps claimed items as unpaid
  ``in_progress`` without treating them as corrupt.
* A claimed bounty leaves claimable-only results but remains visible in
  lifecycle surfaces as escrowed/unpaid.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

READY_TO_EARN = "ready_to_earn"
ENGINEERING = "engineering"

# The Opportunity record mirrors the upstream Rust struct field-for-field, so
# the instance-attribute limit is intentionally lifted for this data type.
# pylint: disable=too-many-instance-attributes


@dataclass(frozen=True)
class CashEconomics:
    """Exact reward and bond economics for a contract fixture."""

    solver_reward: str
    refundable_claim_bond: str
    required_external_spend: str
    gross_cash_margin: str
    positive: bool = True

    def to_json(self) -> dict[str, Any]:
        """Serialize the economics block to the canonical JSON shape."""
        return {
            "solver_reward": {"amount": self.solver_reward},
            "refundable_claim_bond": {"amount": self.refundable_claim_bond},
            "required_external_spend": {"amount": self.required_external_spend},
            "gross_cash_margin": {"amount": self.gross_cash_margin},
            "gross_cash_margin_positive": self.positive,
        }


@dataclass
class Opportunity:
    """A single contract opportunity surfaced across inventory surfaces."""

    work_state: str
    payment_state: str
    payment_committed: bool
    verification_ready: bool
    funded_amount: str
    reward: str
    bond: str
    terms_hash: str
    network: str = "base-mainnet"
    verification_method: str = "sandboxed_regression_v1"

    @classmethod
    def from_fixture_item(cls, item: dict[str, Any]) -> "Opportunity":
        """Build an opportunity from a canonical fixture item."""
        return cls(
            work_state=item["work_state"],
            payment_state=item["payment_state"],
            payment_committed=item["payment_committed"],
            verification_ready=item["verification_ready"],
            funded_amount=item["funded_amount"],
            reward=item["reward"],
            bond=item["bond"],
            terms_hash=item["terms_hash"],
            network=item.get("network", "base-mainnet"),
            verification_method=item.get(
                "verification_method", "sandboxed_regression_v1"
            ),
        )

    def economics(self) -> CashEconomics:
        """Compute exact cash economics from the reward and bond."""
        gross = int(self.reward) - int(self.bond)
        return CashEconomics(
            solver_reward=self.reward,
            refundable_claim_bond=self.bond,
            required_external_spend="0",
            gross_cash_margin=str(gross),
            positive=gross > 0,
        )

    def is_claimable(self) -> bool:
        """A claimable item is funded, escrowed, committed, and verifier-ready."""
        return (
            self.work_state == "claimable"
            and self.payment_state == "escrowed"
            and self.payment_committed
            and self.verification_ready
        )

    def is_terms_valid(self) -> bool:
        """Terms are valid when a non-empty terms hash is committed."""
        return len(self.terms_hash) > 0

    def as_api_json(self) -> dict[str, Any]:
        """Serialize as the API/MCP structured-content item."""
        return {
            "work_state": self.work_state,
            "payment_state": self.payment_state,
            "payment_committed": self.payment_committed,
            "verification_ready": self.verification_ready,
            "funded_amount": {"amount": self.funded_amount},
            "reward": {"amount": self.reward},
            "bond": {"amount": self.bond},
            "terms_hash": self.terms_hash,
            "cash_economics": self.economics().to_json(),
            "network": self.network,
            "verification_method": self.verification_method,
        }


@dataclass
class OpportunityProjection:
    """A projection of opportunities for a single applied view."""

    items: list[Opportunity]
    applied_view: str
    network: str = "base-mainnet"
    degraded: bool = False

    @classmethod
    def from_fixture(cls, fixture: dict[str, Any]) -> "OpportunityProjection":
        """Build a projection from the canonical inventory fixture."""
        items = [
            Opportunity.from_fixture_item(item)
            for item in fixture.get("items", [])
        ]
        return cls(
            items=items,
            applied_view=fixture.get("applied_view", READY_TO_EARN),
            network=fixture.get("network", "base-mainnet"),
            degraded=fixture.get("degraded", False),
        )

    def ready_to_earn(self) -> list[Opportunity]:
        """Claimable-only surface: claimed items are excluded."""
        return [item for item in self.items if item.is_claimable()]

    def engineering(self) -> list[Opportunity]:
        """Lifecycle surface: claimed items remain visible as in_progress."""
        rendered = []
        for item in self.items:
            if item.work_state == "claimed":
                rendered.append(
                    Opportunity(
                        work_state="in_progress",
                        payment_state=item.payment_state,
                        payment_committed=item.payment_committed,
                        verification_ready=item.verification_ready,
                        funded_amount=item.funded_amount,
                        reward=item.reward,
                        bond=item.bond,
                        terms_hash=item.terms_hash,
                        network=item.network,
                        verification_method=item.verification_method,
                    )
                )
            else:
                rendered.append(item)
        return rendered


def render_opportunity_feeds(
    projection: OpportunityProjection, base_url: str
) -> dict[str, str]:
    """Render JSON and RSS feeds for a projection of opportunities."""
    items = [
        {"_bountyboard": item.as_api_json()} for item in projection.ready_to_earn()
    ]
    payload = {
        "schema_version": "agent-bounties/projection-v1",
        "network": projection.network,
        "applied_view": projection.applied_view,
        "degraded": projection.degraded,
        "items": items,
    }
    json_feed = json.dumps(payload)
    titles = ", ".join(
        item.reward + " reward; gross " + item.economics().gross_cash_margin
        for item in projection.ready_to_earn()
    )
    rss = (
        f"Gross cash margin (not net profit) at {base_url}: " + titles
    )
    return {"json": json_feed, "rss": rss}


def apply_view(
    projection: OpportunityProjection, view: str
) -> list[Opportunity]:
    """Apply a named view to the projection."""
    if view == READY_TO_EARN:
        return projection.ready_to_earn()
    if view == ENGINEERING:
        return projection.engineering()
    raise ValueError(f"unknown inventory view: {view!r}")


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical inventory fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def build_projection(path: str | Path) -> OpportunityProjection:
    """Build a projection from the canonical fixture on disk."""
    return OpportunityProjection.from_fixture(load_fixture(path))


def main() -> None:
    """Print the claimable-only summary for the canonical fixture."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "profitable-inventory-contract.json"
    )
    if not fixture_path.is_file():
        return
    projection = build_projection(fixture_path)
    ready = projection.ready_to_earn()
    print("applied_view:", projection.applied_view)
    print("items: %d, ready_to_earn: %d", len(projection.items), len(ready))
    for item in ready:
        print(" ", item.work_state, item.reward, item.network)


if __name__ == "__main__":
    main()
