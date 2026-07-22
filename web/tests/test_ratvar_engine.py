import pytest
from web.engine.ratvar_engine import RatvarEngine

class TestRatvarEngine:
    def test_initialization(self):
        engine = RatvarEngine("ratvar1")
        assert engine.engine_id == "ratvar1"
        assert 0.1 <= engine.integrity <= 1.0
        assert engine.power_output == 0
        assert not engine.is_active

    def test_feed_bronze(self):
        engine = RatvarEngine("ratvar1", 0.5)
        engine.feed_bronze(10)
        assert 0.5 < engine.integrity <= 0.6

        # Test bounds
        engine.feed_bronze(-100)  # Should not go below 0.1
        assert engine.integrity == 0.1

        engine.feed_bronze(100)  # Should not go above 1.0
        assert engine.integrity == 1.0

    def test_power_output(self):
        engine = RatvarEngine("ratvar1", 0.5)
        engine.update_power_output()
        assert engine.power_output == 50

        engine.integrity = 0.2
        engine.update_power_output()
        assert engine.power_output == 0

    def test_activation(self):
        engine = RatvarEngine("ratvar1", 0.5)
        engine.activate()
        assert engine.is_active
        assert engine.power_output == 50

        engine.integrity = 0.2
        with pytest.raises(ValueError):
            engine.activate()

    def test_deactivation(self):
        engine = RatvarEngine("ratvar1", 0.5)
        engine.activate()
        engine.deactivate()
        assert not engine.is_active
        assert engine.power_output == 0