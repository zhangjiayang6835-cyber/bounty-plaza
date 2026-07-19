import json
import re
from datetime import datetime


def parse_json_log(log_line):
    try:
        log_data = json.loads(log_line)
        return {
            'timestamp': log_data.get('timestamp', ''),
            'level': log_data.get('level', ''),
           'service': log_data.get('service', ''),
           'message': log_data.get('message', '')
        }
    except json.JSONDecodeError:
        return None


def parse_text_log(log_line):
    parts = log_line.split(' - ')
    if len(parts) < 3:
        return None
    timestamp, level, message = parts[0], parts[1],'- '.join(parts[2:])
    return {
        'timestamp': timestamp,
        'level': level,
       'service': '',
       'message': message
    }


def parse_nginx_log(log_line):
    regex = r'(?P<ip>\S+) \S+ \S+ \[(?P<timestamp>[^\]]+)\] "(?P<method>\S+) (?P<path>\S+) \S+" (?P<status>\d{3}) (?P<size>\d+)'
    match = re.match(regex, log_line)
    if not match:
        return None
    return {
        'timestamp': match.group('timestamp'),
        'level': '',
       'service': 'nginx',
        'message': f"{{match.group('method')}} {{match.group('path')}} - Status: {{match.group('status')}}, Size: {{match.group('size')}}"
    }


def parse_log(log_line, log_format):
    if log_format == 'json':
        return parse_json_log(log_line)
    elif log_format == 'text':
        return parse_text_log(log_line)
    elif log_format == 'nginx':
        return parse_nginx_log(log_line)
    else:
        return None
