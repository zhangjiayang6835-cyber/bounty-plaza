class MechMovement:
    def __init__(self, mech):
        self.mech = mech
        self.base_speed = 10
        self.current_speed = self.base_speed

    def update_speed(self):
        # Adjust speed based on thermal state
        if self.mech.thermal_system.is_overclocked:
            self.current_speed = self.base_speed * 1.2
        else:
            temp_factor = 1 - (self.mech.get_current_temp() / self.mech.thermal_system.emergency_threshold) * 0.3
            self.current_speed = self.base_speed * max(0.5, temp_factor)