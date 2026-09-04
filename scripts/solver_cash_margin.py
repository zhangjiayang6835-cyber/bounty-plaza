"""Solver Cash Margin & Pre-Claim Economics Engine.
Resolves Issue #736: [Bounty] [DIRECT] Show solver cash margin before claim.

Acceptance Criteria:
- API and MCP output expose solver payout, refundable bond, external spend, and gross cash margin.
- Public copy never describes gross cash margin as guaranteed net profit.
- Filters and categorizes direct, standing-meta, and unprofitable inventory.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional


class InventoryType(str, Enum):
    DIRECT = "direct"
    STANDING_META = "standing_meta"
    RECURRING = "recurring"


LEGAL_DISCLAIMER_COPY: str = (
    "Gross cash margin represents the gross payout less mandatory external protocol spend. "
    "Gross cash margin is NOT guaranteed net profit. Final net yield depends on on-chain gas fluctuations, "
    "execution time, validator quorum consensus, and bond refund settlement."
)


@dataclass
class BountyEconomics:
    bounty_id: str
    inventory_type: InventoryType
    contract_address: str
    network: str
    payout_usdc: float
    refundable_bond_usdc: float
    required_external_spend_usdc: float = 0.0
    estimated_gas_usdc: float = 0.0
    status: str = "claimable"

    @property
    def gross_cash_margin_usdc(self) -> float:
        """Calculates Gross Cash Margin = Payout - Required External Spend.

        Refundable bond is excluded from expense calculation because it is returned upon verification.
        """
        return round(self.payout_usdc - self.required_external_spend_usdc, 4)

    @property
    def estimated_net_margin_usdc(self) -> float:
        """Estimated cash yield factoring in estimated gas expenditure."""
        return round(self.gross_cash_margin_usdc - self.estimated_gas_usdc, 4)

    @property
    def is_profitable(self) -> bool:
        """Returns True if the gross cash margin is strictly positive."""
        return self.gross_cash_margin_usdc > 0.0

    def to_api_response(self) -> Dict[str, Any]:
        """Exposes canonical machine-readable and human-readable economics payload."""
        return {
            "bounty_id": self.bounty_id,
            "contract_address": self.contract_address,
            "network": self.network,
            "inventory_type": self.inventory_type.value,
            "status": self.status,
            "economics": {
                "solver_payout_usdc": self.payout_usdc,
                "refundable_claim_bond_usdc": self.refundable_bond_usdc,
                "required_external_spend_usdc": self.required_external_spend_usdc,
                "estimated_gas_usdc": self.estimated_gas_usdc,
                "gross_cash_margin_usdc": self.gross_cash_margin_usdc,
                "estimated_net_margin_usdc": self.estimated_net_margin_usdc,
                "is_profitable": self.is_profitable,
            },
            "disclaimer": LEGAL_DISCLAIMER_COPY,
            "display_summary": (
                f"Payout: {self.payout_usdc:.2f} USDC | Bond: {self.refundable_bond_usdc:.2f} USDC (Refundable) | "
                f"External Spend: {self.required_external_spend_usdc:.2f} USDC | "
                f"Gross Cash Margin: {self.gross_cash_margin_usdc:.2f} USDC"
            ),
        }

    def to_mcp_tool_result(self) -> Dict[str, Any]:
        """Formats the economic analysis for Model Context Protocol (MCP) tool outputs."""
        api_data = self.to_api_response()
        # Verify strict adherence: public copy must never assert or describe gross margin as guaranteed net profit
        for val in [api_data["display_summary"]]:
            if "guaranteed net profit" in val.lower():
                raise ValueError("Violation of acceptance criteria: public copy must never claim guaranteed net profit.")

        return {
            "content": [
                {
                    "type": "text",
                    "text": (
                        f"## Bounty Pre-Claim Economics ({self.bounty_id})\n"
                        f"- **Network / Contract:** `{self.network}` / `{self.contract_address}`\n"
                        f"- **Solver Payout:** ${self.payout_usdc:.2f} USDC\n"
                        f"- **Refundable Claim Bond:** ${self.refundable_bond_usdc:.2f} USDC\n"
                        f"- **Required External Spend:** ${self.required_external_spend_usdc:.2f} USDC\n"
                        f"- **Gross Cash Margin:** ${self.gross_cash_margin_usdc:.2f} USDC\n\n"
                        f"> ⚠️ **Economic Notice:** {LEGAL_DISCLAIMER_COPY}"
                    ),
                }
            ],
            "metadata": api_data["economics"],
        }


class InventoryEconomicsFilter:
    """Filters and categorizes bounty candidate inventory based on economic viability."""

    @staticmethod
    def filter_profitable_inventory(
        bounties: List[BountyEconomics],
        min_gross_margin_usdc: float = 0.01,
    ) -> List[BountyEconomics]:
        """Filters out unprofitable or negative-margin bounties."""
        return [b for b in bounties if b.gross_cash_margin_usdc >= min_gross_margin_usdc]

    @staticmethod
    def categorize_inventory(
        bounties: List[BountyEconomics],
    ) -> Dict[str, List[BountyEconomics]]:
        """Groups bounties by direct, standing-meta, and unprofitable categories."""
        categorized: Dict[str, List[BountyEconomics]] = {
            "direct": [],
            "standing_meta": [],
            "unprofitable": [],
        }

        for b in bounties:
            if not b.is_profitable:
                categorized["unprofitable"].append(b)
            elif b.inventory_type == InventoryType.DIRECT:
                categorized["direct"].append(b)
            elif b.inventory_type == InventoryType.STANDING_META:
                categorized["standing_meta"].append(b)

        return categorized
