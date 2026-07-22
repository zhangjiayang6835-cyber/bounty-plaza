class Atmosphere:
    def __init__(self):
        self.temperature = 20  # Default room temperature

    def update_temperature(self, new_temp):
        self.temperature = new_temp

    def get_temperature(self):
        return self.temperature