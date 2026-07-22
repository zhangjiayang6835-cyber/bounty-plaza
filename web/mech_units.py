class MechUnit:
    def __init__(self, tier, complexity):
        self.tier = tier
        self.complexity = complexity
        self.heat_generated = 0
        self.heat_dissipated = 0
        self.is_active = False

    def activate(self):
        self.is_active = True
        self.heat_generated = self.calculate_heat_generation()

    def deactivate(self):
        self.is_active = False
        self.heat_generated = 0

    def calculate_heat_generation(self):
        # Base heat generation based on tier and complexity
        return self.tier * self.complexity * 0.5

    def update_heat(self, environment_temp):
        # Heat dissipation based on environment temperature
        if environment_temp < self.get_current_temp():
            self.heat_dissipated = (self.get_current_temp() - environment_temp) * 0.1
        else:
            self.heat_dissipated = 0

        # Update current temperature
        self.current_temp = self.get_current_temp() - self.heat_dissipated

    def get_current_temp(self):
        return self.heat_generated - self.heat_dissipated

class MechThermalSystem:
    def __init__(self, mech):
        self.mech = mech
        self.default_threshold = 100
        self.emergency_threshold = 150
        self.is_overclocked = False

    def check_safety(self):
        if self.mech.get_current_temp() > self.default_threshold and not self.is_overclocked:
            self.mech.deactivate_equipment()
            return False
        elif self.mech.get_current_temp() > self.emergency_threshold:
            self.apply_emergency_effects()
            return False
        return True

    def apply_emergency_effects(self):
        # Reduce movement speed
        self.mech.movement_speed *= 0.7

        # Reduce module efficiency
        for module in self.mech.modules:
            module.efficiency *= 0.8

        # Reduce armor stability
        self.mech.armor_stability *= 0.9

        # Heat cockpit if closed
        if not self.mech.cockpit_open:
            self.mech.cockpit_temp += 10

    def overclock(self):
        self.is_overclocked = True

    def reset_overclock(self):
        self.is_overclocked = False