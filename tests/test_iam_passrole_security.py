"""Unit and security test suite for AWS IAM PassRole Escalation Defense.
Resolves Issue #303: AWS IAM Privilege Escalation via PassRole + EC2 ($150 USD).
"""

import pytest
from scripts.iam_passrole_security import (
    IAMPolicyValidator,
    SecurePassRoleAuthorizer,
    PrivilegeEscalationError,
)


@pytest.fixture
def authorizer():
    allowed_roles = {
        "arn:aws:iam::123456789012:role/web-app-readonly-worker",
        "arn:aws:iam::123456789012:role/data-processing-agent",
    }
    source_arns = {
        "arn:aws:ec2:us-east-1:123456789012:instance/i-0abcdef1234567890",
        "arn:aws:ec2:us-east-1:123456789012:launch-template/lt-0987654321fedcba",
    }
    return SecurePassRoleAuthorizer(
        allowed_role_arns=allowed_roles,
        allowed_target_services={"ec2.amazonaws.com"},
        source_arn_whitelist=source_arns,
    )


def test_validator_blocks_wildcard_resource_passrole():
    """Validates that IAM policies with Resource: '*' on iam:PassRole fail audit."""
    dangerous_statement = {
        "Effect": "Allow",
        "Action": ["iam:PassRole"],
        "Resource": "*",
        "Condition": {
            "StringEquals": {
                "iam:PassedToService": "ec2.amazonaws.com"
            }
        }
    }
    with pytest.raises(PrivilegeEscalationError, match=r"wildcard Resource '\*'"):
        IAMPolicyValidator.validate_statement(dangerous_statement)


def test_validator_blocks_missing_passed_to_service_condition():
    """Validates that iam:PassRole without iam:PassedToService is blocked."""
    statement_missing_condition = {
        "Effect": "Allow",
        "Action": "iam:PassRole",
        "Resource": "arn:aws:iam::123456789012:role/web-worker",
    }
    with pytest.raises(PrivilegeEscalationError, match="must enforce 'iam:PassedToService'"):
        IAMPolicyValidator.validate_statement(statement_missing_condition)


def test_validator_accepts_compliant_statement():
    compliant_statement = {
        "Effect": "Allow",
        "Action": "iam:PassRole",
        "Resource": ["arn:aws:iam::123456789012:role/web-worker"],
        "Condition": {
            "StringEquals": {
                "iam:PassedToService": "ec2.amazonaws.com"
            }
        }
    }
    # Should not raise
    IAMPolicyValidator.validate_statement(compliant_statement)


def test_authorize_pass_role_success(authorizer):
    role_arn = "arn:aws:iam::123456789012:role/web-app-readonly-worker"
    source = "arn:aws:ec2:us-east-1:123456789012:launch-template/lt-0987654321fedcba"

    res = authorizer.authorize_pass_role(
        principal_arn="arn:aws:iam::123456789012:user/developer_bob",
        target_role_arn=role_arn,
        target_service="ec2.amazonaws.com",
        source_arn=source,
    )
    assert res is True


def test_authorize_blocks_admin_privilege_escalation(authorizer):
    """Principal tries to pass an Administrator or OrganizationAccess role."""
    admin_roles = [
        "arn:aws:iam::123456789012:role/AdministratorAccess",
        "arn:aws:iam::123456789012:role/FullAccessCloudAdmin",
        "arn:aws:iam::123456789012:role/OrganizationAccountAccessRole",
        "arn:aws:iam::123456789012:role/RootAccountEmergencyRole",
    ]

    for role in admin_roles:
        with pytest.raises(PrivilegeEscalationError, match="protected administrative role"):
            authorizer.authorize_pass_role(
                principal_arn="arn:aws:iam::123456789012:user/developer_bob",
                target_role_arn=role,
                target_service="ec2.amazonaws.com",
            )


def test_authorize_blocks_unwhitelisted_role(authorizer):
    with pytest.raises(PrivilegeEscalationError, match="not present in authorized role whitelist"):
        authorizer.authorize_pass_role(
            principal_arn="arn:aws:iam::123456789012:user/developer_bob",
            target_role_arn="arn:aws:iam::123456789012:role/unauthorized-internal-role",
            target_service="ec2.amazonaws.com",
        )


def test_authorize_blocks_unauthorized_target_service(authorizer):
    with pytest.raises(PrivilegeEscalationError, match="Unauthorized service delegation"):
        authorizer.authorize_pass_role(
            principal_arn="arn:aws:iam::123456789012:user/developer_bob",
            target_role_arn="arn:aws:iam::123456789012:role/web-app-readonly-worker",
            target_service="lambda.amazonaws.com",
        )


def test_authorize_blocks_unauthorized_source_arn(authorizer):
    role_arn = "arn:aws:iam::123456789012:role/web-app-readonly-worker"
    unauthorized_source = "arn:aws:ec2:us-west-2:999999999999:instance/i-rogue"

    with pytest.raises(PrivilegeEscalationError, match="aws:SourceArn constraint"):
        authorizer.authorize_pass_role(
            principal_arn="arn:aws:iam::123456789012:user/developer_bob",
            target_role_arn=role_arn,
            target_service="ec2.amazonaws.com",
            source_arn=unauthorized_source,
        )


def test_build_secure_policy(authorizer):
    doc = authorizer.build_secure_policy(
        statement_id="AllowEC2PassRoleSafe",
        role_arns=["arn:aws:iam::123456789012:role/web-app-readonly-worker"],
        target_service="ec2.amazonaws.com",
    )
    stmt = doc["Statement"][0]
    assert stmt["Action"] == "iam:PassRole"
    assert stmt["Resource"] == ["arn:aws:iam::123456789012:role/web-app-readonly-worker"]
    assert stmt["Condition"]["StringEquals"]["iam:PassedToService"] == "ec2.amazonaws.com"
