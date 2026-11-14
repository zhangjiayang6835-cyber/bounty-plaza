import unittest
from solution import execute_task

class TestTaskExecution(unittest.TestCase):
    def test_execution(self):
        self.assertTrue(execute_task())

if __name__ == "__main__":
    unittest.main()
