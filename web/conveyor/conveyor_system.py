class ConveyorSystem:
    # ... existing code ...

    def feed_engine(self, engine, amount):
        """Feed material to an engine"""
        if hasattr(engine, 'feed_bronze'):
            engine.feed_bronze(amount)
        else:
            raise ValueError("Engine does not support bronze feeding")