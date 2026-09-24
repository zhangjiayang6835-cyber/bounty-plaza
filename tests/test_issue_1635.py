"""Comprehensive verification test suite for Issue #1635 stipulations."""

import io
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.rpc_failover.client import (
    BASE_CHAIN_ID,
    RpcClient,
    RpcError,
    RpcFailoverError,
    TransportError,
    redact_rpc_endpoint,
    rpc,
    rpc_call,
    rpc_failover,
    select_working_base_rpc,
)
from packages.rpc_failover.models import SettlementTerms
from packages.rpc_failover.settlement import SettlementReconciler


class MockHttpResponse(io.BytesIO):
    """Mock HTTP response object mimicking urllib HTTP response streams."""

    def __init__(self, body: bytes, status: int = 200) -> None:
        super().__init__(body)
        self.status = status

    def getcode(self) -> int:
        """Return configured HTTP status integer."""
        return self.status

    def __enter__(self) -> "MockHttpResponse":
        return self

    def __exit__(self, *_args: object) -> bool:
        self.close()
        return False


class TestIssue1635PinnedFixture(unittest.TestCase):
    """Validation for pinned failing RPC failover fixture and stipulations."""

    def test_pinned_failing_fixture_primary_down_secondary_recovers(self) -> None:
        """Test primary failure with deterministic failover to secondary Base node."""
        primary_endpoint = "https://primary-down.local/rpc"
        secondary_endpoint = "https://secondary-ok.local/rpc"

        def simulated_urlopen(request: object, **_kwargs: object) -> MockHttpResponse:
            url = str(getattr(request, "full_url"))
            raw_data = getattr(request, "data").decode("utf-8")
            payload = json.loads(raw_data)
            req_id = payload.get("id", 1)
            method = payload.get("method")

            if "primary-down" in url:
                raise URLError("Connection refused by target peer")

            if method == "eth_chainId":
                return MockHttpResponse(
                    json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x2105"}).encode()
                )
            if method == "eth_blockNumber":
                return MockHttpResponse(
                    json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x123456"}).encode()
                )
            return MockHttpResponse(
                json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x0"}).encode()
            )

        with patch("scripts._shared.rpc.urlopen", side_effect=simulated_urlopen):
            chosen, response = rpc_call(
                [primary_endpoint, secondary_endpoint],
                method="eth_blockNumber",
                params=[],
            )
            self.assertEqual(chosen, secondary_endpoint)
            self.assertEqual(response.get("result"), "0x123456")
            self.assertEqual(response.get("id"), 1)

    def test_non_base_chain_id_rejected_during_probe(self) -> None:
        """Reject non-Base chain responses such as Ethereum Mainnet chain 1."""
        ethereum_endpoint = "https://eth-mainnet.local/rpc"

        def eth_mainnet_response(request: object, **_kwargs: object) -> MockHttpResponse:
            raw_data = getattr(request, "data").decode("utf-8")
            payload = json.loads(raw_data)
            req_id = payload.get("id", 1)
            return MockHttpResponse(
                json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x1"}).encode()
            )

        with patch("scripts._shared.rpc.urlopen", side_effect=eth_mainnet_response):
            with self.assertRaises(RuntimeError) as context:
                select_working_base_rpc(endpoints=(ethereum_endpoint,), max_retries=1)
            self.assertIn("wrong chain 1", str(context.exception))

    def test_response_id_mismatch_rejected_as_invalid(self) -> None:
        """Reject RPC responses whose id does not bind to request id."""
        endpoint = "https://mismatched-id.local/rpc"

        def mismatched_response(request: object, **_kwargs: object) -> MockHttpResponse:
            return MockHttpResponse(
                json.dumps({"jsonrpc": "2.0", "id": 999, "result": "0x2105"}).encode()
            )

        with patch("scripts._shared.rpc.urlopen", side_effect=mismatched_response):
            with self.assertRaises(RuntimeError) as context:
                rpc(endpoint, method="eth_chainId", params=[], request_id=1, attempts=1)
            self.assertIn("RPC response was invalid", str(context.exception))

    def test_terminal_rpc_error_halts_without_failover_or_retry(self) -> None:
        """Terminal execution reverted errors must raise RpcError immediately."""
        endpoint_a = "https://node-a.local/rpc"
        endpoint_b = "https://node-b.local/rpc"
        call_log: list[str] = []

        def error_response(request: object, **_kwargs: object) -> MockHttpResponse:
            url = str(getattr(request, "full_url"))
            call_log.append(url)
            raw_data = getattr(request, "data").decode("utf-8")
            payload = json.loads(raw_data)
            method = payload.get("method")
            req_id = payload.get("id", 1)

            if method == "eth_chainId":
                return MockHttpResponse(
                    json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x2105"}).encode()
                )
            return MockHttpResponse(
                json.dumps({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": "execution reverted: invalid claim"},
                }).encode()
            )

        with patch("scripts._shared.rpc.urlopen", side_effect=error_response):
            with self.assertRaises(RpcError) as context:
                rpc_failover(
                    method="eth_call",
                    params=[{"to": "0x00"}],
                    endpoints=(endpoint_a, endpoint_b),
                    max_retries=3,
                )
            self.assertIn("execution reverted", str(context.exception))
            self.assertIn("-32000", str(context.exception))
            self.assertEqual(len([u for u in call_log if "node-b" in u]), 0)

    def test_credential_redaction_in_endpoint_and_errors(self) -> None:
        """Ensure credentials and paths are completely purged from output."""
        sensitive_url = "https://user:secretpass@node.example.org:8545/path/v1?token=auth123#frag"
        redacted = redact_rpc_endpoint(sensitive_url)
        self.assertEqual(redacted, "https://node.example.org:8545")
        self.assertNotIn("secretpass", redacted)
        self.assertNotIn("auth123", redacted)
        self.assertNotIn("/path/v1", redacted)

    def test_settlement_reconciliation_financial_integrity(self) -> None:
        """Verify autonomous bounty settlement parameters for 0x26f0...13ce."""
        reconciler = SettlementReconciler()
        self.assertTrue(reconciler.verify_financial_integrity())

        summary = reconciler.serialize_summary()
        self.assertEqual(summary["network"], "base")
        self.assertEqual(
            summary["contract_address"],
            "0x26f0a0a60f8a1c12ca9b724062b9c5bfe8d013ce",
        )
        self.assertEqual(summary["solver_reward_usdc"], 0.99)
        self.assertEqual(summary["claim_bond_usdc"], 0.01)
        self.assertEqual(summary["total_funding_usdc"], 1.00)
        self.assertEqual(summary["solver_reward_base_units"], 990000)
        self.assertEqual(summary["claim_bond_base_units"], 10000)
        self.assertEqual(summary["total_funding_base_units"], 1000000)
        self.assertEqual(
            summary["solver_reward_base_units"] + summary["claim_bond_base_units"],
            summary["total_funding_base_units"],
        )

        digest = reconciler.generate_settlement_digest(bounty_id="issue-1635")
        self.assertIsInstance(digest, str)
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
