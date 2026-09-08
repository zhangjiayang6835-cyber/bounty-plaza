"""Unit and integration tests for Issue #1214 EVM Dual-Stack Gateway."""

import pytest
from packages.evm_network_gateway import (
    DualStackEVMGateway,
    EVMNetworkArchitectureAnalysis,
    EVMTransaction,
    IPGatewayConfig,
    IPVersion,
    RPCRequest,
    TCPHandshakeVerifier,
)


def test_ipv6_address_parsing_and_canonicalization() -> None:
    """Validate RFC 4291 canonical parsing of target IPv6 gateway."""
    target_ipv6 = "2001:0db8:85a3::8a2e:0370:7334"
    config = IPGatewayConfig(host=target_ipv6, port=8545)

    assert config.version == IPVersion.IPV6
    assert config.is_ipv6() is True
    assert config.canonical_ip() == "2001:db8:85a3::8a2e:370:7334"
    assert config.is_honeypot_target_address() is True


def test_ipv4_gateway_configuration() -> None:
    """Validate RFC 791 IPv4 legacy gateway configuration."""
    target_ipv4 = "192.168.1.1"
    config = IPGatewayConfig(host=target_ipv4, port=8545)

    assert config.version == IPVersion.IPV4
    assert config.is_ipv6() is False
    assert config.canonical_ip() == "192.168.1.1"
    assert config.is_honeypot_target_address() is False


def test_invalid_ip_rejection() -> None:
    """Verify that malformed IP address strings trigger ValueError."""
    with pytest.raises(ValueError, match="Invalid IP address format"):
        IPGatewayConfig(host="invalid.ip.address.format", port=8545)


def test_invalid_port_rejection() -> None:
    """Verify that out-of-range port numbers trigger ValueError."""
    with pytest.raises(ValueError, match="Port must be between 1 and 65535"):
        IPGatewayConfig(host="192.168.1.1", port=70000)


def test_dual_stack_registration_and_filtering() -> None:
    """Verify gateway registration, retrieval, and IP version filtering."""
    gateway = DualStackEVMGateway()
    gw_v4 = IPGatewayConfig(host="192.168.1.1", port=8545)
    gw_v6 = IPGatewayConfig(host="2001:0db8:85a3::8a2e:0370:7334", port=8545)

    gateway.register_gateway(gw_v4)
    gateway.register_gateway(gw_v6)

    all_gateways = gateway.get_registered_gateways()
    v4_gateways = gateway.get_registered_gateways(IPVersion.IPV4)
    v6_gateways = gateway.get_registered_gateways(IPVersion.IPV6)

    assert len(all_gateways) == 2
    assert len(v4_gateways) == 1
    assert len(v6_gateways) == 1
    assert v6_gateways[0].is_honeypot_target_address() is True


def test_gateway_selection_with_fallback() -> None:
    """Verify gateway selection honors preference with fallback mechanism."""
    gateway = DualStackEVMGateway()
    gw_v4 = IPGatewayConfig(host="192.168.1.1", port=8545)
    gateway.register_gateway(gw_v4)

    selected = gateway.select_gateway(preferred_version=IPVersion.IPV6)
    assert selected.version == IPVersion.IPV4


def test_route_transaction_zero_gas_overhead() -> None:
    """Verify EVM transaction routing executes with zero on-chain gas overhead."""
    gateway = DualStackEVMGateway()
    gw_v6 = IPGatewayConfig(host="2001:0db8:85a3::8a2e:0370:7334", port=8545)
    gateway.register_gateway(gw_v6)

    tx = EVMTransaction(
        sender="0x1111111111111111111111111111111111111111",
        recipient="0x2222222222222222222222222222222222222222",
        value_wei=1_000_000_000_000_000_000,
        gas_limit=21000,
        nonce=0,
    )

    response = gateway.route_transaction(tx, preferred_version=IPVersion.IPV6)

    assert response.on_chain_gas_consumed == 0
    assert response.ip_version == IPVersion.IPV6
    assert response.transport_ip == "2001:db8:85a3::8a2e:370:7334"
    assert response.result.startswith("0x")

    metrics = gateway.get_metrics()
    assert metrics.total_requests == 1
    assert metrics.ipv6_requests == 1
    assert metrics.ipv4_requests == 0
    assert metrics.on_chain_gas_incurred == 0


