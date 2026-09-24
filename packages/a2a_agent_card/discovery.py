"""Deterministic discovery engine and canonical URL normalization for A2A cards."""

from __future__ import annotations

import posixpath
import urllib.parse
from typing import Any

from packages.a2a_agent_card.models import AgentCard
from packages.a2a_agent_card.validator import AgentCardValidator


class CanonicalUrlNormalizer:
    """Normalizes service URLs while preserving critical casing and path semantics."""

    DEFAULT_PORTS = {"http": 80, "https": 443}

    @classmethod
    def normalize(cls, raw_url: str) -> str:
        """Produce canonically formatted URL string.

        Preserves query parameter casing and path slash semantics while
        normalizing scheme, host, and default port numbers.

        Args:
            raw_url: Input URL string.

        Returns:
            Normalized canonical URL string.
        """
        parsed = urllib.parse.urlsplit(raw_url.strip())
        scheme = parsed.scheme.lower()
        if not scheme:
            scheme = "https"

        hostname = parsed.hostname.lower() if parsed.hostname else ""
        port = parsed.port

        if port and port != cls.DEFAULT_PORTS.get(scheme):
            normalized_netloc = f"{hostname}:{port}"
        else:
            normalized_netloc = hostname

        path = parsed.path
        if not path:
            normalized_path = "/"
        else:
            has_trailing_slash = path.endswith("/")
            normalized_segments = posixpath.normpath(path)
            if has_trailing_slash and not normalized_segments.endswith("/"):
                normalized_path = f"{normalized_segments}/"
            else:
                normalized_path = normalized_segments

        query = parsed.query
        fragment = parsed.fragment

        return urllib.parse.urlunsplit(
            (scheme, normalized_netloc, normalized_path, query, fragment)
        )

    @classmethod
    def is_canonical(cls, raw_url: str) -> bool:
        """Check whether a URL string matches its normalized form.

        Args:
            raw_url: Candidate URL string.

        Returns:
            True if URL equals its canonical normalization.
        """
        return raw_url == cls.normalize(raw_url)


class AgentCardDiscoveryEngine:
    """Discovers, validates, and serves agent cards with HTTP cache negotiation."""

    WELL_KNOWN_PATH = "/.well-known/agent-card.json"

    def __init__(self, card: AgentCard | None = None) -> None:
        """Initialize discovery engine with active agent card instance.

        Args:
            card: Optional AgentCard instance. Defaults to canonical card.
        """
        self._card = card or AgentCard.create_canonical()
        self._validator = AgentCardValidator()

    @property
    def card(self) -> AgentCard:
        """Retrieve current registered agent card.

        Returns:
            Active AgentCard instance.
        """
        return self._card

    def get_discovery_payload(self) -> tuple[dict[str, Any], dict[str, str]]:
        """Generate response payload and RFC-compliant HTTP cache headers.

        Returns:
            Tuple of JSON dictionary and header mapping.
        """
        is_valid, errors = self._validator.validate_dict(self._card.to_dict())
        if not is_valid:
            raise ValueError(f"Agent card fails validation: {errors}")

        headers = {
            "Content-Type": "application/json; charset=utf-8",
            "ETag": self._card.compute_etag(),
            "Cache-Control": "public, max-age=300, must-revalidate",
        }
        return self._card.to_dict(), headers

    def handle_conditional_request(
        self, if_none_match: str | None
    ) -> tuple[int, dict[str, Any] | None, dict[str, str]]:
        """Evaluate conditional HTTP request against current ETag.

        Args:
            if_none_match: Client If-None-Match header value.

        Returns:
            Tuple containing HTTP status code, optional body, and response headers.
        """
        payload, headers = self.get_discovery_payload()
        current_etag = headers.get("ETag", "")

        if if_none_match and if_none_match.strip() == current_etag:
            return 304, None, headers

        return 200, payload, headers
