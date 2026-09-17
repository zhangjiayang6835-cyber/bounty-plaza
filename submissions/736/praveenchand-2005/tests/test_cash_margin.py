"""Tests for the cash-margin economics exposure.

Covers the acceptance criteria for bounty #736:

1. API/MCP-style output exposes reward, refundable bond, external spend,
   and gross cash margin.
2. Public copy never describes gross cash margin as guaranteed net profit.
3. Inventory filtering covers direct, standing-meta, and unprofitable items.
"""

from __future__ import annotations

import json
from pathlib import Path

from show_cash_margin import (
    Opportunity,
    build_cash_economics,
    economics_to_json,
    filter_claimable,
    filter_profitable_claimable,
    inventory_kind,
    is_claimable,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "profitable-canonical-opportunity.json"
).resolve()


def make_opportunity(
    solver_reward: str = "1990000",
    claim_bond: str = "10000",
    required_external_spend: str = "0",
    work_state: str = "claimable",
    verification_ready: bool = True,
) -> Opportunity:
    """Build a canonical opportunity with configurable economics."""
    return Opportunity(
        bounty_contract="0xf2e47a253988e98f535ab60f4b9bd7f8975c1263",
        status="claimable",
        work_state=work_state,
        payment_state="escrowed",
        solver_reward=solver_reward,
        claim_bond=claim_bond,
        required_external_spend=required_external_spend,
        verification_ready=verification_ready,
        terms_hash="0x4444444444444444444444444444444444444444444444444444444444444444",
    )


def test_direct_opportunity_exposes_all_four_amounts() -> None:
    """A direct opportunity exposes reward, bond, spend, and margin."""
    item = make_opportunity()
    economics = build_cash_economics(
        item.solver_reward, item.claim_bond, item.required_external_spend
    )
    payload = economics_to_json(economics)
    for field in (
        "solver_reward",
        "refundable_claim_bond",
        "required_external_spend",
        "gross_cash_margin",
    ):
        assert field in payload
    assert payload["solver_reward"]["amount"] == "1990000"
    assert payload["refundable_claim_bond"]["amount"] == "10000"
    assert payload["required_external_spend"]["amount"] == "0"
    assert payload["gross_cash_margin"]["amount"] == "1990000"
    assert payload["gross_cash_margin_positive"] is True


def test_gross_cash_margin_is_reward_minus_external_spend() -> None:
    """Gross cash margin equals solver reward minus required external spend."""
    economics = build_cash_economics("1990000", "10000", "500000")
    assert economics.gross_cash_margin.amount == "1490000"
    assert economics.gross_cash_margin_positive is True


def test_negative_margin_is_flagged_but_still_reported() -> None:
    """An unprofitable opportunity reports its negative margin honestly."""
    economics = build_cash_economics("1990000", "10000", "2500000")
    assert economics.gross_cash_margin.amount == "-510000"
    assert economics.gross_cash_margin_positive is False


def test_scope_disclaimer_never_claims_guaranteed_net_profit() -> None:
    """Public copy must not describe the margin as guaranteed net profit."""
    economics = build_cash_economics("1990000", "10000", "0")
    disclaimer = economics.scope_disclaimer.lower()
    assert "gross cash margin" in disclaimer
    assert "not guaranteed net profit" in disclaimer
    assert "solver reward minus required external spend" in disclaimer


def test_direct_inventory_filtering() -> None:
    """Direct claimable opportunities are included and classified direct."""
    item = make_opportunity()
    assert is_claimable(item)
    assert inventory_kind(item) == "direct"
    assert filter_claimable([item]) == [item]


def test_standing_meta_inventory_filtering() -> None:
    """Standing-meta parents require external spend and remain claimable."""
    item = make_opportunity(required_external_spend="500000")
    assert is_claimable(item)
    assert inventory_kind(item) == "standing_meta"
    assert filter_claimable([item]) == [item]


def test_unprofitable_inventory_is_filtered_from_profitable_list() -> None:
    """Unprofitable items are excluded from the profitable claimable list."""
    profitable = make_opportunity(required_external_spend="0")
    unprofitable = make_opportunity(required_external_spend="3000000")
    items = [profitable, unprofitable]
    assert inventory_kind(unprofitable) == "unprofitable"
    assert filter_claimable(items) == [profitable, unprofitable]
    assert filter_profitable_claimable(items) == [profitable]


def test_in_progress_items_are_not_claimable() -> None:
    """Only claimable work-state items are eligible."""
    item = make_opportunity(work_state="in_progress")
    assert not is_claimable(item)
    assert inventory_kind(item) == "unavailable"
    assert filter_claimable([item]) == []


def test_verification_required_for_claimability() -> None:
    """Verification readiness gates claimability."""
    item = make_opportunity(verification_ready=False)
    assert not is_claimable(item)
    assert inventory_kind(item) == "unavailable"


def test_fixture_matches_inventory_contract() -> None:
    """The canonical fixture satisfies every public inventory surface."""
    if not FIXTURE.is_file():
        return
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert fixture["reward"]["amount"] == "1990000"
    assert fixture["bond"]["amount"] == "10000"
    assert fixture["funded_amount"]["amount"] == fixture["funding_target"]["amount"]
    assert fixture["source_status"] == "claimable"
    assert fixture["work_state"] == "claimable"
    assert fixture["verification_ready"] is True
    cash = fixture["cash_economics"]
    assert int(cash["gross_cash_margin"]["amount"]) > 0
    assert cash["gross_cash_margin_positive"] is True
    assert "not guaranteed net profit" in cash["scope_disclaimer"]
    assert (
        int(cash["solver_reward"]["amount"])
        - int(cash["required_external_spend"]["amount"])
        == int(cash["gross_cash_margin"]["amount"])
    )


def test_mcp_surface_fields_exist() -> None:
    """MCP-style inventory rows expose the economics fields."""
    item = make_opportunity()
    row = {
        "bounty_id": item.bounty_contract,
        "bounty_contract": item.bounty_contract,
        "status": item.status,
        "solver_reward": item.solver_reward,
        "claim_bond": item.claim_bond,
        "required_external_spend": item.required_external_spend,
        "gross_cash_margin": build_cash_economics(
            item.solver_reward, item.claim_bond, item.required_external_spend
        ).gross_cash_margin.amount,
        "terms_hash": item.terms_hash,
        "verification_ready": item.verification_ready,
    }
    for field in (
        "solver_reward",
        "claim_bond",
        "required_external_spend",
        "gross_cash_margin",
    ):
        assert field in row
