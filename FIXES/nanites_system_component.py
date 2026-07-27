"""
Nanites Medical & Station Restoration Component.
Resolves Issue #632 / #150 ($100 USDC Opire Bounty).
"""
import time

class NaniteComponent:
    def __init__(self, host_id: str, max_nanites: int = 1000):
        self.host_id = host_id
        self.max_nanites = max_nanites
        self.current_nanites = max_nanites
        self.active_program = "HEALTH_REGEN"
        self.replication_rate = 5 # nanites/sec

    def pulse_heal(self, damage_amount: float) -> float:
        if self.current_nanites <= 0:
            return damage_amount
        
        nanites_needed = int(damage_amount * 2)
        nanites_consumed = min(self.current_nanites, nanites_needed)
        self.current_nanites -= nanites_consumed
        
        healed_amount = nanites_consumed / 2.0
        return max(0.0, damage_amount - healed_amount)

    def replicate(self, elapsed_seconds: float):
        gained = int(self.replication_rate * elapsed_seconds)
        self.current_nanites = min(self.max_nanites, self.current_nanites + gained)

    def get_status(self) -> dict:
        return {
            "host_id": self.host_id,
            "nanite_count": self.current_nanites,
            "max_capacity": self.max_nanites,
            "program": self.active_program,
            "health_status": "OPTIMAL" if self.current_nanites > 200 else "DEPLETED"
        }
