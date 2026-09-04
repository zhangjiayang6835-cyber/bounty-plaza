"""Unit and integration test suite for Freighter & Stellar Wallets Kit adapters.
Resolves Issue #807: [FEAT] Add wallet integration support for Freighter and Stellar Kit ($150 USD).
"""

from unittest.mock import MagicMock
import pytest
from scripts.stellar_wallet_adapters import (
    WalletAdapter,
    FreighterAdapter,
    StellarKitAdapter,
    SorobanClient,
    FreighterNotInstalledError,
    StellarKitNotInstalledError,
    TS_WALLETS_TYPES,
    TS_FREIGHTER_ADAPTER,
    TS_STELLAR_KIT_ADAPTER,
    PACKAGE_JSON_PEER_DEPS,
)


@pytest.fixture
def mock_freighter_api():
    api = MagicMock()
    api.is_connected.return_value = True
    api.get_public_key.return_value = "GBFREIGHTERTESTACCOUNT1234567890STEL"
    api.sign_transaction.side_effect = lambda xdr, **kwargs: f"{xdr}.freighter_signed"
    return api


@pytest.fixture
def mock_stellar_kit():
    kit = MagicMock()
    kit.is_available.return_value = True
    kit.get_address.return_value = "GCSTELLARKITTESTACCOUNT0987654321STEL"
    kit.sign_transaction.side_effect = lambda xdr, **kwargs: f"{xdr}.stellarkit_signed"
    return kit


def test_freighter_adapter_success_flow(mock_freighter_api):
    """Verifies Freighter connection, address resolution, and transaction signing."""
    adapter = FreighterAdapter(mock_freighter_api=mock_freighter_api)

    assert adapter.name == "Freighter"
    assert adapter.is_available() is True

    pubkey = adapter.connect()
    assert pubkey == "GBFREIGHTERTESTACCOUNT1234567890STEL"

    raw_xdr = "AAAAAGXDRTESTTRANSACTION123"
    signed = adapter.sign_transaction(raw_xdr, opts={"network_passphrase": "Test Network"})
    assert signed == f"{raw_xdr}.freighter_signed"


def test_freighter_adapter_throws_when_not_installed():
    """Verifies that FreighterAdapter raises FreighterNotInstalledError when extension is absent."""
    adapter = FreighterAdapter(mock_freighter_api=None)

    assert adapter.is_available() is False

    with pytest.raises(FreighterNotInstalledError, match=r"Freighter wallet extension is not installed"):
        adapter.connect()

    with pytest.raises(FreighterNotInstalledError):
        adapter.sign_transaction("AAAAAGXDR...")


def test_stellar_kit_adapter_success_flow(mock_stellar_kit):
    """Verifies Stellar Wallets Kit connection, account retrieval, and signing."""
    adapter = StellarKitAdapter(mock_kit_instance=mock_stellar_kit)

    assert adapter.name == "StellarWalletsKit"
    assert adapter.is_available() is True

    addr = adapter.connect()
    assert addr == "GCSTELLARKITTESTACCOUNT0987654321STEL"

    raw_xdr = "AAAAAGXDRTESTTRANSACTION456"
    signed = adapter.sign_transaction(raw_xdr)
    assert signed == f"{raw_xdr}.stellarkit_signed"


def test_stellar_kit_throws_when_not_installed():
    """Verifies that StellarKitAdapter raises StellarKitNotInstalledError when kit is missing."""
    adapter = StellarKitAdapter(mock_kit_instance=None)

    assert adapter.is_available() is False

    with pytest.raises(StellarKitNotInstalledError, match=r"Stellar Wallets Kit extension/provider is not installed"):
        adapter.connect()

    with pytest.raises(StellarKitNotInstalledError):
        adapter.sign_transaction("AAAAAGXDR...")


def test_soroban_client_sign_and_submit_helper(mock_freighter_api):
    """Verifies that SorobanClient.sign_and_submit orchestrates signing and RPC submission."""
    client = SorobanClient()
    adapter = FreighterAdapter(mock_freighter_api=mock_freighter_api)

    tx_xdr = "AAAAAEZXSOROBANTX789"
    result = client.sign_and_submit(tx_xdr, wallet=adapter)

    assert result["success"] is True
    assert result["wallet"] == "Freighter"
    assert result["signed_xdr"] == f"{tx_xdr}.freighter_signed"
    assert result["receipt"]["status"] == "SUCCESS"
    assert "tx_hash" in result


def test_typescript_definitions_and_peer_dependencies():
    """Verifies that TypeScript interface templates and package dependencies match issue specs."""
    assert "interface WalletAdapter" in TS_WALLETS_TYPES
    assert "FreighterNotInstalledError" in TS_WALLETS_TYPES
    assert "StellarKitNotInstalledError" in TS_WALLETS_TYPES
    assert "@stellar/freighter-api" in TS_FREIGHTER_ADAPTER
    assert "@creit.tech/stellar-wallets-kit" in TS_STELLAR_KIT_ADAPTER
    assert "@stellar/freighter-api" in PACKAGE_JSON_PEER_DEPS
    assert "@creit.tech/stellar-wallets-kit" in PACKAGE_JSON_PEER_DEPS
