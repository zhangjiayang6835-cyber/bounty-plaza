"""Pytest test discovery suite for deliverable_4256 (#4256).

Tests that verify_sequence_gap enforces contiguous sequence validation
and raises KeyError("missing seq key in header") when 'seq' is missing.
"""

from __future__ import annotations

import unittest

from deliverable_4256 import verify_sequence_gap


class TestDeliverable4256(unittest.TestCase):
    """Test suite for deliverable_4256."""

    def test_missing_seq_key_in_first_header(self) -> None:
        """Verify KeyError is raised when the first header lacks 'seq'."""
        headers = [{"height": 1}, {"seq": 2}]
        with self.assertRaises(KeyError) as ctx:
            verify_sequence_gap(headers)
        self.assertEqual(ctx.exception.args[0], "missing seq key in header")

    def test_missing_seq_key_in_second_header(self) -> None:
        """Verify KeyError is raised when a subsequent header lacks 'seq'."""
        headers = [{"seq": 1}, {"height": 2}]
        with self.assertRaises(KeyError) as ctx:
            verify_sequence_gap(headers)
        self.assertEqual(ctx.exception.args[0], "missing seq key in header")

    def test_missing_seq_key_in_single_header(self) -> None:
        """Verify KeyError is raised when a single header lacks 'seq'."""
        headers = [{"height": 1}]
        with self.assertRaises(KeyError) as ctx:
            verify_sequence_gap(headers)
        self.assertEqual(ctx.exception.args[0], "missing seq key in header")

    def test_missing_seq_key_in_middle_header(self) -> None:
        """Verify KeyError is raised when a middle header lacks 'seq'."""
        headers = [{"seq": 10}, {"other": 11}, {"seq": 12}]
        with self.assertRaises(KeyError) as ctx:
            verify_sequence_gap(headers)
        self.assertEqual(ctx.exception.args[0], "missing seq key in header")

    def test_empty_headers_list(self) -> None:
        """Verify empty headers list returns True."""
        self.assertTrue(verify_sequence_gap([]))

    def test_single_valid_header(self) -> None:
        """Verify single valid header returns True."""
        self.assertTrue(verify_sequence_gap([{"seq": 0}]))
        self.assertTrue(verify_sequence_gap([{"seq": 42}]))

    def test_strictly_contiguous_sequence(self) -> None:
        """Verify strictly contiguous sequence returns True."""
        headers = [{"seq": 1}, {"seq": 2}, {"seq": 3}, {"seq": 4}]
        self.assertTrue(verify_sequence_gap(headers))

    def test_gap_in_sequence_returns_false(self) -> None:
        """Verify gap between sequence numbers returns False."""
        headers = [{"seq": 1}, {"seq": 3}]
        self.assertFalse(verify_sequence_gap(headers))

    def test_gap_in_later_elements_returns_false(self) -> None:
        """Verify gap occurring later in sequence returns False."""
        headers = [{"seq": 10}, {"seq": 11}, {"seq": 13}]
        self.assertFalse(verify_sequence_gap(headers))

    def test_decreasing_sequence_returns_false(self) -> None:
        """Verify decreasing sequence returns False."""
        headers = [{"seq": 2}, {"seq": 1}]
        self.assertFalse(verify_sequence_gap(headers))

    def test_duplicate_sequence_returns_false(self) -> None:
        """Verify duplicate sequence numbers return False."""
        headers = [{"seq": 5}, {"seq": 5}]
        self.assertFalse(verify_sequence_gap(headers))

    def test_headers_with_extra_fields(self) -> None:
        """Verify extra metadata in header dictionaries is accepted."""
        headers = [
            {"seq": 1, "height": 100, "hash": 12345},
            {"seq": 2, "height": 101, "hash": 67890},
        ]
        self.assertTrue(verify_sequence_gap(headers))

    def test_negative_contiguous_sequence(self) -> None:
        """Verify negative contiguous sequence numbers return True."""
        headers = [{"seq": -2}, {"seq": -1}, {"seq": 0}, {"seq": 1}]
        self.assertTrue(verify_sequence_gap(headers))

    def test_large_contiguous_sequence(self) -> None:
        """Verify large contiguous sequences return True."""
        headers = [{"seq": i} for i in range(1000)]
        self.assertTrue(verify_sequence_gap(headers))

    def test_large_sequence_with_single_gap(self) -> None:
        """Verify large sequence with single gap returns False."""
        headers = [{"seq": i} for i in range(500)] + [{"seq": i} for i in range(501, 1000)]
        self.assertFalse(verify_sequence_gap(headers))


if __name__ == "__main__":
    unittest.main()
