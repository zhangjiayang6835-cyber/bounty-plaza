"""Deterministic A2A agent-card discovery.

Small, dependency-free resolver for A2A (Agent2Agent) agent cards. The
implementation is intentionally deterministic so that discovery behaviour can
be asserted in tests without network access: the resolver relies only on the
injected fetcher callable and the declared well-known path template.

Responsibilities:

* build the canonical well-known URL for a base origin,
* normalise and validate a fetched agent-card document,
* merge capability declarations into a stable, sorted view,
* report precise, typed discovery errors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

__all__ = [
    "AgentCard",
    "DiscoveryError",
    "CardValidationError",
    "AgentCardResolver",
    "WELL_KNOWN_PATH",
]

WELL_KNOWN_PATH = "/.well-known/agent-card.json"

SUPPORTED_VERSIONS = ("1.0", "1.1")


class DiscoveryError(RuntimeError):
    """Raised when an agent card cannot be retrieved or parsed."""

    def __init__(self, origin: str, reason: str) -> None:
        """Store the origin and the human readable reason."""
        super().__init__(f"discovery failed for {origin}: {reason}")
        self.origin = origin
        self.reason = reason


class CardValidationError(ValueError):
    """Raised when a fetched agent card document is structurally invalid."""

    def __init__(self, missing: Sequence[str]) -> None:
        """Store the list of missing or invalid fields."""
        super().__init__("invalid agent card: " + ", ".join(missing))
        self.missing: List[str] = list(missing)


@dataclass(frozen=True)
class AgentCard:
    """A normalised A2A agent card."""

    name: str
    version: str
    url: str
    capabilities: Sequence[str] = field(default_factory=tuple)
    skills: Sequence[str] = field(default_factory=tuple)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate the required card fields."""
        if not self.name:
            raise CardValidationError(["name"])
        if not self.url:
            raise CardValidationError(["url"])

    def supports(self, capability: str) -> bool:
        """Return True when the card declares ``capability``."""
        return capability in self.capabilities

    def as_dict(self) -> Dict[str, object]:
        """Return a JSON-serialisable view of the card."""
        return {
            "name": self.name,
            "version": self.version,
            "url": self.url,
            "capabilities": list(self.capabilities),
            "skills": list(self.skills),
            "metadata": dict(self.metadata),
        }


class AgentCardResolver:
    """Resolve agent cards from origins through an injected fetcher."""

    def __init__(
        self,
        fetcher: Callable[[str], Optional[Dict[str, object]]],
        well_known_path: str = WELL_KNOWN_PATH,
    ) -> None:
        """Create a resolver backed by ``fetcher``."""
        self._fetcher = fetcher
        self._well_known_path = well_known_path

    def well_known_url(self, origin: str) -> str:
        """Return the canonical well-known URL for ``origin``."""
        parsed = urlparse(origin)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise DiscoveryError(origin, "unsupported origin")
        return f"{parsed.scheme}://{parsed.netloc}{self._well_known_path}"

    def discover(self, origin: str) -> AgentCard:
        """Fetch and normalise the agent card published at ``origin``."""
        url = self.well_known_url(origin)
        document = self._fetcher(url)
        if not document:
            raise DiscoveryError(origin, "empty response")
        return self.normalise(document)

    def discover_many(self, origins: Iterable[str]) -> Dict[str, AgentCard]:
        """Resolve several origins, skipping the ones that fail."""
        resolved: Dict[str, AgentCard] = {}
        for origin in origins:
            try:
                resolved[origin] = self.discover(origin)
            except (DiscoveryError, CardValidationError):
                continue
        return resolved

    @staticmethod
    def normalise(document: Dict[str, object]) -> AgentCard:
        """Validate and normalise a raw agent card document."""
        missing: List[str] = []
        name = document.get("name")
        url = document.get("url")
        if not isinstance(name, str) or not name:
            missing.append("name")
        if not isinstance(url, str) or not url:
            missing.append("url")
        if missing:
            raise CardValidationError(missing)

        version = document.get("version", SUPPORTED_VERSIONS[0])
        if not isinstance(version, str):
            version = SUPPORTED_VERSIONS[0]
        if version not in SUPPORTED_VERSIONS:
            version = SUPPORTED_VERSIONS[0]

        capabilities = AgentCardResolver._string_list(document.get("capabilities"))
        skills = AgentCardResolver._string_list(document.get("skills"))

        return AgentCard(
            name=name,
            version=version,
            url=url,
            capabilities=tuple(sorted(set(capabilities))),
            skills=tuple(sorted(set(skills))),
            metadata=AgentCardResolver._metadata(document.get("metadata")),
        )

    @staticmethod
    def _string_list(value: object) -> List[str]:
        """Coerce ``value`` into a list of non-empty strings."""
        if not isinstance(value, (list, tuple)):
            return []
        return [item.strip() for item in value
                if isinstance(item, str) and item.strip()]

    @staticmethod
    def _metadata(value: object) -> Dict[str, str]:
        """Coerce ``value`` into a flat string-to-string mapping."""
        if not isinstance(value, dict):
            return {}
        return {
            str(key): str(item)
            for key, item in value.items()
            if isinstance(item, (str, int, float, bool))
        }


def main() -> None:
    """Run a tiny deterministic demonstration of the resolver."""
    documents = {
        "https://agent-a.example/.well-known/agent-card.json": {
            "name": "agent-a",
            "version": "1.1",
            "url": "https://agent-a.example",
            "capabilities": ["streaming", "tasks"],
            "skills": ["translate"],
            "metadata": {"region": "eu"},
        }
    }
    resolver = AgentCardResolver(lambda url: documents.get(url))
    card = resolver.discover("https://agent-a.example")
    print("card:", card.as_dict())
    print("supports streaming:", card.supports("streaming"))


if __name__ == "__main__":
    main()
