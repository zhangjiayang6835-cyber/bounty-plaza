"""Deterministic JSON-RPC failover: try each endpoint, then the next."""
from __future__ import annotations

import json
import urllib.error
import urllib.request


class RpcFailoverError(RuntimeError):
    """Raised when every configured endpoint fails or none are given."""


def _post(endpoint: str, payload: dict, timeout: float) -> dict:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        endpoint,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
            body = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RpcFailoverError(
            f"malformed json from {endpoint}: {exc}"
        ) from exc
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as exc:
        raise RpcFailoverError(
            f"transport error from {endpoint}: {exc}"
        ) from exc
    if not isinstance(body, dict):
        raise RpcFailoverError(f"malformed response from {endpoint}: {body!r}")
    if body.get("error") is not None:
        raise RpcFailoverError(f"rpc error from {endpoint}: {body['error']}")
    if "result" not in body:
        raise RpcFailoverError(f"malformed response from {endpoint}: {body!r}")
    return body


def rpc_call(
    endpoints: list[str],
    method: str,
    params: list | None = None,
    timeout: float = 5.0,
    request_id: int = 1,
    attempts_per_endpoint: int = 2,
) -> tuple[str, dict]:
    """Call ``method`` on the first endpoint that succeeds.

    Each endpoint is tried ``attempts_per_endpoint`` times so a transient
    JSON-RPC error (e.g. ``-32000`` busy) is retried before failover.
    Transport failures are also retried, then the next endpoint is used.
    Order is strictly the order of ``endpoints``; no shuffling.
    """
    if not endpoints:
        raise RpcFailoverError("no endpoints configured")
    if attempts_per_endpoint < 1:
        raise RpcFailoverError("attempts_per_endpoint must be >= 1")

    payload = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params or [],
    }
    errors: list[str] = []
    for endpoint in endpoints:
        for _ in range(attempts_per_endpoint):
            try:
                return endpoint, _post(endpoint, payload, timeout)
            except RpcFailoverError as exc:
                errors.append(str(exc))
    raise RpcFailoverError("all endpoints failed: " + " | ".join(errors))
