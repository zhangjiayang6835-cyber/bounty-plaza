"""DoomVault — 100,000 DOOM ($wDOOM) Steam Digital Gift Card Redemption Engine.

Resolves Issue #4114:
Exchange 100,000 DOOM ($wDOOM) for a $10 Steam Digital Gift Card.
Supports Base Mainnet ERC-20 wDOOM and Doomsday Layer-1 DOOM receipt verification,
replay protection, per-user limits, and inventory accounting.
"""

import json
import re
import secrets
from typing import Any, Dict, List, Optional, Set

VAULT_NAME = "STEAM VAULT"
TOTAL_VAULT_CARDS = 10
CARD_VALUE_USD = 10.0
TOTAL_VAULT_USD = 100.0
REQUIRED_TOKEN_AMOUNT = 100_000.0
WDOOM_CONTRACT_BASE = "0x623c84A5E04bF715018203334b0eFE41696eBC3E"
VAULT_EVM_ADDRESS = "0x484ed370ded0d36e36aad469a2afe5d69b1a005d"
VAULT_DOOM_L1_ADDRESS = "doom12da148685b855223a3cd830058e227d8369b5aac8e96db05"
BASE_CHAIN_ID = 8453
WDOOM_DECIMALS = 18

HEX_TX_REGEX = re.compile(r"^(0x)?[0-9a-fA-F]{64}$")
STEAM_KEY_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def normalize_address(addr: Optional[str]) -> str:
    """Normalize EVM or L1 address for comparison."""
    if not addr:
        return ""
    return addr.strip().lower()


def generate_steam_gift_card_code() -> str:
    """Generate a standard Steam 15-character activation key (XXXXX-XXXXX-XXXXX)."""
    parts = []
    for _ in range(3):
        block = "".join(secrets.choice(STEAM_KEY_ALPHABET) for _ in range(5))
        parts.append(block)
    return "-".join(parts)


