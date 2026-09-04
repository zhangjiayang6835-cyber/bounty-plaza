import pytest
from scripts.grpc_security import (
    GRPCSecurityInterceptor,
    GRPCSecurityError,
    GRPCStatus,
)


def test_grpc_reflection_disabled_in_production():
    interceptor = GRPCSecurityInterceptor(environment="production", require_mtls=False)

    with pytest.raises(GRPCSecurityError) as excinfo:
        interceptor.intercept_call(
            service_name="grpc.reflection.v1alpha.ServerReflection",
            method_name="ServerReflectionInfo",
            metadata={},
        )
    assert excinfo.value.code == GRPCStatus.UNIMPLEMENTED
    assert "strictly disabled in production" in excinfo.value.message


def test_grpc_reflection_allowed_in_dev():
    interceptor = GRPCSecurityInterceptor(environment="development", require_mtls=False)
    code, msg = interceptor.intercept_call(
        service_name="grpc.reflection.v1alpha.ServerReflection",
        method_name="ServerReflectionInfo",
        metadata={},
    )
    assert code == GRPCStatus.OK
    assert msg == "Authorized"


def test_grpc_mtls_enforcement():
    interceptor = GRPCSecurityInterceptor(
        environment="production",
        require_mtls=True,
        allowed_client_common_names=["payment-service", "order-service"],
    )

    # Missing client cert
    with pytest.raises(GRPCSecurityError) as excinfo:
        interceptor.intercept_call("bounty.OrderService", "GetOrder", metadata={})
    assert excinfo.value.code == GRPCStatus.UNAUTHENTICATED
    assert "mTLS" in excinfo.value.message

    # Unauthorized CN
    with pytest.raises(GRPCSecurityError) as excinfo:
        interceptor.intercept_call(
            "bounty.OrderService",
            "GetOrder",
            metadata={},
            client_cert_info={"verified": True, "cn": "attacker-service"},
        )
    assert excinfo.value.code == GRPCStatus.PERMISSION_DENIED
    assert "attacker-service" in excinfo.value.message

    # Valid CN
    code, msg = interceptor.intercept_call(
        "bounty.OrderService",
        "GetOrder",
        metadata={},
        client_cert_info={"verified": True, "cn": "payment-service"},
    )
    assert code == GRPCStatus.OK


def test_grpc_service_token_authentication():
    interceptor = GRPCSecurityInterceptor(
        environment="production",
        require_mtls=False,
        allowed_service_tokens={"audit-worker": "super_secret_token_123"},
    )

    # Missing token
    with pytest.raises(GRPCSecurityError) as excinfo:
        interceptor.intercept_call("bounty.AuditService", "RecordAudit", metadata={})
    assert excinfo.value.code == GRPCStatus.UNAUTHENTICATED

    # Invalid token
    with pytest.raises(GRPCSecurityError) as excinfo:
        interceptor.intercept_call(
            "bounty.AuditService",
            "RecordAudit",
            metadata={"authorization": "Bearer wrong_token"},
        )
    assert excinfo.value.code == GRPCStatus.PERMISSION_DENIED

    # Valid Bearer token
    code, msg = interceptor.intercept_call(
        "bounty.AuditService",
        "RecordAudit",
        metadata={"authorization": "Bearer super_secret_token_123"},
    )
    assert code == GRPCStatus.OK

    # Valid X-Service-Token header
    code, msg = interceptor.intercept_call(
        "bounty.AuditService",
        "RecordAudit",
        metadata={"x-service-token": "super_secret_token_123"},
    )
    assert code == GRPCStatus.OK
