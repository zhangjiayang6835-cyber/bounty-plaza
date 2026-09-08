"""TCP Handshake and transport layer verifier for dual-stack EVM gateways."""

import ipaddress
import socket
import time
from .models import IPGatewayConfig, IPVersion


class TCPHandshakeVerifier:
    """Performs deterministic TCP connection probes and IP stack verification."""

    @staticmethod
    def validate_ip(host: str) -> IPVersion:
        """Validate whether the provided host conforms to IPv4 or IPv6 standards."""
        ip_obj = ipaddress.ip_address(host)
        if isinstance(ip_obj, ipaddress.IPv6Address):
            return IPVersion.IPV6
        return IPVersion.IPV4

    @staticmethod
    def probe_socket_handshake(
        config: IPGatewayConfig,
        timeout_sec: float = 0.5
    ) -> tuple[bool, float, str]:
        """Verify TCP handshake against configured gateway with precise latency timing."""
        address_family = (
            socket.AF_INET6 if config.version == IPVersion.IPV6 else socket.AF_INET
        )
        start_time = time.perf_counter()
        sock = socket.socket(address_family, socket.SOCK_STREAM)
        sock.settimeout(timeout_sec)

        try:
            sock.connect((config.host, config.port))
            latency = (time.perf_counter() - start_time) * 1000.0
            sock.close()
            return True, latency, "Handshake successful"
        except (socket.timeout, ConnectionRefusedError, OSError) as exc:
            latency = (time.perf_counter() - start_time) * 1000.0
            sock.close()
            return False, latency, f"Handshake refused or unreachable: {exc}"

    @staticmethod
    def verify_dual_stack_support() -> dict[str, bool]:
        """Check operating system support for both IPv4 and IPv6 network families."""
        results = {"ipv4": False, "ipv6": False}

        try:
            sock_v4 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock_v4.close()
            results["ipv4"] = True
        except OSError:
            results["ipv4"] = False

        try:
            sock_v6 = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
            sock_v6.close()
            results["ipv6"] = True
        except OSError:
            results["ipv6"] = False

        return results
