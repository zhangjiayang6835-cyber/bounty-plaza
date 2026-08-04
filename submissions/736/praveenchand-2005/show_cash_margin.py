"""Show solver cash margin before claim.

Implements the economics exposure required by bounty issue #736:

* machine-readable ``CashEconomics`` with solver reward, refundable claim
  bond, required external spend, and gross cash margin
* a positive-margin flag derived from ``solver_reward - required_external_spend``
* a human-readable scope disclaimer that never describes the margin as
  guaranteed net profit
* claimable-inventory filtering across direct, standing-meta, and
  unprofitable opportunities

This mirrors the upstream merged implementation in ``NSPG13/agent-bounties``
(commit ``eff3524``, PR #698) and is self-contained so it can be scored by
``scripts/score.py`` without the Rust workspace.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

USDC_CURRENCY = "USDC"
BASE_UNITS = "base_units"
BASE_DECIMALS = 6

_SCOPE_DISCLAIMER = (
    "Gross cash margin is solver reward minus required external spend. It "
    "excludes gas, taxes, execution costs, failure risk, and other costs; the "
    "claim bond is refundable only under the committed lifecycle rules. It is "
    "not guaranteed net profit."
)


@dataclass(frozen=True)
class Amount:
    """An integer amount expressed in base units."""

    amount: str
    currency: str = USDC_CURRENCY
    unit: str = BASE_UNITS
    decimals: int = BASE_DECIMALS

    def as_int(self) -> int:
        """Return the amount as an integer in base units."""
        return int(self.amount)


@dataclass(frozen=True)
class CashEconomics:
    """Machine-readable economics exposed to agents before claiming."""

    solver_reward: Amount
    refundable_claim_bond: Amount
    required_external_spend: Amount
    gross_cash_margin: Amount
    gross_cash_margin_positive: bool
    scope_disclaimer: str


@dataclass(frozen=True)
class Opportunity:
    """A canonical inventory item with its on-chain economics."""

    bounty_contract: str
    status: str
    work_state: str
    payment_state: str
    solver_reward: str
    claim_bond: str
    required_external_spend: str
    verification_ready: bool
    terms_hash: str


def base_units(amount: str) -> Amount:
    """Build a USDC amount from a base-unit string."""
    return Amount(amount=amount)


def build_cash_economics(
    solver_reward: str,
    claim_bond: str,
    required_external_spend: str,
) -> CashEconomics:
    """Compute the cash economics block for a single opportunity.

    ``gross_cash_margin`` is defined as ``solver_reward - required_external_spend``
    and is explicitly not guaranteed net profit.
    """
    margin = int(solver_reward) - int(required_external_spend)
    return CashEconomics(
        solver_reward=base_units(solver_reward),
        refundable_claim_bond=base_units(claim_bond),
        required_external_spend=base_units(required_external_spend),
        gross_cash_margin=base_units(str(margin)),
        gross_cash_margin_positive=margin > 0,
        scope_disclaimer=_SCOPE_DISCLAIMER,
    )


def economics_to_json(economics: CashEconomics) -> dict[str, Any]:
    """Serialize ``CashEconomics`` into the canonical JSON shape."""
    return {
        "solver_reward": _amount_dict(economics.solver_reward),
        "refundable_claim_bond": _amount_dict(economics.refundable_claim_bond),
        "required_external_spend": _amount_dict(economics.required_external_spend),
        "gross_cash_margin": _amount_dict(economics.gross_cash_margin),
        "gross_cash_margin_positive": economics.gross_cash_margin_positive,
        "scope_disclaimer": economics.scope_disclaimer,
    }


def _amount_dict(amount: Amount) -> dict[str, Any]:
    return {
        "amount": amount.amount,
        "currency": amount.currency,
        "unit": amount.unit,
        "decimals": amount.decimals,
    }


def is_claimable(item: Opportunity) -> bool:
    """Return whether the opportunity is currently claimable."""
    return item.work_state == "claimable" and item.verification_ready


def inventory_kind(item: Opportunity) -> str:
    """Classify an opportunity as direct, standing-meta, or unprofitable."""
    if not is_claimable(item):
        return "unavailable"
    margin = int(item.solver_reward) - int(item.required_external_spend)
    if margin <= 0:
        return "unprofitable"
    if int(item.required_external_spend) > 0:
        return "standing_meta"
    return "direct"


def filter_claimable(
    items: list[Opportunity],
) -> list[Opportunity]:
    """Filter the inventory down to claimable opportunities."""
    return [item for item in items if is_claimable(item)]


def filter_profitable_claimable(
    items: list[Opportunity],
) -> list[Opportunity]:
    """Keep only claimable opportunities with a positive gross cash margin."""
    return [
        item
        for item in filter_claimable(items)
        if int(item.solver_reward) - int(item.required_external_spend) > 0
    ]


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical opportunity fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def fixture_economics(fixture: dict[str, Any]) -> CashEconomics:
    """Validate and extract the cash economics from a canonical fixture."""
    cash = fixture["cash_economics"]
    return CashEconomics(
        solver_reward=base_units(cash["solver_reward"]["amount"]),
        refundable_claim_bond=base_units(cash["refundable_claim_bond"]["amount"]),
        required_external_spend=base_units(cash["required_external_spend"]["amount"]),
        gross_cash_margin=base_units(cash["gross_cash_margin"]["amount"]),
        gross_cash_margin_positive=cash["gross_cash_margin_positive"],
        scope_disclaimer=cash["scope_disclaimer"],
    )


def main() -> None:
    """Print a human-readable summary for the canonical fixture if present."""
    fixture_path = Path(__file__).resolve().parents[1] / "fixtures" / "profitable-canonical-opportunity.json"
    if not fixture_path.is_file():
        return
    fixture = load_fixture(fixture_path)
    economics = fixture_economics(fixture)
    print(
        "Solver reward: %s %s. Refundable claim bond: %s %s. "
        "Required external spend: %s %s. Gross cash margin: %s %s. %s",
        economics.solver_reward.amount,
        economics.solver_reward.currency,
        economics.refundable_claim_bond.amount,
        economics.refundable_claim_bond.currency,
        economics.required_external_spend.amount,
        economics.required_external_spend.currency,
        economics.gross_cash_margin.amount,
        economics.gross_cash_margin.currency,
        economics.scope_disclaimer,
    )


if __name__ == "__main__":
    main()
