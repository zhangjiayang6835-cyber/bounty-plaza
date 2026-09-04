"""HTTP Request Framing Validator & Request Smuggling Defense.
Resolves Issue #294: CL.TE HTTP Request Smuggling -> Cache Poisoning Defense ($200).
Compliant with RFC 7230 Section 3.3.3 and RFC 9112 Section 6.1.
Enforces mutual exclusion between Content-Length and Transfer-Encoding,
rejects obfuscated/malformed headers, and normalizes framing.
"""

import re
from typing import Dict, List, Optional, Set, Tuple


class HTTPSmugglingSecurityError(ValueError):
    """Raised when HTTP request headers contain ambiguous framing or smuggling vectors."""
    pass


class MalformedHeaderError(HTTPSmugglingSecurityError):
    """Raised when Transfer-Encoding or Content-Length format is malformed or obfuscated."""
    pass


class AmbiguousFramingError(HTTPSmugglingSecurityError):
    """Raised when both Content-Length and Transfer-Encoding are present (CL.TE / TE.CL conflict)."""
    pass


VALID_TRANSFER_ENCODINGS: Set[str] = {"chunked", "compress", "deflate", "gzip"}
OBSCURE_SPACE_CHARS = {"\t", "\x0b", "\x0c", "\x00"}


class HTTPFramingValidator:
    """Zero-dependency HTTP request header framing and deserialization validator.
    Strictly prevents CL.TE and TE.CL HTTP request smuggling and pipeline desync attacks.
    """

    @staticmethod
    def _find_header_variants(headers: Dict[str, str], target_name: str) -> List[Tuple[str, str]]:
        """Case-insensitively find all occurrences of a header and identify duplicate or obfuscated forms."""
        target_lower = target_name.lower().strip()
        matches = []
        for k, v in headers.items():
            # Check for control characters or weird whitespace in header name
            clean_k = k.strip().lower()
            if any(ch in k for ch in OBSCURE_SPACE_CHARS):
                raise MalformedHeaderError(f"Obfuscated header name detected with control whitespace: {repr(k)}")
            if clean_k == target_lower:
                matches.append((k, str(v)))
        return matches

    def validate_request_framing(
        self,
        headers: Dict[str, str],
        protocol_version: str = "HTTP/1.1",
    ) -> Dict[str, str]:
        """Validate and sanitize request framing headers.

        Args:
            headers: Raw dictionary of HTTP headers.
            protocol_version: Protocol string (e.g. 'HTTP/1.1', 'HTTP/2', 'HTTP/3').

        Returns:
            Dict containing normalized, safe framing headers.

        Raises:
            AmbiguousFramingError: If both Content-Length and Transfer-Encoding are present.
            MalformedHeaderError: If Content-Length or Transfer-Encoding headers are corrupted or duplicate.
        """
        # If HTTP/2 or HTTP/3, binary multiplexed framing is used and TE/CL are prohibited or redundant
        is_h2 = protocol_version.upper().startswith("HTTP/2") or protocol_version.upper().startswith("HTTP/3")

        te_matches = self._find_header_variants(headers, "Transfer-Encoding")
        cl_matches = self._find_header_variants(headers, "Content-Length")

        # In HTTP/2+, Transfer-Encoding is strictly forbidden (RFC 7540 §8.1.2.2)
        if is_h2:
            if te_matches:
                raise MalformedHeaderError("Transfer-Encoding is prohibited in HTTP/2+ streams")
            return {
                "validated": "true",
                "protocol": protocol_version,
                "framing": "multiplexed",
            }

        # 1. Reject duplicate headers of the same type
        if len(te_matches) > 1:
            raise MalformedHeaderError(
                f"Duplicate Transfer-Encoding headers detected: {len(te_matches)} instances."
            )
        if len(cl_matches) > 1:
            # All CL headers must have identical numerical value or be rejected
            cl_values = {v.strip() for _, v in cl_matches}
            if len(cl_values) > 1:
                raise MalformedHeaderError(
                    f"Conflicting Content-Length headers detected: {cl_values}"
                )

        has_te = len(te_matches) == 1
        has_cl = len(cl_matches) >= 1

        # 2. Invariant: TE and CL must NEVER exist concurrently in the same request (RFC 7230 §3.3.3 #3)
        if has_te and has_cl:
            raise AmbiguousFramingError(
                "CL.TE request smuggling vector neutralized: Both Transfer-Encoding and Content-Length are present. "
                "Simultaneous existence is prohibited."
            )

        sanitized_headers: Dict[str, str] = {}

        # 3. Validate Transfer-Encoding if present
        if has_te:
            _, raw_te = te_matches[0]
            # Check for obfuscations (e.g. "chunked, identity", "cow chunked", trailing invalid tokens)
            if any(ch in raw_te for ch in OBSCURE_SPACE_CHARS):
                raise MalformedHeaderError(f"Obfuscated Transfer-Encoding whitespace detected: {repr(raw_te)}")

            # Parse transfer encodings list
            encodings = [e.strip().lower() for e in raw_te.split(",") if e.strip()]
            if not encodings:
                raise MalformedHeaderError("Transfer-Encoding header is empty or pure commas")

            for enc in encodings:
                if enc not in VALID_TRANSFER_ENCODINGS:
                    raise MalformedHeaderError(f"Unsupported or malformed Transfer-Encoding: '{enc}'")

            # Final encoding MUST be chunked in HTTP/1.1
            if encodings[-1] != "chunked":
                raise MalformedHeaderError(
                    f"Final Transfer-Encoding must be 'chunked', received '{encodings[-1]}'"
                )

            sanitized_headers["Transfer-Encoding"] = "chunked"
            sanitized_headers["Framing-Type"] = "chunked"

        # 4. Validate Content-Length if present
        elif has_cl:
            _, raw_cl = cl_matches[0]
            clean_cl = raw_cl.strip()
            # Must be purely non-negative decimal digits
            if not clean_cl.isdigit():
                raise MalformedHeaderError(f"Content-Length must be a valid non-negative integer, got: '{raw_cl}'")

            cl_int = int(clean_cl)
            if cl_int < 0:
                raise MalformedHeaderError("Negative Content-Length is prohibited")

            sanitized_headers["Content-Length"] = str(cl_int)
            sanitized_headers["Framing-Type"] = "content-length"

        else:
            sanitized_headers["Framing-Type"] = "none"

        return sanitized_headers
