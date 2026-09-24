"""
Test cases for flower collector dimensions against tinaco constraints
"""

import unittest
from cad.tinaco_geometry import Tinaco
from cad.assembly_constraints import RetrofitConstraints

class TestCollectorDimensions(unittest.TestCase):
    def test_200l_tinaco_compatibility(self):
        tinaco = Tinaco("200L")
        self.assertTrue(tinaco.validate_collector(750, 400))
        self.assertFalse(tinaco.validate_collector(800, 400))  # Exceeds diameter

    def test_300l_tinaco_compatibility(self):
        tinaco = Tinaco("300L")
        self.assertTrue(tinaco.validate_collector(850, 450))
        self.assertFalse(tinaco.validate_collector(900, 450))

    def test_structural_integrity(self):
        constraints = RetrofitConstraints()
        self.assertTrue(constraints.validate_structural(5, 20e6))  # Valid case
        self.assertFalse(constraints.validate_structural(3, 20e6))  # Too thin

    def test_water_flow(self):
        constraints = RetrofitConstraints()
        self.assertTrue(constraints.validate_water_flow(8, 800))  # Valid
        self.assertFalse(constraints.validate_water_flow(4, 800))  # Too few petals

if __name__ == "__main__":
    unittest.main()