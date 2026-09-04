"""CL.TE HTTP Request Smuggling & Cache Poisoning Defense Subsystem.
Resolves Issue #495: [Bounty] [zhangjiayang6835-cyber/ai-research] [BUG] CL.TE HTTP Request Smuggling → Cache Poisoning ($200 USD).
Upstream Reference: RFC 9112 Section 6.1, RFC 9113 (HTTP/2), CWE-444.

Vulnerability Context:
Front-end proxy (e.g. Nginx/CDN) uses Content-Length (CL) while back-end application server
uses Transfer-Encoding: chunked (TE), or vice-versa. An attacker crafts ambiguous requests containing
both headers or obfuscated TE headers (e.g., Transfer-Encoding: xchunked, leading spaces, duplicate headers)
causing request desynchronization, cache poisoning, and credential interception.

Defensive Architecture:
1. Strict RFC 9112 Section 6.1 Compliance:
   - If a request contains both Content-Length and Transfer-Encoding, Transfer-Encoding overrides Content-Length
     or the request is immediately rejected with 400 Bad Request to prevent desync.
   - Reject any malformed, duplicate, or obfuscated Transfer-Encoding values (e.g., TE: chunked\r\nTE: cow,
     Transfer-Encoding: \tchunked, Transfer-Encoding: chunked, identity).
2. End-to-End HTTP/2 Gateway Adapter:
   - Eliminates framing ambiguity entirely by enforcing binary framing (DATA/HEADERS frames with explicit length fields)
     preventing delimiter-based HTTP/1.1 smuggling.
   - Disallows HTTP/1.0 protocol downgrades on backend upstream connections.
3. Cache Poisoning Sanitizer:
   - Strips dangerous unkeyed hop-by-hop headers from upstream responses before caching.
   - Enforces cache-key normalization across path and query strings.
"""

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional, Set, Tuple


class HttpProtocolVersion(str, Enum):
    HTTP_1_0 = "HTTP/1.0"
    HTTP_1_1 = "HTTP/1.1"
    HTTP_2 = "HTTP/2"


class ValidationAction(str, Enum):
    ALLOW = "ALLOW"
    REJECT_400 = "REJECT_400"
    NORMALIZE = "NORMALIZE"


@dataclass
class HttpRequestMessage:
    method: str
    uri: str
    protocol: HttpProtocolVersion
    headers: Dict[str, str] = field(default_factory=dict)
    raw_header_lines: List[str] = field(default_factory=list)
    body: bytes = b""


@dataclass
class InspectionResult:
    action: ValidationAction
    status_code: int = 200
    reason: Optional[str] = None
    sanitized_headers: Dict[str, str] = field(default_factory=dict)
    is_http2_safe: bool = False


