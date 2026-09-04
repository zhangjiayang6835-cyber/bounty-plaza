import json

import pytest

from scripts.safe_cache import CacheFormatError, read_cache, write_cache


def test_round_trip_json(tmp_path):
    path = tmp_path / "cache.json"
    write_cache(path, {"answer": 42, "items": ["a", "b"]})
    assert read_cache(path) == {"answer": 42, "items": ["a", "b"]}


def test_missing_entry_is_cache_miss(tmp_path):
    assert read_cache(tmp_path / "missing.json") is None


def test_rejects_pickle_bytes(tmp_path):
    path = tmp_path / "cache.bin"
    path.write_bytes(b"\x80\x04cos\nsystem\n.")
    with pytest.raises(CacheFormatError, match="invalid JSON"):
        read_cache(path)


def test_rejects_oversized_entry(tmp_path):
    path = tmp_path / "cache.json"
    path.write_text(json.dumps({"x": "0123456789"}), encoding="utf-8")
    with pytest.raises(CacheFormatError, match="size limit"):
        read_cache(path, max_bytes=5)


def test_rejects_non_json_values(tmp_path):
    with pytest.raises(CacheFormatError, match="JSON serializable"):
        write_cache(tmp_path / "cache.json", {"bad": {1, 2}})
