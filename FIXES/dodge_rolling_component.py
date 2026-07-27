"""
Dodge Rolling Mechanics Component with Invulnerability Frames.
Resolves Issue #710 ($50.00 USD Bounty).
"""
import time

class DodgeRollComponent:
    def __init__(self, entity_id: str, roll_duration_sec: float = 0.8, cooldown_sec: float = 2.0):
        self.entity_id = entity_id
        self.roll_duration_sec = roll_duration_sec
        self.cooldown_sec = cooldown_sec
        self.last_roll_timestamp = 0.0
        self.is_rolling = False

    def trigger_dodge_roll(self) -> bool:
        now = time.time()
        if now - self.last_roll_timestamp < self.cooldown_sec:
            return False # Cooldown active
        
        self.is_rolling = True
        self.last_roll_timestamp = now
        return True

    def check_invulnerability(self) -> bool:
        now = time.time()
        if self.is_rolling:
            if now - self.last_roll_timestamp <= self.roll_duration_sec:
                return True # Invulnerable during roll window
            else:
                self.is_rolling = False
        return False

    def process_incoming_damage(self, raw_damage: float) -> float:
        if self.check_invulnerability():
            print(f"[DodgeRoll] Entity {self.entity_id} DODGED damage ({raw_damage} HP mitigated)!")
            return 0.0 # Zero damage taken while rolling
        return raw_damage
