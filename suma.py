@@ -1,4 +1,4 @@
 def suma(a, b):
-    return a - b  # Incorrect: should be addition
+    return a + b  # Correct: should be addition
```

And the test cases in `test_suma.py`:

```python
# test_suma.py
import unittest
from suma import suma

class TestSuma(unittest.TestCase):
    def test_suma_positive_numbers(self):
        self.assertEqual(suma(5, 3), 8)

    def test_suma_negative_numbers(self):
        self.assertEqual(suma(-5, -3), -8)

    def test_suma_mixed_numbers(self):
        self.assertEqual(suma(-5, 3), -2)

    def test_suma_zero(self):
        self.assertEqual(suma(0, 0), 0)

if __name__ == '__main__':
    unittest.main()
```

By following these steps, you should be able to fix the issue and submit a high-quality PR.