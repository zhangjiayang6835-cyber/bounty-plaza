"""Java RMI Deserialization & JEP 290 Class Filter Engine.
Resolves Issue #75: Java RMI Deserialization -> Remote Code Execution Defense ($200).
Enforces JEP 290 ObjectInputFilter pattern matching, class whitelisting,
bind address lockdown (loopback/private only), and RMI SSL enforcement.
"""

import fnmatch
import ipaddress
from typing import Any, Dict, List, Optional, Set, Tuple


class RMISecurityError(Exception):
    """Base exception for RMI configuration and deserialization security violations."""
    pass


class DeserializationFilterRejectedError(RMISecurityError):
    """Raised when an untrusted or blacklisted class is encountered during deserialization."""
    pass


class InsecureBindAddressError(RMISecurityError):
    """Raised when RMI registry attempts to bind to a public or wildcard network interface."""
    pass


class SerialFilterStatus:
    ALLOWED = "ALLOWED"
    REJECTED = "REJECTED"
    UNDECIDED = "UNDECIDED"


# Known gadget classes commonly leveraged in ysoserial payloads
COMMON_GADGET_BLACKLIST: Set[str] = {
    "org.apache.commons.collections.functors.*",
    "org.apache.commons.collections4.functors.*",
    "org.apache.commons.beanutils.*",
    "com.sun.org.apache.xalan.internal.xsltc.trax.TemplatesImpl",
    "javassist.*",
    "org.codehaus.groovy.runtime.*",
    "org.springframework.beans.factory.*",
    "com.mchange.v2.c3p0.*",
    "java.lang.ProcessBuilder",
    "java.lang.Runtime",
}

DEFAULT_SAFE_WHITELIST: Set[str] = {
    "java.lang.String",
    "java.lang.Number",
    "java.lang.Integer",
    "java.lang.Long",
    "java.lang.Boolean",
    "java.lang.Double",
    "java.lang.Float",
    "java.util.ArrayList",
    "java.util.HashMap",
    "java.util.HashSet",
    "java.util.UUID",
    "java.rmi.server.ObjID",
    "java.rmi.server.UID",
    "java.rmi.server.VMID",
    "java.rmi.dgc.Lease",
    "java.rmi.dgc.VMID",
}


class JEP290SerialFilter:
    """Implements Java JEP 290 ObjectInputFilter semantics.
    Supports maxdepth, maxrefs, maxbytes, and class pattern matching (whitelist + blacklist).
    """

    def __init__(
        self,
        allowed_patterns: Optional[Set[str]] = None,
        disallowed_patterns: Optional[Set[str]] = None,
        max_depth: int = 5,
        max_references: int = 100,
        max_stream_bytes: int = 1048576,  # 1MB
    ):
        self.allowed_patterns = set(allowed_patterns or DEFAULT_SAFE_WHITELIST)
        self.disallowed_patterns = set(disallowed_patterns or COMMON_GADGET_BLACKLIST)
        self.max_depth = max_depth
        self.max_references = max_references
        self.max_stream_bytes = max_stream_bytes

    def check_input(
        self,
        class_name: str,
        current_depth: int = 1,
        current_references: int = 1,
        stream_bytes: int = 0,
    ) -> str:
        """Evaluate an incoming class against JEP 290 resource limits and pattern rules.

        Returns:
            SerialFilterStatus.ALLOWED or SerialFilterStatus.REJECTED

        Raises:
            DeserializationFilterRejectedError: If bounds or class filters reject the deserialization.
        """
        # 1. Enforce stream resource limits (anti-DoS)
        if current_depth > self.max_depth:
            raise DeserializationFilterRejectedError(
                f"JEP 290: Depth limit exceeded ({current_depth} > {self.max_depth})"
            )
        if current_references > self.max_references:
            raise DeserializationFilterRejectedError(
                f"JEP 290: Reference limit exceeded ({current_references} > {self.max_references})"
            )
        if stream_bytes > self.max_stream_bytes:
            raise DeserializationFilterRejectedError(
                f"JEP 290: Stream byte limit exceeded ({stream_bytes} > {self.max_stream_bytes})"
            )

        clean_class = class_name.strip()

        # 2. Check blacklist (known gadget chains)
        for pattern in self.disallowed_patterns:
            if fnmatch.fnmatch(clean_class, pattern):
                raise DeserializationFilterRejectedError(
                    f"JEP 290: Class '{clean_class}' rejected by blacklist pattern '{pattern}'"
                )

        # 3. Check whitelist (fail-closed: only explicitly whitelisted classes permitted)
        for pattern in self.allowed_patterns:
            if fnmatch.fnmatch(clean_class, pattern):
                return SerialFilterStatus.ALLOWED

        # Fail-closed default
        raise DeserializationFilterRejectedError(
            f"JEP 290: Class '{clean_class}' not in whitelist (strict fail-closed policy)"
        )


class RMIServerConfig:
    """Manages secure RMI Server configuration: address binding, SSL/TLS, and JEP 290 filter."""

    def __init__(
        self,
        bind_host: str = "127.0.0.1",
        registry_port: int = 1099,
        enable_ssl: bool = True,
        serial_filter: Optional[JEP290SerialFilter] = None,
    ):
        self.bind_host = self.validate_bind_address(bind_host)
        self.registry_port = registry_port
        self.enable_ssl = enable_ssl
        self.serial_filter = serial_filter or JEP290SerialFilter()

        if not self.enable_ssl:
            raise RMISecurityError("RMI without SSL/TLS socket factories is strictly forbidden.")

    @staticmethod
    def validate_bind_address(host: str) -> str:
        """Validate that the RMI server binds exclusively to localhost or private RFC1918 networks."""
        clean_host = (host or "").strip()
        if not clean_host:
            raise InsecureBindAddressError("RMI bind address cannot be empty")

        # Wildcard bind is dangerous as it exposes RMI directly on all public interfaces
        if clean_host in ("0.0.0.0", "::", "*"):
            raise InsecureBindAddressError(
                f"Wildcard bind '{clean_host}' is prohibited: RMI registry must not be exposed to the public Internet."
            )

        try:
            ip = ipaddress.ip_address(clean_host)
            if not (ip.is_loopback or ip.is_private):
                raise InsecureBindAddressError(
                    f"Public IP '{clean_host}' rejected: RMI must bind strictly to loopback or private interface."
                )
        except ValueError:
            # Hostname check
            if clean_host.lower() not in ("localhost", "127.0.0.1", "::1"):
                raise InsecureBindAddressError(
                    f"Unresolved non-local hostname '{clean_host}' rejected for RMI binding."
                )

        return clean_host

    def build_jvm_flags(self) -> List[str]:
        """Generate hardened JVM system properties for RMI runtime."""
        filter_pattern = ";".join(sorted(list(self.serial_filter.allowed_patterns)))
        filter_pattern += ";!" + ";!".join(sorted(list(self.serial_filter.disallowed_patterns)))
        filter_pattern += f";maxdepth={self.serial_filter.max_depth};maxbytes={self.serial_filter.max_stream_bytes}"

        return [
            "-Djava.rmi.server.hostname=" + self.bind_host,
            "-Djdk.serialFilter=" + filter_pattern,
            "-Dcom.sun.management.jmxremote.ssl=true",
            "-Dcom.sun.management.jmxremote.authenticate=true",
            "-Dcom.sun.management.jmxremote.ssl.need.client.auth=true",
        ]
