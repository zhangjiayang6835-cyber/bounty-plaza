class RatvarEngine:
    def __init__(self, engine_id, initial_integrity=0.5):
        self.engine_id = engine_id
        self.integrity = initial_integrity
        self.power_output = 0
        self.is_active = False

    def feed_bronze(self, amount):
        """Feed bronze to maintain Ratvar's integrity"""
        self.integrity += amount * 0.01
        self.integrity = min(1.0, max(0.1, self.integrity))  # Keep within bounds

    def update_power_output(self):
        """Calculate power output based on current integrity"""
        if 0.3 <= self.integrity <= 0.7:
            self.power_output = 100 * self.integrity
        else:
            self.power_output = 0

    def activate(self):
        """Activate the Ratvar Engine"""
        if 0.3 <= self.integrity <= 0.7:
            self.is_active = True
            self.update_power_output()
        else:
            raise ValueError("Integrity level not suitable for activation")

    def deactivate(self):
        """Deactivate the Ratvar Engine"""
        self.is_active = False
        self.power_output = 0

    def get_status(self):
        """Return current status of the Ratvar Engine"""
        return {
            'engine_id': self.engine_id,
            'integrity': self.integrity,
            'power_output': self.power_output,
            'is_active': self.is_active
        }