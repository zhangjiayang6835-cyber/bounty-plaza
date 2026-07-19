import unittest
from bring_up_cosyvoice import main

class TestCosyVoiceBringUp(unittest.TestCase):
    def test_inference(self):
        # Capture the output of the main function
        from io import StringIO
        import sys
        captured_output = StringIO()
        sys.stdout = captured_output
        main()
        sys.stdout = sys.__stdout__ 

        # Check if the output is as expected
        output = captured_output.getvalue().strip()
        self.assertIn("Output:", output)

if __name__ == "__main__":
    unittest.main()
