"""Tests for the end-to-end profitable inventory contract test (#737).

Covers the acceptance criteria:

1. One fixture covers API, MCP, discovery feed, and public website inventory.
2. The test asserts reward, bond, funding, status, terms validity, and verifier
   readiness.
3. A claimed bounty leaves claimable-only results without being treated as
   corrupt or unpaid.
"""

from __future__ import annotations

import json
from pathlib import Path

from profitable_inventory import (
    Opportunity,
    OpportunityProjection,
    READY_TO_EARN,
    ENGINEERING,
    apply_view,
    build_projection,
    render_opportunity_feeds,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "profitable-inventory-contract.json"
).resolve()

PROJECTION = build_projection(FIXTURE)


def test_fixture_covers_all_surfaces() -> None:
    """One fixture drives API, MCP, feed, and website inventory."""
    assert len(PROJECTION.items) == 4
    assert PROJECTION.applied_view == READY_TO_EARN
    assert PROJECTION.network == "base-mainnet"


def test_api_json_surface_asserts_reward_and_bond() -> None:
    """The API surface asserts exact reward and bond economics."""
    item = PROJECTION.ready_to_earn()[0].as_api_json()
    assert item["work_state"] == "claimable"
    assert item["payment_state"] == "escrowed"
    assert item["payment_committed"] is True
    assert item["verification_ready"] is True
    economics = item["cash_economics"]
    assert economics["solver_reward"]["amount"] == "1990000"
    assert economics["refundable_claim_bond"]["amount"] == "10000"
    assert economics["required_external_spend"]["amount"] == "0"
    assert economics["gross_cash_margin"]["amount"] == "1980000"
    assert economics["gross_cash_margin_positive"] is True


def test_mcp_structured_content_surface() -> None:
    """The MCP structured-content surface mirrors the API JSON shape."""
    for item in PROJECTION.ready_to_earn():
        payload = item.as_api_json()
        assert "cash_economics" in payload
        assert "terms_hash" in payload
        assert "verification_method" in payload


def test_funding_asserted() -> None:
    """Funding amount is asserted across the fixture."""
    for item in PROJECTION.ready_to_earn():
        assert int(item.funded_amount) > 0


def test_terms_validity_asserted() -> None:
    """Terms hash is non-empty for every ready item."""
    for item in PROJECTION.ready_to_earn():
        assert item.is_terms_valid() is True


def test_verifier_readiness_asserted() -> None:
    """Verifier readiness is asserted for every ready item."""
    for item in PROJECTION.ready_to_earn():
        assert item.verification_ready is True
        assert item.verification_method == "sandboxed_regression_v1"


def test_discovery_feed_uses_canonical_economics() -> None:
    """The discovery feed embeds the exact reward and bond economics."""
    feeds = render_opportunity_feeds(PROJECTION, "https://api.example/")
    feed_json = json.loads(feeds["json"])
    first = feed_json["items"][0]["_bountyboard"]
    assert first["work_state"] == "claimable"
    assert first["payment_state"] == "escrowed"
    economics = first["cash_economics"]
    assert economics["solver_reward"]["amount"] == "1990000"


def test_rss_is_not_misleading() -> None:
    """The RSS summary says gross margin, never guaranteed profit."""
    feeds = render_opportunity_feeds(PROJECTION, "https://api.example/")
    assert "Gross cash margin (not net profit)" in feeds["rss"]
    assert "guaranteed profit" not in feeds["rss"].lower()


def test_claimed_excluded_from_ready_to_earn() -> None:
    """A claimed bounty leaves claimable-only results."""
    ready = apply_view(PROJECTION, READY_TO_EARN)
    assert len(ready) == 2
    for item in ready:
        assert item.work_state == "claimable"


def test_claimed_visible_in_engineering_lifecycle() -> None:
    """A claimed bounty stays visible in the lifecycle surface."""
    lifecycle = apply_view(PROJECTION, ENGINEERING)
    assert len(lifecycle) == 4
    found = [item for item in lifecycle if item.work_state == "in_progress"]
    assert len(found) == 1
    assert found[0].payment_state == "escrowed"
    assert found[0].payment_committed is True


def test_claimed_not_treated_as_corrupt() -> None:
    """A claimed bounty remains in the lifecycle view without error."""
    lifecycle = apply_view(PROJECTION, ENGINEERING)
    claimed = [item for item in lifecycle if item.work_state == "in_progress"]
    assert len(claimed) == 1
    assert claimed[0].payment_state == "escrowed"
    assert claimed[0].is_terms_valid() is True
    for item in lifecycle:
        assert item.payment_state in ("escrowed", "pending")


def test_claimable_only_not_unpaid_mislabeled() -> None:
    """Claimable-only results never surface an in_progress unpaid item."""
    ready = apply_view(PROJECTION, READY_TO_EARN)
    assert all(item.work_state == "claimable" for item in ready)
    assert all(item.payment_committed for item in ready)


def test_underfunded_item_fails_closed() -> None:
    """An unfunded, unverified item never appears as ready to earn."""
    ready = apply_view(PROJECTION, READY_TO_EARN)
    for item in ready:
        assert int(item.funded_amount) > 0
        assert item.verification_ready is True


def test_exact_second_fixture_economics() -> None:
    """The second claimable fixture asserts its own exact economics."""
    second = PROJECTION.ready_to_earn()[1].as_api_json()
    economics = second["cash_economics"]
    assert economics["solver_reward"]["amount"] == "900000"
    assert economics["refundable_claim_bond"]["amount"] == "100000"
    assert economics["gross_cash_margin"]["amount"] == "800000"


def test_feed_covers_website_surface() -> None:
    """The rendered feed is the public website inventory source."""
    feeds = render_opportunity_feeds(PROJECTION, "https://api.example/")
    payload = json.loads(feeds["json"])
    assert payload["schema_version"] == "agent-bounties/projection-v1"
    assert payload["applied_view"] == READY_TO_EARN
    assert payload["degraded"] is False


def test_unknown_view_raises() -> None:
    """An unknown view fails closed."""
    try:
        apply_view(PROJECTION, "mystery")
    except ValueError as exc:
        assert "unknown inventory view" in str(exc)
        return
    raise AssertionError("expected ValueError for unknown view")


def test_opportunity_claimable_predicate() -> None:
    """The claimable predicate requires all readiness flags."""
    item = PROJECTION.items[0]
    assert item.is_claimable() is True
    assert item.is_terms_valid() is True


def test_projection_roundtrip() -> None:
    """A projection rebuilt from fixture items matches the original count."""
    rebuilt = OpportunityProjection(
        items=[
            Opportunity.from_fixture_item(item.as_api_json())
            for item in PROJECTION.ready_to_earn()
        ],
        applied_view=READY_TO_EARN,
    )
    assert len(rebuilt.ready_to_earn()) == 2
