"""Log Aggregator and Multi-Format Parser Subsystem.
Resolves Issue #494: [weilixiong/TentOfTrials] [$25 BOUNTY] [Python] Add independent log parser fixtures.
Upstream Reference: weilixiong/TentOfTrials#5.

Supported Formats:
1. JSON Log Lines: Structured JSON records with dynamic keys.
2. Standard Plain Text Log Lines: ISO/standard timestamps with log level and service tag.
3. Nginx Combined / Extended Log Lines: HTTP access logs with client IP, request method, URI, status, and bytes.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import re
from typing import Any, Dict, Iterator, List, Optional, TextIO


@dataclass
class ParsedLogRecord:
    raw_line: str
    format_type: str
    timestamp: Optional[str] = None
    level: str = "INFO"
    service: Optional[str] = None
    message: str = ""
    fields: Dict[str, Any] = field(default_factory=dict)
    is_malformed: bool = False
    error_reason: Optional[str] = None


class LogParser:
    """Robust multi-format log parser with non-crashing malformed line handling."""

    # Plain text log regex: e.g. 2026-06-19 12:34:56 [INFO] [auth-service] User login successful
    TEXT_LOG_PATTERN = re.compile(
        r"^(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:?\d{2})?)\s+"
        r"\[?([A-Z]+)\]?\s+"
        r"(?:\[([a-zA-Z0-9_\-\.]+)\]\s+)?"
        r"(.*)$"
    )

    # Nginx combined log regex: e.g. 192.168.1.10 - frank [19/Jun/2026:12:34:56 +0000] "GET /api/v1/health HTTP/1.1" 200 4522 "referer" "user-agent"
    NGINX_LOG_PATTERN = re.compile(
        r"^(\S+)\s+\S+\s+(\S+)\s+\[([^\]]+)\]\s+\"(\S+)\s+(\S+)\s*([^\"]*)\"\s+(\d{3})\s+(\d+|-)"
        r"(?:\s+\"([^\"]*)\"\s+\"([^\"]*)\")?"
    )

    @classmethod
    def parse_line(cls, line: str) -> ParsedLogRecord:
        """Parses a single log line into a normalized ParsedLogRecord."""
        stripped = line.strip()
        if not stripped:
            return ParsedLogRecord(raw_line=line, format_type="empty", is_malformed=True, error_reason="Empty line")

        # 1. Attempt JSON parsing
        if stripped.startswith("{"):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict):
                    ts = data.get("timestamp") or data.get("time") or data.get("@timestamp")
                    level = (data.get("level") or data.get("severity") or "INFO").upper()
                    service = data.get("service") or data.get("app") or data.get("component")
                    message = data.get("message") or data.get("msg") or ""

                    # Retain remaining custom fields
                    reserved = {"timestamp", "time", "@timestamp", "level", "severity", "service", "app", "component", "message", "msg"}
                    extra_fields = {k: v for k, v in data.items() if k not in reserved}

                    return ParsedLogRecord(
                        raw_line=line,
                        format_type="json",
                        timestamp=str(ts) if ts else None,
                        level=level,
                        service=str(service) if service else None,
                        message=str(message),
                        fields=extra_fields,
                    )
            except Exception as e:
                # Malformed JSON payload
                return ParsedLogRecord(
                    raw_line=line,
                    format_type="json",
                    is_malformed=True,
                    error_reason=f"Invalid JSON syntax: {str(e)}",
                )

        # 2. Attempt Nginx Access Log format
        nginx_match = cls.NGINX_LOG_PATTERN.match(stripped)
        if nginx_match:
            ip, user, ts_raw, method, uri, protocol, status_code, body_bytes, referer, user_agent = nginx_match.groups()
            level = "INFO" if int(status_code) < 400 else ("WARNING" if int(status_code) < 500 else "ERROR")
            return ParsedLogRecord(
                raw_line=line,
                format_type="nginx",
                timestamp=ts_raw,
                level=level,
                service="nginx",
                message=f"{method} {uri} -> {status_code}",
                fields={
                    "client_ip": ip,
                    "auth_user": user if user != "-" else None,
                    "http_method": method,
                    "request_uri": uri,
                    "http_protocol": protocol.strip() if protocol else None,
                    "status_code": int(status_code),
                    "bytes_sent": int(body_bytes) if body_bytes != "-" else 0,
                    "referer": referer if referer and referer != "-" else None,
                    "user_agent": user_agent if user_agent and user_agent != "-" else None,
                },
            )

        # 3. Attempt Plain Text log format
        text_match = cls.TEXT_LOG_PATTERN.match(stripped)
        if text_match:
            ts, level, service, msg = text_match.groups()
            return ParsedLogRecord(
                raw_line=line,
                format_type="text",
                timestamp=ts,
                level=level.upper(),
                service=service,
                message=msg.strip(),
            )

        # 4. Fallback: Malformed / Unrecognized format (never crash)
        return ParsedLogRecord(
            raw_line=line,
            format_type="unrecognized",
            is_malformed=True,
            error_reason="Line does not match recognized JSON, Nginx, or standard text log formats",
        )


class LogAggregator:
    """Aggregates and filters log lines across files or streams."""

    def __init__(self):
        self.records: List[ParsedLogRecord] = []
        self.error_count: int = 0

    def ingest_lines(self, lines: Iterator[str]) -> None:
        """Ingests and parses an iterator of lines."""
        for line in lines:
            rec = LogParser.parse_line(line)
            if rec.format_type != "empty":
                self.records.append(rec)
                if rec.is_malformed:
                    self.error_count += 1

    def filter_by_level(self, level: str) -> List[ParsedLogRecord]:
        lvl = level.upper()
        return [r for r in self.records if not r.is_malformed and r.level == lvl]

    def filter_by_service(self, service: str) -> List[ParsedLogRecord]:
        return [r for r in self.records if not r.is_malformed and r.service == service]

    def summary_stats(self) -> Dict[str, Any]:
        valid_records = [r for r in self.records if not r.is_malformed]
        format_counts: Dict[str, int] = {}
        level_counts: Dict[str, int] = {}
        for r in valid_records:
            format_counts[r.format_type] = format_counts.get(r.format_type, 0) + 1
            level_counts[r.level] = level_counts.get(r.level, 0) + 1

        return {
            "total_lines_parsed": len(self.records),
            "valid_records": len(valid_records),
            "malformed_lines": self.error_count,
            "formats": format_counts,
            "levels": level_counts,
        }
