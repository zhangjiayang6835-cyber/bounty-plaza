"""Self-verification and operational check script for Issue #1214."""

import sys
from packages.evm_network_gateway import (
    DualStackEVMGateway,
    EVMNetworkArchitectureAnalysis,
    EVMTransaction,
    IPGatewayConfig,
    IPVersion,
    TCPHandshakeVerifier,
)


def verify_issue_1214_implementation() -> int:
    """Execute end-to-end operational verification of dual-stack gateway."""
    gateway = DualStackEVMGateway()

    gw_v4 = IPGatewayConfig(host="192.168.1.1", port=8545)
    gw_v6 = IPGatewayConfig(host="2001:0db8:85a3::8a2e:0370:7334", port=8545)

    gateway.register_gateway(gw_v4)
    gateway.register_gateway(gw_v6)

    tx = EVMTransaction(
        sender="0x1111111111111111111111111111111111111111",
        recipient="0x2222222222222222222222222222222222222222",
        value_wei=500_000_000_000_000_000,
        gas_limit=21000,
        gas_price_wei=2_000_000_000,
        nonce=1,
    )

    response_v6 = gateway.route_transaction(tx, preferred_version=IPVersion.IPV6)
    response_v4 = gateway.route_transaction(tx, preferred_version=IPVersion.IPV4)
    metrics = gateway.get_metrics()
    support = TCPHandshakeVerifier.verify_dual_stack_support()
    analysis = EVMNetworkArchitectureAnalysis.verify_zero_gas_transport_invariant()

    valid = True
    if response_v6.on_chain_gas_consumed != 0 or response_v6.ip_version != IPVersion.IPV6:
        valid = False
    if response_v4.on_chain_gas_consumed != 0 or response_v4.ip_version != IPVersion.IPV4:
        valid = False
    if metrics.total_requests != 2 or metrics.on_chain_gas_incurred != 0:
        valid = False
    if not support.get("ipv4") or not analysis.get("invariant_holds"):
        valid = False

    return 0 if valid else 1


def main() -> int:
    """Main entry point for command-line verification."""
    return verify_issue_1214_implementation()


if __name__ == "__main__":
    sys.exit(main())
