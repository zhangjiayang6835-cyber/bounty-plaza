import unittest
from web.mech_units import MechUnit, MechThermalSystem

class TestMechUnits(unittest.TestCase):
    def setUp(self):
        self.mech = MechUnit(tier=2, complexity=5)
        self.thermal_system = MechThermalSystem(self.mech)

    def test_heat_generation(self):
        self.mech.activate()
        self.assertGreater(self.mech.heat_generated, 0)

    def test_heat_dissipation(self):
        self.mech.activate()
        initial_temp = self.mech.get_current_temp()
        self.mech.update_heat(environment_temp=10)
        self.assertLess(self.mech.get_current_temp(), initial_temp)

    def test_safety_system(self):
        self.mech.activate()
        self.mech.heat_generated = 120
        self.assertFalse(self.thermal_system.check_safety())

    def test_overclock(self):
        self.thermal_system.overclock()
        self.assertTrue(self.thermal_system.is_overclocked)

if __name__ == '__main__':
    unittest.main()