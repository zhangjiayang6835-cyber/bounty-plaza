import unittest
from tools.log_aggregator import parse_log


class TestLogParsers(unittest.TestCase):
    def test_json_parser(self):
        log_line = '{"timestamp": "2023-10-01T12:00:00", "level": "INFO", "service": "app", "message": "User logged in"}'
        parsed_log = parse_log(log_line, 'json')
        self.assertIsNotNone(parsed_log)
        self.assertEqual(parsed_log['timestamp'], '2023-10-01T12:00:00')
        self.assertEqual(parsed_log['level'], 'INFO')
        self.assertEqual(parsed_log['service'], 'app')
        self.assertEqual(parsed_log['message'], 'User logged in')

        # Malformed JSON
        malformed_log_line = '{"timestamp": "2023-10-01T12:00:00", "level": "INFO", "service": "app", "message": "User logged in'
        parsed_log = parse_log(malformed_log_line, 'json')
        self.assertIsNone(parsed_log)

    def test_text_parser(self):
        log_line = '2023-10-01T12:00:00 - INFO - User logged in'
        parsed_log = parse_log(log_line, 'text')
        self.assertIsNotNone(parsed_log)
        self.assertEqual(parsed_log['timestamp'], '2023-10-01T12:00:00')
        self.assertEqual(parsed_log['level'], 'INFO')
        self.assertEqual(parsed_log['service'], '')
        self.assertEqual(parsed_log['message'], 'User logged in')

        # Malformed text log
        malformed_log_line = '2023-10-01T12:00:00 - User logged in'
        parsed_log = parse_log(malformed_log_line, 'text')
        self.assertIsNone(parsed_log)

    def test_nginx_parser(self):
        log_line = '192.168.1.1 - - [01/Oct/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200 1024'
        parsed_log = parse_log(log_line, 'nginx')
        self.assertIsNotNone(parsed_log)
        self.assertEqual(parsed_log['timestamp'], '01/Oct/2023:12:00:00 +0000')
        self.assertEqual(parsed_log['level'], '')
        self.assertEqual(parsed_log['service'], 'nginx')
        self.assertEqual(parsed_log['message'], 'GET /index.html - Status: 200, Size: 1024')

        # Malformed nginx log
        malformed_log_line = '192.168.1.1 - - [01/Oct/2023:12:00:00 +0000] "GET /index.html HTTP/1.1" 200'
        parsed_log = parse_log(malformed_log_line, 'nginx')
        self.assertIsNone(parsed_log)


if __name__ == '__main__':
    unittest.main()