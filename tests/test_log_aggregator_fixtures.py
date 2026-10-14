"""Unit tests for multi-format log parser using independent hand-written fixtures.
Validates Issue #494: [weilixiong/TentOfTrials] [$25 BOUNTY] [Python] Add independent log parser fixtures.
Upstream Reference: weilixiong/TentOfTrials#5.
"""

from pathlib import Path
import pytest
import sys

# Add bounty-plaza root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.log_aggregator import LogParser, LogAggregator, ParsedLogRecord


FIXTURES_DIR = Path(__file__).parent / "fixtures"


def test_independent_json_log_fixtures():
    json_path = FIXTURES_DIR / "sample_json_logs.log"
    with open(json_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    records = [LogParser.parse_line(line) for line in lines]
    assert len(records) == 3

    # Record 1: Payment gateway INFO
    r0 = records[0]
    assert r0.format_type == "json"
    assert r0.level == "INFO"
    assert r0.service == "payment-gateway"
    assert r0.timestamp == "2026-06-19T04:15:22.105Z"
    assert r0.message == "Captured authorized charge"
    assert r0.fields["tx_id"] == "tx_994812"
    assert r0.fields["amount_cents"] == 2500
    assert not r0.is_malformed

    # Record 2: Risk engine WARN
    r1 = records[1]
    assert r1.format_type == "json"
    assert r1.level == "WARN"
    assert r1.service == "risk-engine"
    assert r1.fields["merchant_id"] == "m_441"
    assert r1.fields["score"] == 0.84
    assert not r1.is_malformed

    # Record 3: Settlement worker ERROR
    r2 = records[2]
    assert r2.format_type == "json"
    assert r2.level == "ERROR"
    assert r2.service == "settlement-worker"
    assert r2.fields["error_code"] == "ETIMEDOUT"
    assert not r2.is_malformed


def test_independent_plain_text_log_fixtures():
    text_path = FIXTURES_DIR / "sample_plain_text_logs.log"
    with open(text_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    records = [LogParser.parse_line(line) for line in lines]
    assert len(records) == 4

    r0 = records[0]
    assert r0.format_type == "text"
    assert r0.timestamp == "2026-06-19 04:18:10"
    assert r0.level == "INFO"
    assert r0.service == "ingress-controller"
    assert "TLS handshake established" in r0.message
    assert not r0.is_malformed

    r1 = records[1]
    assert r1.format_type == "text"
    assert r1.level == "WARN"
    assert r1.service == "rate-limiter"
    assert not r1.is_malformed

    r2 = records[2]
    assert r2.format_type == "text"
    assert r2.level == "ERROR"
    assert r2.service == "database-pool"
    assert not r2.is_malformed

    r3 = records[3]
    assert r3.format_type == "text"
    assert r3.level == "DEBUG"
    assert r3.service == "metrics-exporter"
    assert not r3.is_malformed


def test_independent_nginx_log_fixtures():
    nginx_path = FIXTURES_DIR / "sample_nginx_logs.log"
    with open(nginx_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    records = [LogParser.parse_line(line) for line in lines]
    assert len(records) == 4

    # Record 0: 200 OK
    r0 = records[0]
    assert r0.format_type == "nginx"
    assert r0.fields["client_ip"] == "192.168.1.10"
    assert r0.fields["auth_user"] == "frank"
    assert r0.fields["http_method"] == "GET"
    assert r0.fields["request_uri"] == "/api/v1/health"
    assert r0.fields["status_code"] == 200
    assert r0.fields["bytes_sent"] == 4522
    assert r0.level == "INFO"
    assert not r0.is_malformed

    # Record 2: 403 Forbidden -> Warning
    r2 = records[2]
    assert r2.format_type == "nginx"
    assert r2.fields["status_code"] == 403
    assert r2.level == "WARNING"
    assert not r2.is_malformed

    # Record 3: 502 Bad Gateway -> Error
    r3 = records[3]
    assert r3.format_type == "nginx"
    assert r3.fields["status_code"] == 502
    assert r3.level == "ERROR"
    assert not r3.is_malformed


def test_malformed_and_unsupported_lines_fail_safe():
    # Malformed JSON line
    bad_json = '{"timestamp": "2026-06-19", "unclosed_json: true'
    r_bad_json = LogParser.parse_line(bad_json)
    assert r_bad_json.is_malformed is True
    assert "Invalid JSON" in r_bad_json.error_reason

    # Random binary or corrupt string
    corrupt_line = "@@##$$%% RANDOM NON-LOG NOISE STRING ^^&&**"
    r_corrupt = LogParser.parse_line(corrupt_line)
    assert r_corrupt.is_malformed is True
    assert r_corrupt.format_type == "unrecognized"

    # Aggregator resilience
    aggregator = LogAggregator()
    aggregator.ingest_lines([bad_json, corrupt_line, ""])
    assert aggregator.error_count == 2
    stats = aggregator.summary_stats()
    assert stats["malformed_lines"] == 2
    assert stats["valid_records"] == 0
