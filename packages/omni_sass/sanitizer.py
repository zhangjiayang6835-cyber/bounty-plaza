"""Security validator and sanitizer for CSS and SASS stylesheets."""

import re
from typing import List


class StyleSanitizer:
    """Detects and strips potentially malicious directives and script vectors in stylesheets."""

    DISALLOWED_PATTERNS = [
        (re.compile(r"expression\s*\(", re.IGNORECASE), "Dynamic CSS expression execution"),
        (re.compile(r"javascript\s*:", re.IGNORECASE), "Inline JavaScript URI scheme"),
        (re.compile(r"vbscript\s*:", re.IGNORECASE), "VBScript URI scheme"),
        (re.compile(r"-moz-binding\s*:", re.IGNORECASE), "Mozilla XBL binding injection"),
        (re.compile(r"behavior\s*:", re.IGNORECASE), "IE behavior script attachment"),
        (
            re.compile(r"@import\s+['\"]?(?:javascript|data:text/html)", re.IGNORECASE),
            "Malicious @import target",
        ),
        (re.compile(r"@document\s", re.IGNORECASE), "Disallowed @document directive"),
    ]

    URL_PATTERN = re.compile(r"url\s*\(\s*['\"]?(.*?)['\"]?\s*\)", re.IGNORECASE)

    def __init__(self, allowed_domains: List[str] = None) -> None:
        """Initialize sanitizer with optional domain whitelist."""
        self.allowed_domains = allowed_domains or []

    def find_violations(self, stylesheet_text: str) -> List[str]:
        """Scan stylesheet content and return list of security violations."""
        detected = []
        for pattern, description in self.DISALLOWED_PATTERNS:
            if pattern.search(stylesheet_text):
                detected.append(description)

        for match in self.URL_PATTERN.finditer(stylesheet_text):
            target_url = match.group(1).strip()
            if target_url.startswith(("http://", "https://")) and self.allowed_domains:
                domain_permitted = any(
                    target_url.startswith(domain) for domain in self.allowed_domains
                )
                if not domain_permitted:
                    detected.append(f"Unauthorized external URL resource: {target_url}")

        return detected

    def is_safe(self, stylesheet_text: str) -> bool:
        """Return True if the stylesheet contains zero detected security violations."""
        return len(self.find_violations(stylesheet_text)) == 0

    def sanitize(self, stylesheet_text: str) -> str:
        """Strip dangerous constructs and neutralize prohibited vectors from the stylesheet."""
        cleaned = stylesheet_text
        for pattern, _ in self.DISALLOWED_PATTERNS:
            cleaned = pattern.sub("/* blocked_vector */", cleaned)
        return cleaned
