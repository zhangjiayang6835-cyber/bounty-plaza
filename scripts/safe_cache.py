"""Small on-disk cache that never executes Python object deserializers."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class CacheFormatError(ValueError):
    """Raised when a cache entry is invalid or exceeds the configured limit."""


def write_cache(path: str | Path, value: Any) -> None:
    """Persist JSON-compatible data atomically."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        payload = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
    except (TypeError, ValueError) as exc:
        raise CacheFormatError("cache value must be JSON serializable") from exc
    fd, temporary = tempfile.mkstemp(prefix=f".{target.name}.", dir=target.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def read_cache(path: str | Path, *, max_bytes: int = 2 * 1024 * 1024) -> Any:
    """Read a cache entry as JSON; legacy pickle payloads are not accepted."""
    target = Path(path)
    try:
        if target.stat().st_size > max_bytes:
            raise CacheFormatError("cache entry exceeds size limit")
        raw = target.read_bytes()
    except FileNotFoundError:
        return None
    try:
        return json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CacheFormatError("invalid JSON cache entry") from exc
