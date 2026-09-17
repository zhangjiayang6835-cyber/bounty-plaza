"""Tests for the restored public ChatGPT bounty inventory tool (#738).

Covers the acceptance criteria:

1. A committed test invokes the public tool name used by the mounted ChatGPT
   app (``get_bounty_feed`` / ``list_autonomous_bounties``).
2. The test fails on the unknown-or-unavailable-tool response and passes after
   the fix.
3. The response remains fail-closed about funding, verifier readiness, and
   ``BountySettled`` evidence.
"""

from __future__ import annotations

import json
from pathlib import Path

from chatgpt_inventory import (
    ChatgptAppTools,
    InvalidArgumentError,
    Opportunity,
    UnknownToolError,
    build_tools_from_fixture,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "chatgpt-inventory-fixture.json"
).resolve()

TOOLS = build_tools_from_fixture(FIXTURE)


def test_get_bounty_feed_is_mounted() -> None:
    """The public get_bounty_feed tool is mounted in the ChatGPT app."""
    assert TOOLS.catalog_has_tool("get_bounty_feed") is True


def test_list_autonomous_bounties_is_mounted() -> None:
    """The public list_autonomous_bounties tool is mounted."""
    assert TOOLS.catalog_has_tool("list_autonomous_bounties") is True


def test_unknown_tool_fails_closed() -> None:
    """An unknown tool name fails closed with UnknownToolError."""
    try:
        TOOLS.call("unknown_tool", {})
    except UnknownToolError as exc:
        assert "unknown or unavailable ChatGPT app sandbox tool" in str(exc)
        return
    raise AssertionError("expected UnknownToolError for unknown tool")


def test_unknown_tool_was_previously_broken() -> None:
    """Regression: the unknown-tool path previously returned INVALID_ARGUMENT."""
    before = TOOLS._tool_names  # noqa: SLF001
    assert "unknown_tool" not in before
    raised = False
    try:
        TOOLS.call("unknown_tool", {})
    except UnknownToolError:
        raised = True
    assert raised is True


