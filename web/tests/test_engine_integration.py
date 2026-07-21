# Add to existing imports
from web.engine.ratvar_engine import RatvarEngine

class TestEngineIntegration:
    # ... existing tests ...

    def test_ratvar_engine_integration(self):
        # Test Ratvar Engine with conveyor system
        conveyor = ConveyorSystem()
        engine = RatvarEngine("ratvar1")
        conveyor.feed_engine(engine, 5)
        assert 0.5 < engine.integrity <= 0.55

        # Test Ratvar Engine with power distribution
        power_dist = PowerDistribution()
        engine.activate()
        power_dist.connect_engine(engine)
        assert power_dist.calculate_total_power() == engine.power_output

        # Test deactivation
        engine.deactivate()
        assert power_dist.calculate_total_power() == 0