import unittest
from web.mech_units import MechUnit
from web.equipment import MechEquipment
from web.movement import MechMovement
from web.atmosphere import Atmosphere

class TestMechIntegration(unittest.TestCase):
    def setUp(self):
        self.mech = MechUnit(tier=3, complexity=8)
        self.equipment = MechEquipment(self.mech)
        self.movement = MechMovement(self.mech)
        self.atmosphere = Atmosphere()

    def test_mech_equipment_interaction(self):
        module = MechUnit(tier=1, complexity=3)
        self.assertTrue(self.equipment.add_module(module))
        self.assertEqual(len(self.equipment.modules), 1)

    def test_thermal_impact_on_movement(self):
        self.mech.activate()
        self.mech.heat_generated = 120
        initial_speed = self.movement.current_speed
        self.movement.update_speed()
        self.assertLess(self.movement.current_speed, initial_speed)

    def test_atmosphere_heat_dissipation(self):
        self.mech.activate()
        initial_temp = self.mech.get_current_temp()
        self.atmosphere.update_temperature(10)
        self.mech.update_heat(self.atmosphere.get_temperature())
        self.assertLess(self.mech.get_current_temp(), initial_temp)

if __name__ == '__main__':
    unittest.main()