"""
Core discovery engine for A2A Agent Cards.

Provides single and batch discovery with fault-tolerance, caching,
canonical URL parsing, and typed error handling.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from .canonical_url import canonicalize_url
from .errors import DiscoveryError, NetworkError, ValidationError
from .models import AgentCard

logger = logging.getLogger("agent_card_discovery")


def build_well_known_url(base_url: str) -> str:
    """
    Given a base URL, resolve the canonical /.well-known/agent-card.json endpoint.
    """
    canon = canonicalize_url(base_url)
    if canon.endswith(("/.well-known/agent-card.json", ".json")):
        return canon
    trimmed = canon.rstrip("/")
    return f"{trimmed}/.well-known/agent-card.json"


def fetch_card_payload(
    url: str,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    opener: Callable[[Request, float], bytes] | None = None,
) -> dict[str, Any]:
    """
    Fetch and decode JSON agent card payload from a target URL.
    """
    target_url = canonicalize_url(url)
    req_headers = {
        "User-Agent": "Agent-Card-Discovery/1.0",
        "Accept": "application/json, application/a2a+json;q=0.9, text/plain;q=0.5",
    }
    if headers:
        req_headers.update(headers)

    if opener:
        req = Request(target_url, headers=req_headers)
        raw_data = opener(req, timeout)
    else:
        req = Request(target_url, headers=req_headers)
        try:
            with urlopen(req, timeout=timeout) as response:
                raw_data = response.read()
        except HTTPError as exc:
            raise NetworkError(
                f"HTTP {exc.code} fetching agent card: {exc.reason}", url=target_url
            ) from exc
        except URLError as exc:
            raise NetworkError(
                f"Network error fetching agent card: {exc.reason}", url=target_url
            ) from exc
        except Exception as exc:
            raise NetworkError(
                f"Unexpected error during card fetch: {exc}", url=target_url
            ) from exc

    try:
        data = json.loads(raw_data.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise ValidationError(f"Invalid JSON payload: {exc}", url=target_url) from exc

    if not isinstance(data, dict):
        raise ValidationError(
            f"Payload must be a JSON object, got {type(data).__name__}", url=target_url
        )

    return data


def discover_card(
    url: str,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    try_well_known: bool = True,
    opener: Callable[[Request, float], bytes] | None = None,
) -> AgentCard:
    """
    Discover and validate an Agent Card from a given URL or well-known location.

    Args:
        url: Direct card URL or base domain.
        timeout: Network timeout in seconds.
        headers: Optional custom HTTP headers.
        try_well_known: If True and direct fetch fails, fallback to /.well-known/agent-card.json.
        opener: Optional custom network opener for mocking/testing.

    Returns:
        Validated AgentCard object.

    Raises:
        DiscoveryError: If discovery or validation fails.
    """
    canonical = canonicalize_url(url)
    try:
        payload = fetch_card_payload(
            canonical, timeout=timeout, headers=headers, opener=opener
        )
        return AgentCard.from_dict(payload, context_url=canonical)
    except DiscoveryError as err:
        if try_well_known and not canonical.endswith(
            ("/.well-known/agent-card.json", ".json")
        ):
            well_known = build_well_known_url(canonical)
            logger.info(
                "Direct fetch failed for %s, falling back to %s", canonical, well_known
            )
            try:
                payload = fetch_card_payload(
                    well_known, timeout=timeout, headers=headers, opener=opener
                )
                return AgentCard.from_dict(payload, context_url=well_known)
            except Exception as wk_err:
                raise err from wk_err
        raise


def discover_many(
    urls: list[str],
    max_workers: int = 5,
    timeout: float = 10.0,
    headers: dict[str, str] | None = None,
    return_exceptions: bool = False,
    opener: Callable[[Request, float], bytes] | None = None,
) -> list[AgentCard] | tuple[list[AgentCard], list[tuple[str, DiscoveryError]]]:
    """
    Fault-tolerant batch discovery of multiple Agent Cards concurrently.

    Individual target failures do NOT abort the batch.

    Args:
        urls: List of target URLs.
        max_workers: Concurrency thread limit.
        timeout: Timeout per request in seconds.
        headers: Optional HTTP headers.
        return_exceptions: If True, returns (successful_cards, failed_url_error_pairs).
                          If False, returns only the successful cards.
        opener: Optional custom network opener for testing.

    Returns:
        List of successful AgentCards, or tuple of (successes, failures).
    """
    successes: list[AgentCard] = []
    failures: list[tuple[str, DiscoveryError]] = []

    if not urls:
        return ([], []) if return_exceptions else []

    # Deduplicate URLs deterministically
    unique_urls = []
    seen = set()
    for u in urls:
        if u and u not in seen:
            seen.add(u)
            unique_urls.append(u)

    def _worker(u: str) -> tuple[str, AgentCard | None, DiscoveryError | None]:
        try:
            card = discover_card(u, timeout=timeout, headers=headers, opener=opener)
            return (u, card, None)
        except DiscoveryError as exc:
            return (u, None, exc)
        except Exception as exc:  # noqa: BLE001
            return (u, None, DiscoveryError(f"Unexpected error: {exc}", url=u))

    workers = min(max_workers, len(unique_urls))
    with ThreadPoolExecutor(max_workers=max(1, workers)) as executor:
        future_map = {executor.submit(_worker, u): u for u in unique_urls}
        for future in as_completed(future_map):
            orig_url, card, error = future.result()
            if card is not None:
                successes.append(card)
            elif error is not None:
                failures.append((orig_url, error))
                logger.warning("Agent discovery failed for %s: %s", orig_url, error)

    # Sort successes deterministically by name / version
    successes.sort(key=lambda c: (c.name, c.version))

    if return_exceptions:
        return (successes, failures)
    return successes