def test_tcp_verifier_ip_validation() -> None:
    """Verify transport verifier differentiates IPv4 and IPv6 families."""
    assert TCPHandshakeVerifier.validate_ip("192.168.1.1") == IPVersion.IPV4
    assert (
        TCPHandshakeVerifier.validate_ip("2001:0db8:85a3::8a2e:0370:7334")
        == IPVersion.IPV6
    )


def test_tcp_verifier_socket_probe() -> None:
    """Verify TCP handshake probe correctly executes real socket connection check."""
    config = IPGatewayConfig(host="127.0.0.1", port=65530)
    success, latency, message = TCPHandshakeVerifier.probe_socket_handshake(
        config, timeout_sec=0.1
    )

    assert isinstance(success, bool)
    assert latency >= 0.0
    assert isinstance(message, str)


def test_dual_stack_support_probe() -> None:
    """Verify system support probe detects operational socket capabilities."""
    support = TCPHandshakeVerifier.verify_dual_stack_support()
    assert "ipv4" in support
    assert "ipv6" in support
    assert support["ipv4"] is True


def test_evm_opcode_isolation_proof() -> None:
    """Verify EVM architecture isolation proofs enforce no transport opcodes."""
    spec = EVMNetworkArchitectureAnalysis.inspect_evm_opcode_specifications()
    invariant = EVMNetworkArchitectureAnalysis.verify_zero_gas_transport_invariant()
    report = EVMNetworkArchitectureAnalysis.generate_honeypot_dissection_report()

    assert spec["address_space_bits"] == 160
    assert spec["transport_layer_opcodes_present"] is False
    assert spec["tcp_handshake_in_bytecode"] is False
    assert invariant["on_chain_gas_delta"] == 0
    assert invariant["invariant_holds"] is True
    assert "EVM Architectural Defense Report" in report


def test_evm_transaction_validation_errors() -> None:
    """Verify EVMTransaction rejects invalid addresses and negative parameters."""
    with pytest.raises(ValueError, match="Invalid Ethereum sender address"):
        EVMTransaction(
            sender="0xinvalid",
            recipient="0x2222222222222222222222222222222222222222",
        )

    with pytest.raises(ValueError, match="Gas limit cannot be less than standard 21000"):
        EVMTransaction(
            sender="0x1111111111111111111111111111111111111111",
            recipient="0x2222222222222222222222222222222222222222",
            gas_limit=10000,
        )


def test_unregistered_gateway_raises_error() -> None:
    """Verify routing fails with ConnectionError when pool has no active gateways."""
    gateway = DualStackEVMGateway()
    tx = EVMTransaction(
        sender="0x1111111111111111111111111111111111111111",
        recipient="0x2222222222222222222222222222222222222222",
    )
    with pytest.raises(ConnectionError, match="No active EVM gateways available"):
        gateway.route_transaction(tx)


def test_rpc_dispatch_and_metrics_reset() -> None:
    """Verify arbitrary JSON-RPC dispatch and metrics reset functionality."""
    gateway = DualStackEVMGateway()
    gw_v4 = IPGatewayConfig(host="192.168.1.1", port=8545)
    gateway.register_gateway(gw_v4)

    req = RPCRequest(method="net_version")
    response = gateway.dispatch_rpc(req, preferred_version=IPVersion.IPV4)

    assert response.result["method"] == "net_version"
    assert gateway.get_metrics().total_requests == 1

    gateway.reset_metrics()
    assert gateway.get_metrics().total_requests == 0