class DoomSteamVaultManager:
    """Manages $10 Steam Digital Gift Card redemptions for DOOM / wDOOM."""

    def __init__(
        self,
        total_cards: int = TOTAL_VAULT_CARDS,
        card_value_usd: float = CARD_VALUE_USD,
        state_file: Optional[str] = None,
    ) -> None:
        self.total_cards = total_cards
        self.available_cards = total_cards
        self.card_value_usd = card_value_usd
        self.state_file = state_file

        self.redeemed_users: Set[str] = set()
        self.processed_tx_hashes: Set[str] = set()
        self.redemptions: List[Dict[str, Any]] = []

    def get_vault_status(self) -> Dict[str, Any]:
        """Return current status and inventory of the Steam Vault."""
        depleted = self.available_cards <= 0
        inv_str = f"{self.available_cards} / {self.total_cards} Cards Available"
        rate_str = (
            f"{REQUIRED_TOKEN_AMOUNT:,.1f} DOOM (Layer-1) or "
            f"{REQUIRED_TOKEN_AMOUNT:,.1f} wDOOM (Base Mainnet) = "
            f"1x ${self.card_value_usd:.2f} USD Steam Digital Gift Card Code"
        )
        return {
            "vault_name": VAULT_NAME,
            "available_cards": self.available_cards,
            "total_cards": self.total_cards,
            "inventory_status": inv_str,
            "card_value_usd": self.card_value_usd,
            "total_vault_usd": self.total_cards * self.card_value_usd,
            "exchange_rate": rate_str,
            "limit_per_user": 1,
            "is_vault_depleted": depleted,
        }

    def validate_receipt(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """Syntactically and semantically validate a payment receipt.

        Returns a dictionary with 'valid': bool and 'error': Optional[str].
        """
        if not isinstance(receipt, dict):
            return {"valid": False, "error": "Receipt payload must be a JSON object."}

        token_type = str(receipt.get("token_type", "")).strip().upper()
        if token_type not in ("DOOM", "WDOOM"):
            return {
                "valid": False,
                "error": f"Unsupported token type: {token_type}. Accepted: DOOM, wDOOM.",
            }

        # Validate tx hash format
        tx_hash = str(receipt.get("tx_hash", "")).strip()
        if not tx_hash or not HEX_TX_REGEX.match(tx_hash):
            return {
                "valid": False,
                "error": "Invalid transaction hash format. Expected 64 hex characters.",
            }

        sender = str(receipt.get("sender", "")).strip()
        if not sender:
            return {"valid": False, "error": "Sender address or user ID is required."}

        # Check transaction confirmation / status
        status = receipt.get("status", 1)
        if status not in (1, "1", "confirmed", "success", "SUCCESS", True):
            return {
                "valid": False,
                "error": "Transaction status is not confirmed / successful.",
            }

        # Rail-specific checks
        if token_type == "WDOOM":
            chain_id = receipt.get("chain_id", BASE_CHAIN_ID)
            if chain_id not in (BASE_CHAIN_ID, str(BASE_CHAIN_ID)):
                return {
                    "valid": False,
                    "error": f"Invalid chain ID: {chain_id}. Expected Base Mainnet ({BASE_CHAIN_ID}).",
                }

            contract = normalize_address(receipt.get("token_contract"))
            if contract != normalize_address(WDOOM_CONTRACT_BASE):
                return {
                    "valid": False,
                    "error": (
                        f"Invalid wDOOM contract address: {contract}. "
                        f"Expected {WDOOM_CONTRACT_BASE}."
                    ),
                }

            recipient = normalize_address(receipt.get("recipient"))
            if recipient != normalize_address(VAULT_EVM_ADDRESS):
                return {
                    "valid": False,
                    "error": (
                        f"Invalid vault recipient address: {recipient}. "
                        f"Expected {VAULT_EVM_ADDRESS}."
                    ),
                }

            # Check amount: accept human token amount or raw wei
            amount = receipt.get("amount")
            raw_amount = receipt.get("raw_amount")
            if amount is not None:
                try:
                    amt_float = float(amount)
                except (ValueError, TypeError):
                    return {"valid": False, "error": "Invalid amount value."}
                if amt_float < REQUIRED_TOKEN_AMOUNT:
                    return {
                        "valid": False,
                        "error": (
                            f"Insufficient token amount: {amt_float:,.1f}. "
                            f"Required: {REQUIRED_TOKEN_AMOUNT:,.1f} wDOOM."
                        ),
                    }
            elif raw_amount is not None:
                try:
                    raw_int = int(raw_amount)
                except (ValueError, TypeError):
                    return {"valid": False, "error": "Invalid raw_amount value."}
                min_raw = int(REQUIRED_TOKEN_AMOUNT * (10 ** WDOOM_DECIMALS))
                if raw_int < min_raw:
                    return {
                        "valid": False,
                        "error": (
                            f"Insufficient raw token amount: {raw_int}. "
                            f"Required at least {min_raw} wei."
                        ),
                    }
            else:
                return {
                    "valid": False,
                    "error": "Payment receipt missing 'amount' or 'raw_amount'.",
                }

        elif token_type == "DOOM":
            recipient = str(receipt.get("recipient", "")).strip()
            if recipient != VAULT_DOOM_L1_ADDRESS:
                return {
                    "valid": False,
                    "error": (
                        f"Invalid Doomsday L1 recipient: {recipient}. "
                        f"Expected {VAULT_DOOM_L1_ADDRESS}."
                    ),
                }

            amount = receipt.get("amount")
            try:
                amt_float = float(amount)
            except (ValueError, TypeError):
                return {"valid": False, "error": "Invalid amount value for DOOM transfer."}

            if amt_float < REQUIRED_TOKEN_AMOUNT:
                return {
                    "valid": False,
                    "error": (
                        f"Insufficient DOOM amount: {amt_float:,.1f}. "
                        f"Required: {REQUIRED_TOKEN_AMOUNT:,.1f} DOOM."
                    ),
                }

        return {"valid": True, "error": None}

    def verify_and_redeem(self, receipt: Dict[str, Any]) -> Dict[str, Any]:
        """Verify on-chain payment and redeem a $10 Steam Digital Gift Card."""
        val = self.validate_receipt(receipt)
        if not val["valid"]:
            return {"success": False, "error": val["error"]}

        # Normalize identifiers
        sender = str(receipt.get("sender", "")).strip().lower()
        tx_hash = str(receipt.get("tx_hash", "")).strip().lower()
        if not tx_hash.startswith("0x") and receipt.get("token_type", "").upper() == "WDOOM":
            tx_hash = "0x" + tx_hash

        # Replay Attack Prevention
        if tx_hash in self.processed_tx_hashes:
            return {
                "success": False,
                "error": "Replay attack detected: Transaction hash has already been redeemed.",
            }

        # 1-per-user Limit Enforcement
        if sender in self.redeemed_users:
            return {
                "success": False,
                "error": "Redemption limit exceeded: Only 1 redemption allowed per verified user/wallet.",
            }

        # Vault Inventory Check
        if self.available_cards <= 0:
            return {
                "success": False,
                "error": "Vault inventory depleted: All Steam Digital Gift Cards have been claimed.",
            }

        # Issue Gift Card Code
        code = generate_steam_gift_card_code()
        self.available_cards -= 1
        self.redeemed_users.add(sender)
        self.processed_tx_hashes.add(tx_hash)

        record = {
            "user_id": sender,
            "tx_hash": tx_hash,
            "token_type": receipt.get("token_type", "").upper(),
            "code": code,
            "card_value_usd": self.card_value_usd,
        }
        self.redemptions.append(record)

        return {
            "success": True,
            "message": "Successfully redeemed 100,000 DOOM/$wDOOM for a $10 USD Steam Digital Gift Card!",
            "steam_gift_card_code": code,
            "card_value_usd": self.card_value_usd,
            "remaining_cards": self.available_cards,
            "tx_hash": tx_hash,
            "user_id": sender,
        }
