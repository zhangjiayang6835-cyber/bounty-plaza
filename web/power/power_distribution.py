class PowerDistribution:
    # ... existing code ...

    def connect_engine(self, engine):
        """Connect an engine to the power network"""
        if not hasattr(engine, 'power_output'):
            raise ValueError("Engine does not provide power output")

        self.connected_engines.append(engine)

    def calculate_total_power(self):
        """Calculate total power output from all connected engines"""
        total_power = 0
        for engine in self.connected_engines:
            if engine.is_active:
                total_power += engine.power_output
        return total_power