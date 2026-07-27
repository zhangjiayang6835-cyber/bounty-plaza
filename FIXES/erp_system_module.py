"""
Enterprise Resource Planning (ERP) System Module for Bounty Plaza / TG-Station.
Resolves Issue #585 ($40 USDC Opire Bounty).
"""
import uuid
import datetime

class ERPResourceItem:
    def __init__(self, name: str, category: str, quantity: int, unit_cost: float):
        self.item_id = str(uuid.uuid4())[:8]
        self.name = name
        self.category = category
        self.quantity = max(0, quantity)
        self.unit_cost = max(0.0, unit_cost)
        self.updated_at = datetime.datetime.utcnow().isoformat()

    def total_value(self) -> float:
        return self.quantity * self.unit_cost

    def to_dict(self) -> dict:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "quantity": self.quantity,
            "unit_cost": self.unit_cost,
            "total_value": self.total_value(),
            "updated_at": self.updated_at
        }

class ERPSystemManager:
    def __init__(self, org_name: str = "Terran Station Enterprise"):
        self.org_name = org_name
        self.inventory = {}
        self.transactions = []

    def add_resource(self, name: str, category: str, quantity: int, unit_cost: float) -> dict:
        item = ERPResourceItem(name, category, quantity, unit_cost)
        self.inventory[item.item_id] = item
        self.log_transaction("ADD_RESOURCE", item.item_id, quantity, item.total_value())
        return item.to_dict()

    def update_stock(self, item_id: str, delta_quantity: int) -> dict:
        if item_id not in self.inventory:
            raise KeyError(f"Resource item {item_id} not found.")
        item = self.inventory[item_id]
        item.quantity = max(0, item.quantity + delta_quantity)
        item.updated_at = datetime.datetime.utcnow().isoformat()
        self.log_transaction("UPDATE_STOCK", item_id, delta_quantity, item.total_value())
        return item.to_dict()

    def log_transaction(self, tx_type: str, item_id: str, quantity: int, value: float):
        self.transactions.append({
            "tx_id": str(uuid.uuid4())[:8],
            "tx_type": tx_type,
            "item_id": item_id,
            "quantity": quantity,
            "value": value,
            "timestamp": datetime.datetime.utcnow().isoformat()
        })

    def generate_valuation_report(self) -> dict:
        total_items = len(self.inventory)
        total_inventory_value = sum(item.total_value() for item in self.inventory.values())
        return {
            "organization": self.org_name,
            "total_items_count": total_items,
            "total_inventory_value_usd": round(total_inventory_value, 2),
            "generated_at": datetime.datetime.utcnow().isoformat()
        }

if __name__ == "__main__":
    erp = ERPSystemManager()
    item1 = erp.add_resource("Nanite Repair Gel", "Medical Supply", 150, 45.50)
    item2 = erp.add_resource("Plasma Containment Cell", "Station Power", 50, 120.00)
    print("ERP System Report:", erp.generate_valuation_report())
