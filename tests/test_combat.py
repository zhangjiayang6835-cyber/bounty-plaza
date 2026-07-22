import unittest
from game.combat import CombatSystem
from game.items.security_weapons import SecurityRifle, SecurityShotgun

class TestCombatSystem(unittest.TestCase):
    def setUp(self):
        self.combat_system = CombatSystem()
        self.rifle = SecurityRifle()
        self.shotgun = SecurityShotgun()

    def test_add_weapon(self):
        self.combat_system.add_weapon(self.rifle)
        self.assertIn(self.rifle, self.combat_system.weapons)

    def test_calculate_damage(self):
        attacker = type('Attacker', (), {})()
        defender = type('Defender', (), {'take_damage': lambda self, damage: None})()
        damage = self.combat_system.calculate_damage(attacker, defender, self.rifle)
        self.assertEqual(damage, 25)

    def test_perform_attack(self):
        attacker = type('Attacker', (), {})()
        defender = type('Defender', (), {'take_damage': lambda self, damage: setattr(self, 'damage_taken', damage)})()
        self.combat_system.perform_attack(attacker, defender, self.shotgun)
        self.assertEqual(defender.damage_taken, 40)

if __name__ == '__main__':
    unittest.main()