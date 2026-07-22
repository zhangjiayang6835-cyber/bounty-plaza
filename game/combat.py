class CombatSystem:
    def __init__(self):
        self.weapons = []

    def add_weapon(self, weapon):
        self.weapons.append(weapon)

    def calculate_damage(self, attacker, defender, weapon):
        base_damage = weapon.get_damage()
        # Additional damage calculation logic can be added here
        return base_damage

    def perform_attack(self, attacker, defender, weapon):
        damage = self.calculate_damage(attacker, defender, weapon)
        defender.take_damage(damage)
        if weapon.special_effect:
            weapon.apply_special_effect(defender)