"""
Agent Card Discovery Package.

Deterministic, fault-tolerant Agent2Agent (A2A) Agent Card discovery and validation.
"""

from .canonical_url import canonicalize_url
from .discovery import (
    build_well_known_url,
    discover_card,
    discover_many,
    fetch_card_payload,
)
from .errors import (
    DiscoveryError,
    InvalidFieldTypeError,
    InvalidUrlError,
    MissingFieldError,
    NetworkError,
    SecurityViolationError,
    ValidationError,
)
from .models import AgentCard, AgentInterface, AgentSkill, normalize_string_list

__all__ = [
    "AgentCard",
    "AgentInterface",
    "AgentSkill",
    "DiscoveryError",
    "InvalidFieldTypeError",
    "InvalidUrlError",
    "MissingFieldError",
    "NetworkError",
    "SecurityViolationError",
    "ValidationError",
    "build_well_known_url",
    "canonicalize_url",
    "discover_card",
    "discover_many",
    "fetch_card_payload",
    "normalize_string_list",
]
