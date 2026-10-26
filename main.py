import os
import sys
import json
from typing import Dict, Any, List

VAULT_NAME = "STEAM VAULT"
TOTAL_INVENTORY = 10
COST_PER_ITEM = 100000.0
REWARD_DESCRIPTION = "$10 USD Steam Digital Gift Card"

class SteamVault:
    def __init__(self, inventory_file: str = "vault_inventory.json"):
        self.inventory_file = inventory_file
        self.inventory = TOTAL_INVENTORY
        self.redeemed_users: List[str] = []
        self.load_state()

    def load_state(self) -> None:
        if os.path.exists(self.inventory_file):
            try:
                with open(self.inventory_file, "r") as f:
                    data = json.load(f)
                    self.inventory = data.get("inventory", TOTAL_INVENTORY)
                    self.redeemed_users = data.get("redeemed_users", [])
            except Exception as e:
                print(f"Warning: Failed to load vault state: {e}", file=sys.stderr)

    def save_state(self) -> None:
        data = {
            "inventory": self.inventory,
            "redeemed_users": self.redeemed_users
        }
        with open(self.inventory_file, "w") as f:
            json.dump(data, f, indent=4)

    def get_vault_status(self) -> Dict[str, Any]:
        return {
            "vault_name": VAULT_NAME,
            "inventory_available": self.inventory,
            "total_inventory": TOTAL_INVENTORY,
            "exchange_rate": f"{COST_PER_ITEM} DOOM / wDOOM",
            "reward": REWARD_DESCRIPTION,
            "limit_per_user": 1
        }

    def redeem(self, user_id: str, amount: float, token_type: str) -> Dict[str, Any]:
        if token_type.upper() not in ["DOOM", "WDOOM"]:
            return {"success": False, "error": "Invalid token type. Accepted: DOOM (Layer-1), wDOOM (Base Mainnet)."}

        if amount < COST_PER_ITEM:
            return {"success": False, "error": f"Insufficient funds. Required: {COST_PER_ITEM} {token_type.upper()}."}

        if user_id in self.redeemed_users:
            return {"success": False, "error": "Redemption limit reached. Only 1 redemption allowed per verified GP."}

        if self.inventory <= 0:
            return {"success": False, "error": "Vault is empty. All Steam Digital Gift Cards have been claimed."}

        # Process redemption
        self.inventory -= 1
        self.redeemed_users.append(user_id)
        self.save_state()

        gift_card_code = self._allocate_gift_card_code()

        return {
            "success": True,
            "message": f"Successfully exchanged {COST_PER_ITEM} {token_type.upper()} for a {REWARD_DESCRIPTION}!",
            "gift_card_code": gift_card_code,
            "remaining_inventory": self.inventory
        }

    def _allocate_gift_card_code(self) -> str:
        # Production stub returning a mock secure code reference or integration hook
        import secrets
        return f"STEAM-VAL-{secrets.token_hex(4).upper()}-{secrets.token_hex(4).upper()}"

def main():
    vault = SteamVault()
    print(json.dumps(vault.get_vault_status(), indent=2))

if __name__ == "__main__":
    main()