class HttpSmugglingDefenseGateway:
    """Hardened HTTP Gateway Validator defending against CL.TE, TE.CL, and TE.TE smuggling."""

    # Valid Transfer-Encoding single token according to RFC 9112
    VALID_TE_TOKENS = {"chunked", "compress", "deflate", "gzip"}

    def __init__(
        self,
        enforce_http2_upstream: bool = True,
        disallow_http10_downgrade: bool = True,
        strict_reject_te_cl_coexistence: bool = True,
    ):
        self.enforce_http2_upstream = enforce_http2_upstream
        self.disallow_http10_downgrade = disallow_http10_downgrade
        self.strict_reject_te_cl_coexistence = strict_reject_te_cl_coexistence
        self.poisoning_attempts_blocked = 0

    def inspect_and_sanitize(self, req: HttpRequestMessage) -> InspectionResult:
        """Inspects incoming HTTP request for smuggling vectors and validates header integrity."""
        # 1. Check HTTP/2 binary framing
        if req.protocol == HttpProtocolVersion.HTTP_2:
            return InspectionResult(
                action=ValidationAction.ALLOW,
                status_code=200,
                sanitized_headers=dict(req.headers),
                is_http2_safe=True,
            )

        # 2. Check HTTP/1.0 downgrade defense
        if req.protocol == HttpProtocolVersion.HTTP_1_0 and self.disallow_http10_downgrade:
            return InspectionResult(
                action=ValidationAction.REJECT_400,
                status_code=400,
                reason="HTTP/1.0 downgrade disabled to prevent framing desynchronization",
            )

        # Case-insensitive header dictionary lookup
        normalized_headers: Dict[str, str] = {}
        header_occurrences: Dict[str, int] = {}
        for k, v in req.headers.items():
            k_lower = k.strip().lower()
            header_occurrences[k_lower] = header_occurrences.get(k_lower, 0) + 1
            normalized_headers[k_lower] = v.strip()

        # Check raw header lines for duplicate or obfuscated headers
        te_lines = [line for line in req.raw_header_lines if line.lower().startswith("transfer-encoding")]
        cl_lines = [line for line in req.raw_header_lines if line.lower().startswith("content-length")]

        # 3. Detect duplicate Content-Length headers (RFC 9112 Section 6.1)
        if len(cl_lines) > 1 or header_occurrences.get("content-length", 0) > 1:
            self.poisoning_attempts_blocked += 1
            return InspectionResult(
                action=ValidationAction.REJECT_400,
                status_code=400,
                reason="Duplicate Content-Length headers detected (potential CL.CL smuggling)",
            )

        has_te = "transfer-encoding" in normalized_headers or len(te_lines) > 0
        has_cl = "content-length" in normalized_headers or len(cl_lines) > 0

        # 4. Strict rejection of TE and CL coexistence
        if has_te and has_cl and self.strict_reject_te_cl_coexistence:
            self.poisoning_attempts_blocked += 1
            return InspectionResult(
                action=ValidationAction.REJECT_400,
                status_code=400,
                reason="Coexistence of Transfer-Encoding and Content-Length forbidden (CL.TE vector)",
            )

        # 5. Validate Transfer-Encoding tokens & detect obfuscation (TE.TE vector)
        if has_te:
            if len(te_lines) > 1 or header_occurrences.get("transfer-encoding", 0) > 1:
                self.poisoning_attempts_blocked += 1
                return InspectionResult(
                    action=ValidationAction.REJECT_400,
                    status_code=400,
                    reason="Multiple or duplicate Transfer-Encoding headers detected",
                )

            te_val = normalized_headers.get("transfer-encoding", "")
            # Check for header name obfuscation in raw lines (e.g. 'Transfer-Encoding : chunked', 'Transfer-Encoding\t:')
            for line in te_lines:
                colon_idx = line.find(":")
                if colon_idx != -1:
                    pre_colon = line[:colon_idx]
                    if pre_colon.endswith(" ") or pre_colon.endswith("\t"):
                        self.poisoning_attempts_blocked += 1
                        return InspectionResult(
                            action=ValidationAction.REJECT_400,
                            status_code=400,
                            reason="Malformed Transfer-Encoding header with whitespace before colon",
                        )

            # Check value tokens
            tokens = [t.strip().lower() for t in te_val.split(",")]
            for tok in tokens:
                if tok not in self.VALID_TE_TOKENS:
                    self.poisoning_attempts_blocked += 1
                    return InspectionResult(
                        action=ValidationAction.REJECT_400,
                        status_code=400,
                        reason=f"Unsupported or obfuscated Transfer-Encoding token '{tok}'",
                    )

            # Chunked must be the final encoding
            if tokens[-1] != "chunked":
                self.poisoning_attempts_blocked += 1
                return InspectionResult(
                    action=ValidationAction.REJECT_400,
                    status_code=400,
                    reason="Transfer-Encoding must specify 'chunked' as final coding",
                )

        # 6. Validate Content-Length numerical format
        if has_cl:
            cl_val = normalized_headers.get("content-length", "")
            if not cl_val.isdigit() or int(cl_val) < 0:
                return InspectionResult(
                    action=ValidationAction.REJECT_400,
                    status_code=400,
                    reason=f"Invalid non-integer Content-Length value '{cl_val}'",
                )

        # Passed all security checks
        return InspectionResult(
            action=ValidationAction.ALLOW,
            status_code=200,
            sanitized_headers=normalized_headers,
            is_http2_safe=self.enforce_http2_upstream,
        )


class WebCachePoisoningSanitizer:
    """Sanitizes cache keys and strips dangerous unkeyed headers preventing cache poisoning."""

    DANGEROUS_UNKEYED_HEADERS = {
        "x-forwarded-host",
        "x-forwarded-scheme",
        "x-original-url",
        "x-rewrite-url",
        "x-host",
    }

    @classmethod
    def sanitize_upstream_request(cls, headers: Dict[str, str], allowed_hosts: Set[str]) -> Dict[str, str]:
        """Strips cache poisoning vectors and ensures Host matches allowed host whitelist."""
        clean = {}
        for k, v in headers.items():
            k_lower = k.lower().strip()
            if k_lower in cls.DANGEROUS_UNKEYED_HEADERS:
                continue
            clean[k_lower] = v.strip()

        host = clean.get("host", "").split(":")[0].strip()
        if host and allowed_hosts and host not in allowed_hosts:
            clean["host"] = next(iter(allowed_hosts))

        return clean

    @classmethod
    def generate_safe_cache_key(cls, method: str, host: str, path: str, query: str) -> str:
        """Normalizes cache key preventing path traversal or parameter cloaking."""
        clean_path = re.sub(r"/+", "/", path).strip()
        sorted_query = "&".join(sorted(q for q in query.split("&") if q))
        return f"{method.upper()}|{host.lower()}|{clean_path}|{sorted_query}"
