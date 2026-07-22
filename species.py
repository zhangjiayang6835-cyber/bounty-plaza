# ... existing code ...

class Shitman(Species):
    def __init__(self):
        super().__init__(
            name="Shitman",
            description="A species transformed by Shitium exposure",
            traits={
                "strength": 80,
                "agility": 70,
                "intelligence": 60,
                "charisma": 50,
                "endurance": 90
            }
        )

    def apply_transformation(self, entity):
        entity.species = self
        entity.send_message("You're now a shitman!")

# ... existing code ...