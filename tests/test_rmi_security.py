import pytest
from scripts.rmi_security import (
    JEP290SerialFilter,
    RMIServerConfig,
    DeserializationFilterRejectedError,
    InsecureBindAddressError,
    RMISecurityError,
    SerialFilterStatus,
)


def test_jep290_allows_whitelisted_classes():
    filter_engine = JEP290SerialFilter()
    assert filter_engine.check_input("java.lang.String") == SerialFilterStatus.ALLOWED
    assert filter_engine.check_input("java.lang.Integer") == SerialFilterStatus.ALLOWED
    assert filter_engine.check_input("java.util.HashMap") == SerialFilterStatus.ALLOWED
    assert filter_engine.check_input("java.rmi.server.UID") == SerialFilterStatus.ALLOWED


def test_jep290_blocks_gadget_blacklist():
    filter_engine = JEP290SerialFilter()

    # ysoserial CommonsCollections gadget payload
    with pytest.raises(DeserializationFilterRejectedError) as excinfo:
        filter_engine.check_input("org.apache.commons.collections.functors.InvokerTransformer")
    assert "rejected by blacklist pattern" in str(excinfo.value)

    # Spring Beans gadget
    with pytest.raises(DeserializationFilterRejectedError):
        filter_engine.check_input("org.springframework.beans.factory.support.DefaultListableBeanFactory")

    # Direct Process execution
    with pytest.raises(DeserializationFilterRejectedError):
        filter_engine.check_input("java.lang.ProcessBuilder")

    with pytest.raises(DeserializationFilterRejectedError):
        filter_engine.check_input("java.lang.Runtime")


def test_jep290_fail_closed_on_unwhitelisted_class():
    filter_engine = JEP290SerialFilter()
    with pytest.raises(DeserializationFilterRejectedError) as excinfo:
        filter_engine.check_input("com.example.vulnerable.CustomPayload")
    assert "strict fail-closed policy" in str(excinfo.value)


def test_jep290_resource_limits():
    filter_engine = JEP290SerialFilter(max_depth=3, max_references=10, max_stream_bytes=1000)

    # Exceeding depth
    with pytest.raises(DeserializationFilterRejectedError) as excinfo:
        filter_engine.check_input("java.lang.String", current_depth=4)
    assert "Depth limit exceeded" in str(excinfo.value)

    # Exceeding references
    with pytest.raises(DeserializationFilterRejectedError) as excinfo:
        filter_engine.check_input("java.lang.String", current_references=11)
    assert "Reference limit exceeded" in str(excinfo.value)

    # Exceeding stream bytes
    with pytest.raises(DeserializationFilterRejectedError) as excinfo:
        filter_engine.check_input("java.lang.String", stream_bytes=2000)
    assert "Stream byte limit exceeded" in str(excinfo.value)


def test_rmi_bind_address_lockdown():
    # Loopback and private IP permitted
    cfg_loopback = RMIServerConfig(bind_host="127.0.0.1")
    assert cfg_loopback.bind_host == "127.0.0.1"

    cfg_private = RMIServerConfig(bind_host="10.0.1.20")
    assert cfg_private.bind_host == "10.0.1.20"

    # Wildcard 0.0.0.0 rejected
    with pytest.raises(InsecureBindAddressError) as excinfo:
        RMIServerConfig(bind_host="0.0.0.0")
    assert "Wildcard bind '0.0.0.0' is prohibited" in str(excinfo.value)

    # Public internet IP rejected
    with pytest.raises(InsecureBindAddressError) as excinfo:
        RMIServerConfig(bind_host="93.184.216.34")
    assert "Public IP" in str(excinfo.value)


def test_rmi_server_flags_and_ssl_enforcement():
    with pytest.raises(RMISecurityError):
        RMIServerConfig(bind_host="127.0.0.1", enable_ssl=False)

    cfg = RMIServerConfig(bind_host="127.0.0.1", enable_ssl=True)
    flags = cfg.build_jvm_flags()

    assert "-Djava.rmi.server.hostname=127.0.0.1" in flags
    assert any("-Djdk.serialFilter=" in f for f in flags)
    assert "-Dcom.sun.management.jmxremote.ssl=true" in flags
