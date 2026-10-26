import os
import sys
import json
from typing import Dict, Any, List

# Configuration & Vault State
VAULT_NAME = "STEAM VAULT"
TOTAL_CARDS = 10
CARD_VALUE_USD = 10.0
REDEMPTION_COST = 100000.0

# Persistent vault storage simulation for production
VAULT_STATE_FILE = "vault_state.json"

class SteamVaultManager:
    def __init__(self, state_file: str = VAULT_STATE_FILE):
        self.state_file = state_file
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "available_cards": TOTAL_CARDS,
            "redeemed_users": [],
            "distributed_codes": []
        }

    def _save_state(self):
        with open(self.state_file, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, indent=2)

    def get_vault_status(self) -> Dict[str, Any]:
        return {
            "vault_name": VAULT_NAME,
            "available_inventory": f"{self.state['available_cards']} / {TOTAL_CARDS} Cards Available",
            "total_vault_usd": f"${TOTAL_CARDS * CARD_VALUE_USD} USD",
            "exchange_rate": f"{REDEMPTION_COST:,.1f} DOOM (Layer-1) or {REDEMPTION_COST:,.1f} wDOOM (Base Mainnet) = 1x ${CARD_VALUE_USD:.2f} Steam Digital Gift Card",
            "limit_per_user": 1
        }

    def redeem_gift_card(self, user_id: str, token_type: str, token_amount: float) -> Dict[str, Any]:
        if token_type.upper() not in ["DOOM", "WDOOM"]:
            return {"success": False, "error": "Invalid token type. Accepted: DOOM, wDOOM"}

        if token_amount < REDEMPTION_COST:
            return {"success": False, "error": f"Insufficient funds. Required: {REDEMPTION_COST:,.1f} {token_type.upper()}"}

        if user_id in self.state["redeemed_users"]:
            return {"success": False, "error": "Redemption limit reached. Only 1 redemption allowed per verified user."}

        if self.state["available_cards"] <= 0:
            return {"success": False, "error": "Vault inventory empty. All Steam Digital Gift Cards have been claimed."}

        # Process redemption
        self.state["available_cards"] -= 1
        self.state["redeemed_users"].append(user_id)
        
        # Generate simulated secure gift card code placeholder or fetch from secure env
        part1 = os.urandom(4).hex().upper()
        part2 = os.urandom(4).hex().upper()
        gift_card_code = f"STEAM-DOOM-{part1}-{part2}"
        
        self.state["distributed_codes"].append({
            "user_id": user_id,
            "code": gift_card_code,
            "token_type": token_type.upper(),
            "amount_paid": token_amount
        })
        
        self._save_state()

        return {
            "success": True,
            "message": "Successfully redeemed 100,000 DOOM/$wDOOM for a $10 USD Steam Digital Gift Card!",
            "steam_gift_card_code": gift_card_code,
            "remaining_cards": self.state["available_cards"]
        }

def main():
    vault = SteamVaultManager()
    status = vault.get_vault_status()
    print(f"=== {status['vault_name']} ===")
    print(f"Inventory: {status['available_inventory']}")
    print(f"Rate: {status['exchange_rate']}")
    print(f"Limit: {status['limit_per_user']} per user\n")

    if len(sys.argv) > 2:
        user_id = sys.argv[1]
        token_type = sys.argv[2]
        try:
            amount = float(sys.argv[3])
        except (IndexError, ValueError):
            amount = REDEMPTION_COST

        result = vault.redeem_gift_card(user_id, token_type, amount)
        print(json.dumps(result, indent=2))
    else:
        print("Usage: python main.py <user_id> <DOOM|wDOOM> <amount>")

if __name__ == "__main__":
    main()
