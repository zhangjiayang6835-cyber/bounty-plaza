"""Tests for modern RpcClient and SettlementReconciler interfaces."""

import io
import json
import sys
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from packages.rpc_failover import (
    BASE_CHAIN_ID,
    EndpointConfig,
    RpcClient,
    RpcFailoverError,
    SettlementReconciler,
    SettlementTerms,
)
from src.rpc_failover import RpcClient as CompatRpcClient


class MockRpcStream(io.BytesIO):
    """Mock HTTP byte stream for testing RPC responses."""

    def __init__(self, data: bytes, status: int = 200) -> None:
        super().__init__(data)
        self.status = status

    def getcode(self) -> int:
        """Return configured HTTP status code."""
        return self.status

    def __enter__(self) -> "MockRpcStream":
        return self

    def __exit__(self, *_args: object) -> bool:
        self.close()
        return False


class TestRpcClient(unittest.TestCase):
    """Test suite covering modern RpcClient and compatibility facades."""

    def test_rpc_client_initialization_defaults(self) -> None:
        """Verify RpcClient initializes default Base endpoints correctly."""
        client = RpcClient()
        self.assertGreaterEqual(len(client.endpoints), 3)
        self.assertEqual(client.max_retries, 3)

    def test_compat_facade_matches_packages_export(self) -> None:
        """Verify src.rpc_failover exports identical client class."""
        self.assertIs(RpcClient, CompatRpcClient)

    def test_endpoint_config_dataclass(self) -> None:
        """Verify EndpointConfig model field assignment and integrity."""
        cfg = EndpointConfig(url="https://base.drpc.org", attempts=3)
        self.assertEqual(cfg.url, "https://base.drpc.org")
        self.assertEqual(cfg.attempts, 3)
        self.assertEqual(cfg.expected_chain_id, BASE_CHAIN_ID)

    def test_settlement_reconciler_unbalanced_escrow(self) -> None:
        """Verify SettlementReconciler detects unbalanced escrow funding."""
        unbalanced = SettlementTerms(
            network="base",
            contract_address="0x26f0a0a60f8a1c12ca9b724062b9c5bfe8d013ce",
            solver_reward_usdc=0.99,
            claim_bond_usdc=0.01,
            total_funding_usdc=2.00,
        )
        reconciler = SettlementReconciler(terms=unbalanced)
        self.assertFalse(reconciler.verify_financial_integrity())
        summary = reconciler.serialize_summary()
        self.assertFalse(summary["is_balanced"])

    def test_rpc_client_execute_success(self) -> None:
        """Verify client execution with mocked Base node response."""
        client = RpcClient(default_endpoints=["https://node-1.local/rpc"])

        def handler(request: object, **_kwargs: object) -> MockRpcStream:
            raw = getattr(request, "data").decode("utf-8")
            payload = json.loads(raw)
            method = payload.get("method")
            req_id = payload.get("id", 1)

            if method == "eth_chainId":
                return MockRpcStream(
                    json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x2105"}).encode()
                )
            if method == "net_version":
                return MockRpcStream(
                    json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "8453"}).encode()
                )
            return MockRpcStream(
                json.dumps({"jsonrpc": "2.0", "id": req_id, "result": "0x0"}).encode()
            )

        with patch("scripts._shared.rpc.urlopen", side_effect=handler):
            result = client.execute("net_version")
            self.assertEqual(result, "8453")

    def test_rpc_client_exhaustion_raises_failover_error(self) -> None:
        """Verify exhausted endpoints raise dedicated RpcFailoverError."""
        client = RpcClient(
            default_endpoints=["https://broken.local/rpc"],
            max_retries=1,
        )
        with patch(
            "scripts._shared.rpc.urlopen",
            side_effect=TimeoutError("Request timed out"),
        ):
            with self.assertRaises(RpcFailoverError):
                client.execute("eth_blockNumber")


if __name__ == "__main__":
    unittest.main()
