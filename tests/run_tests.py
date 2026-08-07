import unittest
import time
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from scripts.dodge_roll import DodgeRollManager

class TestDodgeRoll(unittest.TestCase):
    def test_dodge_roll_success(self):
        manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
        res = manager.execute_roll(current_stamina=100)
        self.assertTrue(res["success"])
        self.assertEqual(res["stamina_remaining"], 80)
        self.assertTrue(res["is_invincible"])
        print("✓ test_dodge_roll_success passed")

    def test_dodge_roll_insufficient_stamina(self):
        manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
        res = manager.execute_roll(current_stamina=10)
        self.assertFalse(res["success"])
        self.assertEqual(res["reason"], "Insufficient stamina")
        print("✓ test_dodge_roll_insufficient_stamina passed")

    def test_dodge_roll_cooldown(self):
        manager = DodgeRollManager(stamina_cost=20, iframe_duration=0.5, cooldown=1.0)
        res1 = manager.execute_roll(current_stamina=100)
        self.assertTrue(res1["success"])

        res2 = manager.execute_roll(current_stamina=80)
        self.assertFalse(res2["success"])
        self.assertIn("cooldown", res2["reason"].lower())
        print("✓ test_dodge_roll_cooldown passed")

if __name__ == "__main__":
    unittest.main()
