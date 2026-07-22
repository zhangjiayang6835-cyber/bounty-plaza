# ... existing code ...

class Shitium(Gas):
    def __init__(self):
        super().__init__(
            name="Shitium",
            color=(139, 69, 19),  # Brown color
            density=1.2,
            flammability=0.1,
            toxicity=0.5,
            specific_heat=1.0,
            thermal_conductivity=0.02,
            molar_heat_capacity=29.0,
            reaction_temperature=293.15
        )

    def interact_with_entity(self, entity):
        if isinstance(entity, Human):
            entity.transform_to_species("Shitman")
            entity.send_message("You're now a shitman!")
        elif isinstance(entity, Item):
            entity.transform_to_shitium_variant()
        elif isinstance(entity, Tile):
            entity.transform_to_shitium_variant()

class KurchatovQuantium(Gas):
    def __init__(self):
        super().__init__(
            name="Kurchatov-Quantium",
            color=(0, 255, 255),  # Cyan color
            density=0.8,
            flammability=0.0,
            toxicity=1.0,
            specific_heat=0.5,
            thermal_conductivity=0.01,
            molar_heat_capacity=25.0,
            reaction_temperature=293.15
        )

    def interact_with_entity(self, entity):
        if isinstance(entity, Human):
            entity.apply_quantum_mutation()
        elif isinstance(entity, Item):
            entity.apply_quantum_mutation()
        elif isinstance(entity, Tile):
            entity.apply_quantum_mutation()

class Adskiderium(Gas):
    def __init__(self):
        super().__init__(
            name="Adskiderium",
            color=(128, 0, 128),  # Purple color
            density=1.5,
            flammability=0.0,
            toxicity=1.0,
            specific_heat=0.8,
            thermal_conductivity=0.015,
            molar_heat_capacity=27.0,
            reaction_temperature=293.15
        )

    def interact_with_entity(self, entity):
        if isinstance(entity, Human):
            entity.apply_eldritch_horror()
        elif isinstance(entity, Item):
            entity.apply_eldritch_horror()
        elif isinstance(entity, Tile):
            entity.apply_eldritch_horror()

# ... existing code ...