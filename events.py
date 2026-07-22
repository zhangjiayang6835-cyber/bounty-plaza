# ... existing code ...

class EldritchHorrorEvent(Event):
    def __init__(self):
        super().__init__(
            name="Eldritch Horror",
            description="An eldritch horror event triggered by Adskiderium exposure",
            probability=0.1
        )

    def trigger(self, entity):
        entity.apply_eldritch_horror_effects()

# ... existing code ...