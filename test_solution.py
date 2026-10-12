import unittest
from unittest.mock import patch
from io import StringIO

# main.py
def main():
    print("Welcome to the VeloDAG Core Rust Dev Bounty Platform")
    print("Please visit the GitHub issue for more details and to claim the bounty")
    print("https://github.com/quantumchain-core/velodag-core/issues/2")

if __name__ == "__main__":
    main()

# tests_main.py
import unittest
from unittest.mock import patch
from main import main

class TestMain(unittest.TestCase):
    @patch('sys.stdout', new_callable=StringIO)
    def test_main_output(self, mock_stdout):
        main()
        expected_output = (
            "Welcome to the VeloDAG Core Rust Dev Bounty Platform\n"
            "Please visit the GitHub issue for more details and to claim the bounty\n"
            "https://github.com/quantumchain-core/velodag-core/issues/2\n"
        )
        self.assertEqual(mock_stdout.getvalue(), expected_output)

if __name__ == "__main__":
    unittest.main()