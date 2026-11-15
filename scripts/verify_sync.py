import unittest
import json
from hunt_bounties import check_control_plane_mismatch

class TestChainFeedSync(unittest.TestCase):
    def setUp(self):
        self.config = {
            "networks": {
                "ethereum_mainnet": {
                    "control_plane_version": "2.0.1"
                }
            }
        }

    def test_mismatch_detection(self):
        # Test case where versions do not match
        bad_feed = {"ethereum_mainnet": {"version": "1.9.9"}}
        self.assertTrue(check_control_plane_mismatch(self.config, bad_feed))

    def test_sync_success(self):
        # Test case where versions match
        good_feed = {"ethereum_mainnet": {"version": "2.0.1"}}
        self.assertFalse(check_control_plane_mismatch(self.config, good_feed))

if __name__ == "__main__":
    unittest.main()
