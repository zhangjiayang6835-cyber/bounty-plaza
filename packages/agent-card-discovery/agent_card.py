"""Deterministic A2A agent-card discovery.

Small, dependency-free resolver for A2A (Agent2Agent) agent cards. The
implementation is intentionally deterministic so that discovery behaviour can
be asserted in tests without network access: the resolver relies only on the
injected fetcher callable and the declared well-known path template.

Responsibilities:

* build the canonical well-known URL for a base origin,
* normalise and validate a fetched agent-card document,
* merge capability declarations into a stable, sorted view,
* report precise, typed discovery errors,
* gracefully fall back across specification versions,
* discover cards across multiple origins fault-tolerantly.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence
from urllib.parse import urlparse

__all__ = [
    "AgentCard",
    "DiscoveryError",
    "CardValidationError",
    "AgentCardResolver",
    "WELL_KNOWN_PATH",
    "SUPPORTED_VERSIONS",
    "BASE_VERSION",
    "well_known_url",
    "normalise",
]

WELL_KNOWN_PATH: str = "/.well-known/agent-card.json"
SUPPORTED_VERSIONS: Sequence[str] = ("1.0", "1.1")
BASE_VERSION: str = "1.0"


class DiscoveryError(RuntimeError):
    """Raised when an agent card cannot be retrieved or parsed."""

    def __init__(self, origin: str, reason: str) -> None:
        super().__init__(f"Discovery error for origin '{origin}': {reason}")
        self.origin = origin
        self.reason = reason


class CardValidationError(DiscoveryError):
    """Raised when an agent card document violates structural constraints."""

    def __init__(
        self,
        origin: str,
        missing_fields: Sequence[str] = (),
        invalid_fields: Sequence[str] = ()
    ) -> None:
        details: List[str] = []
        if missing_fields:
            details.append(f"missing required field(s): [{', '.join(missing_fields)}]")
        if invalid_fields:
            details.append(f"invalid field(s): [{', '.join(invalid_fields)}]")
        reason = "; ".join(details) if details else "card validation failed"
        super().__init__(origin, reason)
        self.missing_fields = tuple(missing_fields)
        self.invalid_fields = tuple(invalid_fields)


@dataclass(frozen=True)
class AgentCard:
    """Immutable representation of a discovered and validated agent card."""

    name: str
    url: str
    version: str = BASE_VERSION
    description: str = ""
    capabilities: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.name or not isinstance(self.name, str):
            raise TypeError("AgentCard name must be a non-empty string")
        if not self.url or not isinstance(self.url, str):
            raise TypeError("AgentCard url must be a non-empty string")

        # Guarantee internal storage is immutable tuple / dict copy
        object.__setattr__(self, "capabilities", tuple(self.capabilities))
        object.__setattr__(self, "skills", tuple(self.skills))
        object.__setattr__(self, "metadata", dict(self.metadata))

    def supports(self, capability: str) -> bool:
        """Checks if a skill or capability is supported by this agent."""
        if not capability or not isinstance(capability, str):
            return False
        needle = capability.strip().lower()
        supported = {c.lower() for c in self.capabilities} | {s.lower() for s in self.skills}
        return needle in supported

    def as_dict(self) -> Dict[str, Any]:
        """Returns a JSON-serializable dictionary representation."""
        return {
            "name": self.name,
            "url": self.url,
            "version": self.version,
            "description": self.description,
            "capabilities": list(self.capabilities),
            "skills": list(self.skills),
            "metadata": dict(self.metadata),
        }


def well_known_url(origin: str, path: str = WELL_KNOWN_PATH) -> str:
    """Builds canonical well-known URL for an origin.

    Validates scheme (http/https only) and hostname, strips default ports,
    and appends the well-known discovery path.
    """
    if not origin or not isinstance(origin, str):
        raise DiscoveryError(str(origin), "Origin must be a non-empty string")

    parsed = urlparse(origin)
    scheme = (parsed.scheme or "").lower()

    if scheme not in ("http", "https"):
        raise DiscoveryError(
            origin,
            f"Invalid scheme '{scheme}': only http and https are permitted",
        )

    if not parsed.netloc or not parsed.hostname:
        raise DiscoveryError(
            origin,
            "Invalid host: origin must contain a valid hostname",
        )

    hostname = parsed.hostname.lower()
    port = parsed.port

    # Strip standard default ports
    if (scheme == "http" and port == 80) or (scheme == "https" and port == 443):
        port = None

    netloc = f"{hostname}:{port}" if port else hostname
    canonical_origin = f"{scheme}://{netloc}"

    clean_path = path if path.startswith("/") else f"/{path}"
    query = f"?{parsed.query}" if parsed.query else ""

    return f"{canonical_origin}{clean_path}{query}"


def normalise_capabilities(items: Any) -> List[str]:
    """Normalizes an iterable of capability/skill items.

    Coerces items to strings, trims whitespace, deduplicates, and sorts alphabetically.
    """
    if not items or not isinstance(items, Iterable) or isinstance(items, (str, bytes)):
        return []

    unique_items = set()
    for item in items:
        if item is None:
            continue
        cleaned = str(item).strip()
        if cleaned:
            unique_items.add(cleaned)

    return sorted(unique_items)


def normalise_metadata(raw_metadata: Any) -> Dict[str, str]:
    """Flattens metadata to a Dict[str, str], discarding non-scalars."""
    if not isinstance(raw_metadata, dict):
        return {}

    result: Dict[str, str] = {}
    for key, val in raw_metadata.items():
        if val is None:
            continue
        if isinstance(val, (str, int, float, bool)):
            result[str(key).strip()] = str(val)

    return result


def normalise_version(raw_version: Any) -> str:
    """Selects supported version, falling back to base version for unsupported ones."""
    if not raw_version or not isinstance(raw_version, str):
        return BASE_VERSION
    cleaned = raw_version.strip()
    if cleaned in SUPPORTED_VERSIONS:
        return cleaned
    return BASE_VERSION


def normalise(origin: str, doc: Any) -> AgentCard:
    """Validates and normalizes raw agent card dictionary into an AgentCard."""
    if not isinstance(doc, dict):
        raise CardValidationError(origin, (), ("agent card document must be an object",))

    missing: List[str] = []
    invalid: List[str] = []

    # Validate name
    if "name" not in doc or doc["name"] is None:
        missing.append("name")
    elif not isinstance(doc["name"], str) or not doc["name"].strip():
        invalid.append("name (must be non-empty string)")

    # Validate url
    if "url" not in doc or doc["url"] is None:
        missing.append("url")
    elif not isinstance(doc["url"], str) or not doc["url"].strip():
        invalid.append("url (must be non-empty string)")

    if missing or invalid:
        raise CardValidationError(origin, missing, invalid)

    name = str(doc["name"]).strip()
    url = str(doc["url"]).strip()
    version = normalise_version(doc.get("version"))
    desc_val = doc.get("description", "")
    description = str(desc_val).strip() if isinstance(desc_val, str) else ""

    capabilities = normalise_capabilities(doc.get("capabilities", []))
    skills = normalise_capabilities(doc.get("skills", []))
    metadata = normalise_metadata(doc.get("metadata", {}))

    return AgentCard(
        name=name,
        url=url,
        version=version,
        description=description,
        capabilities=capabilities,
        skills=skills,
        metadata=metadata,
    )


class AgentCardResolver:
    """Resolver for discovering, parsing, and normalizing agent cards."""

    def __init__(
        self,
        fetcher: Optional[Callable[[str], Optional[Dict[str, Any]]]] = None,
        well_known_path: str = WELL_KNOWN_PATH,
    ) -> None:
        self.fetcher = fetcher
        self.well_known_path = well_known_path

    def well_known_url(self, origin: str) -> str:
        """Returns canonical well-known URL for an origin."""
        return well_known_url(origin, self.well_known_path)

    def normalise(self, origin: str, doc: Any) -> AgentCard:
        """Validates and normalizes an agent card dictionary."""
        return normalise(origin, doc)

    def discover(self, origin: str) -> AgentCard:
        """Discovers and parses an agent card from origin."""
        target_url = self.well_known_url(origin)
        if self.fetcher is None:
            raise DiscoveryError(origin, "No fetcher callable configured on AgentCardResolver")

        try:
            doc = self.fetcher(target_url)
        except Exception as exc:  # pylint: disable=broad-except
            raise DiscoveryError(origin, f"Fetcher failed for URL '{target_url}': {exc}") from exc

        if not doc or not isinstance(doc, dict):
            raise DiscoveryError(origin, f"Empty response or card not found at '{target_url}'")

        return self.normalise(origin, doc)

    def discover_many(self, origins: Iterable[str]) -> List[AgentCard]:
        """Discovers agent cards for multiple origins, skipping failing ones."""
        if not origins:
            return []

        results: List[AgentCard] = []
        for origin in origins:
            try:
                card = self.discover(origin)
                results.append(card)
            except Exception:  # pylint: disable=broad-except
                # Skip failing origin to ensure batch continuity
                continue

        return results
