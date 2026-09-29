import unittest
import numpy as np
import math
from parameterized import parameterized

from ttnn import div_no_nan
from ttnn.testing import TestCase


class TestDivNoNanAccuracy(TestCase):
    """Test div_no_nan accuracy with 1 ULP guarantee."""

    @parameterized.expand([
        (np.float32,),
        (np.float64,),
    ])
    def test_div_no_nan_ulp_accuracy(self, dtype):
        """Test that div_no_nan produces results within 1 ULP of expected."""
        np.random.seed(42)
        
        # Generate test cases including edge cases
        x = np.random.uniform(-1e6, 1e6, 10000).astype(dtype)
        y = np.random.uniform(-1e6, 1e6, 10000).astype(dtype)
        
        # Add special cases
        special_cases = [
            (np.array([1.0, -1.0, 0.0, np.inf, -np.inf, np.nan], dtype=dtype),
             np.array([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=dtype)),
            (np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=dtype),
             np.array([0.0, 1e-30, 1e-40, 1e-50, 1e-60], dtype=dtype)),
            (np.array([1.0, 1.0, 1.0, 1.0, 1.0], dtype=dtype),
             np.array([1e30, 1e40, 1e50, 1e60, 1e70], dtype=dtype)),
        ]
        
        for x_test, y_test in special_cases:
            x = np.concatenate((x, x_test))
            y = np.concatenate((y, y_test))
        
        # Compute expected results
        with np.errstate(invalid='ignore', divide='ignore'):
            expected = np.divide(x, y, where=y!=0)
            expected[y == 0] = 0
        
        # Compute actual results
        actual = div_no_nan(x, y)
        
        # Check 1 ULP accuracy
        max_ulp_error = 0
        for a, e in zip(actual, expected):
            if not (np.isnan(a) and np.isnan(e)) and not (np.isinf(a) and np.isinf(e)):
                ulp_error = self._compute_ulp_error(a, e)
                if ulp_error > max_ulp_error:
                    max_ulp_error = ulp_error
        
        self.assertLessEqual(max_ulp_error, 1, 
                             f"Maximum ULP error {max_ulp_error} > 1 for {dtype}")

    def _compute_ulp_error(self, a, b):
        """Compute ULP error between two floating point numbers."""
        if np.isnan(a) or np.isnan(b):
            return 0
        if np.isinf(a) or np.isinf(b):
            return 0
        
        # Handle signed zeros
        if a == 0 and b == 0:
            return 0
        
        # Compute ULP difference
        if a == b:
            return 0
        
        # Use nextafter to find ULP difference
        if a > b:
            next_val = np.nextafter(a, np.inf)
            while next_val > b:
                next_val = np.nextafter(next_val, np.inf)
            return int(a - next_val)
        else:
            next_val = np.nextafter(a, -np.inf)
            while next_val < b:
                next_val = np.nextafter(next_val, -np.inf)
            return int(next_val - a)


class TestDivNoNanSemantics(TestCase):
    """Test div_no_nan preserves existing semantics."""

    @parameterized.expand([
        (np.float32,),
        (np.float64,),
    ])
    def test_div_no_nan_semantics(self, dtype):
        """Test div_no_nan preserves special value handling."""
        # Test division by zero
        self.assertEqual(div_no_nan(1.0, 0.0).item(), 0.0)
        self.assertEqual(div_no_nan(-1.0, 0.0).item(), 0.0)
        
        # Test infinities
        self.assertTrue(np.isinf(div_no_nan(np.inf, 1.0).item()))
        self.assertTrue(np.isinf(div_no_nan(-np.inf, 1.0).item()))
        self.assertEqual(div_no_nan(np.inf, np.inf).item(), 1.0)
        self.assertEqual(div_no_nan(-np.inf, -np.inf).item(), 1.0)
        
        # Test NaNs
        self.assertTrue(np.isnan(div_no_nan(np.nan, 1.0).item()))
        self.assertTrue(np.isnan(div_no_nan(1.0, np.nan).item()))
        
        # Test signed zeros
        self.assertEqual(div_no_nan(1.0, 0.0).item(), 0.0)
        self.assertEqual(div_no_nan(-1.0, 0.0).item(), 0.0)
        self.assertEqual(div_no_nan(0.0, 1.0).item(), 0.0)
        self.assertEqual(div_no_nan(-0.0, 1.0).item(), -0.0)


if __name__ == '__main__':
    unittest.main()