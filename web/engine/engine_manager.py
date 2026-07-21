# Add to existing imports
from web.engine.ratvar_engine import RatvarEngine

class EngineManager:
    # ... existing code ...

    def __init__(self):
        # ... existing initialization ...
        self.engine_registry = {
            'supermatter': SupermatterEngine,
            'ratvar': RatvarEngine  # Add Ratvar Engine to registry
        }

    # ... existing methods ...

    def create_engine(self, engine_type, engine_id, **kwargs):
        """Create a new engine instance"""
        if engine_type not in self.engine_registry:
            raise ValueError(f"Unknown engine type: {engine_type}")

        engine_class = self.engine_registry[engine_type]
        return engine_class(engine_id, **kwargs)