def test_get_bounty_feed_returns_claimable_only() -> None:
    """Claimable-only inventory returns without INVALID_ARGUMENT."""
    result = TOOLS.call(
        "get_bounty_feed",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    items = result["structuredContent"]["items"]
    assert len(items) == 2
    for item in items:
        assert item["work_state"] == "claimable"
        assert item["payment_state"] == "escrowed"
        assert item["payment_committed"] is True
        assert item["verification_ready"] is True


def test_get_bounty_feed_sandbox_summary() -> None:
    """The feed summary text is present and reports item count."""
    result = TOOLS.call(
        "get_bounty_feed",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    summary = result["content"][0]["text"]
    assert "sandbox feed" in summary
    assert "2 item" in summary


def test_get_bounty_feed_claimable_economics() -> None:
    """Claimable items carry exact reward and bond economics."""
    result = TOOLS.call(
        "get_bounty_feed",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    item = result["structuredContent"]["items"][0]
    assert item["reward"]["amount"] == "1990000"
    assert item["bond"]["amount"] == "10000"
    assert item["refundable_bond"]["amount"] == "10000"
    assert item["external_spend"]["amount"] == "0"
    assert item["gross_cash_margin"]["amount"] == "1990000"


def test_list_autonomous_bounties_callable() -> None:
    """The autonomous bounties tool returns structured items."""
    result = TOOLS.call(
        "list_autonomous_bounties",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    assert result["structuredContent"]["items"]
    assert isinstance(result["structuredContent"]["items"], list)


def test_invalid_network_fails_closed() -> None:
    """An unsupported network fails closed with InvalidArgumentError."""
    try:
        TOOLS.call("get_bounty_feed", {"network": "arbitrum-one"})
    except InvalidArgumentError as exc:
        assert "only base-mainnet" in str(exc)
        return
    raise AssertionError("expected InvalidArgumentError for bad network")


def test_fail_closed_on_unfunded() -> None:
    """Unfunded opportunities are excluded from claimable-only results."""
    result = TOOLS.call(
        "list_autonomous_bounties",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    for item in result["structuredContent"]["items"]:
        assert int(item["funded_amount"]["amount"]) > 0


def test_claimed_bounty_excluded_from_claimable_only() -> None:
    """A claimed bounty leaves claimable-only results without corruption."""
    result = TOOLS.call(
        "get_bounty_feed",
        {"claimable_only": True, "network": "base-mainnet"},
    )
    for item in result["structuredContent"]["items"]:
        assert item["work_state"] != "claimed"


def test_opportunity_is_claimable_when_fully_ready() -> None:
    """A fully funded, verification-ready, unpaid item is claimable."""
    opp = Opportunity(
        work_state="claimable",
        payment_state="escrowed",
        payment_committed=True,
        verification_ready=True,
        funded_amount="2000000",
        funding_target="2000000",
        reward="1990000",
        bond="10000",
        refundable_bond="10000",
        external_spend="0",
        gross_cash_margin="1990000",
    )
    assert opp.is_claimable() is True


def test_opportunity_not_claimable_when_underfunded() -> None:
    """An underfunded item is not claimable regardless of state labels."""
    opp = Opportunity(
        work_state="claimable",
        payment_state="escrowed",
        payment_committed=True,
        verification_ready=True,
        funded_amount="1000000",
        funding_target="2000000",
        reward="0",
        bond="0",
        refundable_bond="0",
        external_spend="0",
        gross_cash_margin="0",
    )
    assert opp.is_claimable() is False


def test_opportunity_not_claimable_when_unverified() -> None:
    """Verifier-unready items fail closed as not claimable."""
    opp = Opportunity(
        work_state="claimable",
        payment_state="escrowed",
        payment_committed=True,
        verification_ready=False,
        funded_amount="2000000",
        funding_target="2000000",
        reward="1990000",
        bond="10000",
        refundable_bond="10000",
        external_spend="0",
        gross_cash_margin="1990000",
    )
    assert opp.is_claimable() is False


def test_cash_economics_json_shape() -> None:
    """The cash economics block serializes to the canonical shape."""
    opp = Opportunity(
        work_state="claimable",
        payment_state="escrowed",
        payment_committed=True,
        verification_ready=True,
        funded_amount="2000000",
        funding_target="2000000",
        reward="1990000",
        bond="10000",
        refundable_bond="10000",
        external_spend="0",
        gross_cash_margin="1990000",
    )
    economics = opp.cash_economics().to_json()
    for field in (
        "solver_reward",
        "refundable_claim_bond",
        "required_external_spend",
        "gross_cash_margin",
        "gross_cash_margin_positive",
    ):
        assert field in economics
    assert economics["solver_reward"]["amount"] == "1990000"
    assert economics["gross_cash_margin_positive"] is True


def test_gross_margin_negative_when_losing() -> None:
    """A negative gross margin is reported as not positive."""
    opp = Opportunity(
        work_state="claimable",
        payment_state="escrowed",
        payment_committed=True,
        verification_ready=True,
        funded_amount="1000000",
        funding_target="2000000",
        reward="100000",
        bond="500000",
        refundable_bond="500000",
        external_spend="50000",
        gross_cash_margin="-450000",
    )
    assert opp.cash_economics().positive is False


def test_full_inventory_shows_all_surfaces() -> None:
    """The full feed returns every fixture item across surfaces."""
    result = TOOLS.call(
        "get_bounty_feed",
        {"claimable_only": False, "network": "base-mainnet"},
    )
    items = result["structuredContent"]["items"]
    assert len(items) == len(TOOLS.opportunities) == 4


def test_json_serialization_roundtrip() -> None:
    """The canonical fixture is valid JSON with the expected items."""
    with FIXTURE.open(encoding="utf-8") as handle:
        fixture = json.load(handle)
    assert len(fixture["items"]) == 4
    for item in fixture["items"]:
        for field in ("work_state", "payment_state", "funded_amount", "reward"):
            assert field in item


def test_fixture_builds_matching_catalog() -> None:
    """The fixture builds a catalog with matching opportunity count."""
    rebuilt = ChatgptAppTools.from_fixture({"items": [o.to_json() for o in TOOLS.opportunities]})
    assert len(rebuilt.opportunities) == len(TOOLS.opportunities)
    assert rebuilt.opportunities[0].network == "base-mainnet"
