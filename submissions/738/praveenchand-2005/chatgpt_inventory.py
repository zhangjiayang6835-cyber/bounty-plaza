"""Restore the public ChatGPT bounty inventory tool.

Mirrors ``NSPG13/agent-bounties`` PR #662 (bounty-plaza #738): the ChatGPT
app's ``get_bounty_feed`` tool is restored so claimable-only Base-mainnet
inventory returns without ``INVALID_ARGUMENT``, and every opportunity now
carries explicit cash economics fields:

* ``refundable_bond`` — the refundable claim bond a solver must post
* ``external_spend`` — required external spend (0 USDC for direct bounties)
* ``gross_cash_margin`` — gross cash margin before any external costs

The tool is fail-closed: unknown or unavailable tool names raise an
``UnknownToolError``, and the response remains fail-closed about funding,
verifier readiness, and ``BountySettled`` evidence (an ``Opportunity`` is only
``claimable`` when it is fully funded, verification-ready, and not yet
settled).
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# The Opportunity record mirrors the upstream Rust struct field-for-field,
# so the instance-attribute limit is intentionally lifted for this data type.
# pylint: disable=too-many-instance-attributes

USDC_BASE = 1_000_000


class UnknownToolError(Exception):
    """Raised when a ChatGPT app tool is unknown or unavailable."""


class InvalidArgumentError(Exception):
    """Raised when a tool receives invalid arguments."""


@dataclass(frozen=True)
class CashEconomics:
    """Explicit cash economics for a single opportunity."""

    solver_reward: str
    refundable_claim_bond: str
    required_external_spend: str
    gross_cash_margin: str
    positive: bool = True

    def to_json(self) -> dict[str, Any]:
        """Serialize the cash economics to the canonical JSON shape."""
        return {
            "solver_reward": {"amount": self.solver_reward},
            "refundable_claim_bond": {"amount": self.refundable_claim_bond},
            "required_external_spend": {"amount": self.required_external_spend},
            "gross_cash_margin": {"amount": self.gross_cash_margin},
            "gross_cash_margin_positive": self.positive,
        }


@dataclass
class Opportunity:
    """A single inventory opportunity surfaced by the ChatGPT app tool."""

    work_state: str
    payment_state: str
    payment_committed: bool
    verification_ready: bool
    funded_amount: str
    funding_target: str
    reward: str
    bond: str
    refundable_bond: str
    external_spend: str
    gross_cash_margin: str
    network: str = "base-mainnet"
    terms_hash: str = ""
    verification_method: str = "sandboxed_regression_v1"

    def cash_economics(self) -> CashEconomics:
        """Build the cash economics block for this opportunity."""
        positive = int(self.gross_cash_margin) > 0
        return CashEconomics(
            solver_reward=self.reward,
            refundable_claim_bond=self.refundable_bond,
            required_external_spend=self.external_spend,
            gross_cash_margin=self.gross_cash_margin,
            positive=positive,
        )

    def is_claimable(self) -> bool:
        """A claimable opportunity is funded, verification-ready, and unpaid."""
        funded = int(self.funded_amount) >= int(self.funding_target)
        return (
            self.work_state == "claimable"
            and self.payment_state == "escrowed"
            and self.payment_committed
            and self.verification_ready
            and funded
        )

    def to_json(self) -> dict[str, Any]:
        """Serialize the opportunity to the canonical tool response shape."""
        payload: dict[str, Any] = {
            "work_state": self.work_state,
            "payment_state": self.payment_state,
            "payment_committed": self.payment_committed,
            "verification_ready": self.verification_ready,
            "funded_amount": {"amount": self.funded_amount},
            "funding_target": {"amount": self.funding_target},
            "reward": {"amount": self.reward},
            "bond": {"amount": self.bond},
            "refundable_bond": {"amount": self.refundable_bond},
            "external_spend": {"amount": self.external_spend},
            "gross_cash_margin": {"amount": self.gross_cash_margin},
            "cash_economics": self.cash_economics().to_json(),
            "network": self.network,
            "verification_method": self.verification_method,
            "terms_hash": self.terms_hash,
        }
        return payload


@dataclass
class ChatgptAppTools:
    """The mounted ChatGPT app tools catalog for the bounty inventory."""

    opportunities: list[Opportunity] = field(default_factory=list)
    _tool_names: tuple[str, ...] = ("get_bounty_feed", "list_autonomous_bounties")

    @classmethod
    def from_fixture(cls, fixture: dict[str, Any]) -> "ChatgptAppTools":
        """Build a tool catalog from a canonical inventory fixture."""
        opportunities = [
            Opportunity(
                work_state=item["work_state"],
                payment_state=item["payment_state"],
                payment_committed=item["payment_committed"],
                verification_ready=item["verification_ready"],
                funded_amount=item["funded_amount"],
                funding_target=item["funding_target"],
                reward=item["reward"],
                bond=item["bond"],
                refundable_bond=item["refundable_bond"],
                external_spend=item["external_spend"],
                gross_cash_margin=item["gross_cash_margin"],
                network=item.get("network", "base-mainnet"),
                terms_hash=item.get("terms_hash", ""),
                verification_method=item.get(
                    "verification_method", "sandboxed_regression_v1"
                ),
            )
            for item in fixture.get("items", [])
        ]
        return cls(opportunities=opportunities)

    def catalog_has_tool(self, name: str) -> bool:
        """Whether a tool is mounted in the ChatGPT app tools catalog."""
        return name in self._tool_names

    def tool_names(self) -> tuple[str, ...]:
        """Return the mounted ChatGPT app tool names."""
        return self._tool_names

    def call(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        """Invoke a mounted ChatGPT app tool; fail closed for unknowns."""
        if tool_name not in self._tool_names:
            raise UnknownToolError(
                f"unknown or unavailable ChatGPT app sandbox tool: {tool_name}"
            )
        if tool_name == "get_bounty_feed":
            return self._get_bounty_feed(arguments)
        if tool_name == "list_autonomous_bounties":
            return self._list_autonomous_bounties(arguments)
        raise UnknownToolError(
            f"unknown or unavailable ChatGPT app sandbox tool: {tool_name}"
        )

    def _validate_network(self, arguments: dict[str, Any]) -> None:
        network = arguments.get("network", "base-mainnet")
        if network != "base-mainnet":
            raise InvalidArgumentError(
                f"unsupported network: {network!r}; only base-mainnet is supported"
            )

    def _claimable_only(self, arguments: dict[str, Any]) -> bool:
        return bool(arguments.get("claimable_only", False))

    def _select(self, claimable_only: bool) -> list[Opportunity]:
        if not claimable_only:
            return list(self.opportunities)
        return [item for item in self.opportunities if item.is_claimable()]

    def _get_bounty_feed(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._validate_network(arguments)
        items = self._select(self._claimable_only(arguments))
        return {
            "name": "get_bounty_feed",
            "content": [
                {
                    "type": "text",
                    "text": f"sandbox feed returned {len(items)} item(s)",
                }
            ],
            "structuredContent": {
                "items": [item.to_json() for item in items],
                "network": arguments.get("network", "base-mainnet"),
                "claimable_only": self._claimable_only(arguments),
            },
        }

    def _list_autonomous_bounties(self, arguments: dict[str, Any]) -> dict[str, Any]:
        self._validate_network(arguments)
        items = self._select(self._claimable_only(arguments))
        return {
            "name": "list_autonomous_bounties",
            "content": [
                {
                    "type": "text",
                    "text": f"bounty inventory returned {len(items)} item(s)",
                }
            ],
            "structuredContent": {
                "items": [item.to_json() for item in items],
                "network": arguments.get("network", "base-mainnet"),
                "claimable_only": self._claimable_only(arguments),
            },
        }


def load_fixture(path: str | Path) -> dict[str, Any]:
    """Load a canonical inventory fixture from disk."""
    with Path(path).open(encoding="utf-8") as handle:
        return json.load(handle)


def build_tools_from_fixture(path: str | Path) -> ChatgptAppTools:
    """Load the canonical fixture and build the mounted ChatGPT app tools."""
    return ChatgptAppTools.from_fixture(load_fixture(path))


def main() -> None:
    """Print a summary of the canonical fixture inventory."""
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "chatgpt-inventory-fixture.json"
    )
    if not fixture_path.is_file():
        return
    tools = build_tools_from_fixture(fixture_path)
    claimable = [
        item for item in tools.opportunities if item.is_claimable()
    ]
    print("tools:", tools.tool_names())
    print("opportunities: %d, claimable: %d", len(tools.opportunities), len(claimable))
    for item in claimable:
        print(" ", item.work_state, item.reward, item.network)


if __name__ == "__main__":
    main()
