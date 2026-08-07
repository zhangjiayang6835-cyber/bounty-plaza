#!/usr/bin/env python3
"""
⚡ Dodge Rolling Mechanics Engine (#710)
Implements invincibility frame (i-frame) dodge rolling, stamina cost management, and cooldown state tracking.
"""

import time

class DodgeRollManager:
    def __init__(self, stamina_cost=20, iframe_duration=0.5, cooldown=1.0):
        self.stamina_cost = stamina_cost
        self.iframe_duration = iframe_duration
        self.cooldown = cooldown
        self.last_roll_time = 0
        self.is_invincible = False

    def can_roll(self, current_stamina):
        if current_stamina < self.stamina_cost:
            return False, "Insufficient stamina"
        now = time.time()
        if now - self.last_roll_time < self.cooldown:
            remaining = round(self.cooldown - (now - self.last_roll_time), 2)
            return False, f"Dodge roll on cooldown ({remaining}s remaining)"
        return True, "Ready"

    def execute_roll(self, current_stamina):
        can, reason = self.can_roll(current_stamina)
        if not can:
            return {
                "success": False,
                "reason": reason,
                "stamina_remaining": current_stamina,
                "is_invincible": False
            }

        self.last_roll_time = time.time()
        self.is_invincible = True

        return {
            "success": True,
            "stamina_remaining": current_stamina - self.stamina_cost,
            "iframe_duration": self.iframe_duration,
            "is_invincible": True
        }

    def check_invincibility(self):
        now = time.time()
        if self.is_invincible and (now - self.last_roll_time > self.iframe_duration):
            self.is_invincible = False
        return self.is_invincible
