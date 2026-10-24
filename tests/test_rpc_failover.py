"""Pinned fixture: primary is down; secondary is busy once, then serves."""
import sys
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.rpc_failover import RpcFailoverError, rpc_call


class _FakeResponse:
    def __init__(self, payload: bytes):
        self._payload = payload

    def read(self):
        return self._payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


def _fake_urlopen(req, timeout=None):
    url = req.full_url
    if url == "http://primary.local":
        raise urllib.error.URLError("connection refused")
    if url == "http://secondary.local":
        _fake_urlopen.calls += 1
        if _fake_urlopen.calls == 1:
            return _FakeResponse(
                b'{"jsonrpc":"2.0","id":1,"error":{"code":-32000,"message":"busy"}}'
            )
        return _FakeResponse(b'{"jsonrpc":"2.0","id":1,"result":"0x2105"}')
    raise AssertionError(f"unexpected endpoint {url}")


_fake_urlopen.calls = 0


class RpcFailoverTest(unittest.TestCase):
    def test_failover_skips_transport_and_rpc_errors_deterministically(self):
        _fake_urlopen.calls = 0
        with patch("src.rpc_failover.urllib.request.urlopen", side_effect=_fake_urlopen):
            endpoint, body = rpc_call(
                ["http://primary.local", "http://secondary.local"],
                "eth_chainId",
            )
        assert endpoint == "http://secondary.local"
        assert body["result"] == "0x2105"
        # primary refused twice (attempts_per_endpoint=2), then secondary busy + ok
        assert _fake_urlopen.calls == 2

    def test_all_endpoints_failed_raises(self):
        def _always_down(req, timeout=None):
            raise urllib.error.URLError("connection refused")

        with patch("src.rpc_failover.urllib.request.urlopen", side_effect=_always_down):
            try:
                rpc_call(["http://primary.local"], "eth_chainId")
            except RpcFailoverError as exc:
                assert "all endpoints failed" in str(exc)
            else:
                raise AssertionError("expected RpcFailoverError")

    def test_empty_endpoint_list_raises(self):
        try:
            rpc_call([], "eth_chainId")
        except RpcFailoverError as exc:
            assert "no endpoints" in str(exc)
        else:
            raise AssertionError("expected RpcFailoverError")


if __name__ == "__main__":
    unittest.main()
