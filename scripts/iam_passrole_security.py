"""AWS IAM Least Privilege & PassRole Escalation Defense Engine.
Resolves Issue #303: AWS IAM Privilege Escalation via PassRole + EC2 ($150 USD).

Implements:
1. Least-privilege IAM policy validation eliminating wildcard Resource ("*") on iam:PassRole.
2. Explicit Role ARN whitelisting and strict protection of administrative/privileged roles.
3. Strict condition key verification:
   - iam:PassedToService ("ec2.amazonaws.com")
   - aws:SourceArn / StringEquals constraints
4. Pre-execution evaluation blocking unauthorized role delegation and EC2 instance profile attachment.
"""

import fnmatch
import re
from typing import Any, Dict, List, Optional, Set


class IAMSecurityError(ValueError):
    """Base exception for IAM security violations."""
    pass


class PrivilegeEscalationError(IAMSecurityError):
    """Raised when an action attempts unauthorized role delegation or privilege escalation."""
    pass


class MalformedPolicyError(IAMSecurityError):
    """Raised when an IAM policy statement is invalid or insecure."""
    pass


# High-privilege role patterns that must NEVER be pass-able by non-admin principals
PROTECTED_ROLE_PATTERNS = [
    "*admin*",
    "*root*",
    "*organizationaccountaccessrole*",
    "*securityaudit*",
    "*fullaccess*",
    "*superuser*",
]


class IAMPolicyValidator:
    """Validates IAM policy definitions to prevent overly permissive PassRole grants."""

    @staticmethod
    def validate_statement(statement: Dict[str, Any]) -> None:
        """Audits policy statement for dangerous PassRole permissions.

        Raises:
            PrivilegeEscalationError: If PassRole uses wildcard resource or lacks service condition.
        """
        effect = statement.get("Effect", "Deny")
        if effect != "Allow":
            return

        actions = statement.get("Action", [])
        if isinstance(actions, str):
            actions = [actions]

        has_pass_role = any(
            a.lower() in ("iam:passrole", "iam:*", "*")
            for a in actions
        )
        if not has_pass_role:
            return

        # 1. Block wildcard Resource on iam:PassRole
        resources = statement.get("Resource", [])
        if isinstance(resources, str):
            resources = [resources]

        for res in resources:
            if res.strip() == "*":
                raise PrivilegeEscalationError(
                    "Dangerous IAM Policy: 'iam:PassRole' granted with wildcard Resource '*'. "
                    "Must be restricted to explicit Role ARNs."
                )

        # 2. Enforce iam:PassedToService condition
        condition = statement.get("Condition", {})
        string_equals = condition.get("StringEquals", {})
        passed_to = (
            string_equals.get("iam:PassedToService")
            or string_equals.get("iam:passedtoservice")
        )

        if not passed_to:
            raise PrivilegeEscalationError(
                "Missing condition: 'iam:PassRole' must enforce 'iam:PassedToService' condition key."
            )


class SecurePassRoleAuthorizer:
    """Enforces runtime authorization for iam:PassRole and ec2:RunInstances operations."""

    def __init__(
        self,
        allowed_role_arns: Set[str],
        allowed_target_services: Optional[Set[str]] = None,
        source_arn_whitelist: Optional[Set[str]] = None,
    ):
        self.allowed_role_arns = set(allowed_role_arns)
        self.allowed_target_services = allowed_target_services or {"ec2.amazonaws.com"}
        self.source_arn_whitelist = source_arn_whitelist or set()

    def is_role_protected(self, role_arn: str) -> bool:
        """Determines if the target role has administrative or privileged keywords."""
        role_lower = role_arn.lower()
        for pattern in PROTECTED_ROLE_PATTERNS:
            if fnmatch.fnmatch(role_lower, pattern):
                return True
        return False

    def authorize_pass_role(
        self,
        principal_arn: str,
        target_role_arn: str,
        target_service: str,
        source_arn: Optional[str] = None,
    ) -> bool:
        """Evaluates whether principal is permitted to pass target_role_arn to target_service.

        Args:
            principal_arn: The IAM caller invoking ec2:RunInstances or iam:PassRole.
            target_role_arn: The ARN of the IAM role being attached to the instance profile.
            target_service: The AWS service receiving the role (e.g. 'ec2.amazonaws.com').
            source_arn: The originating ARN (e.g. EC2 launch template or pipeline ARN).

        Returns:
            True if authorized.

        Raises:
            PrivilegeEscalationError: If authorization fails.
        """
        if not target_role_arn or not isinstance(target_role_arn, str):
            raise PrivilegeEscalationError("Invalid target role ARN")

        # 1. Prohibit passing protected / administrative roles
        if self.is_role_protected(target_role_arn):
            raise PrivilegeEscalationError(
                f"Privilege escalation blocked: Role '{target_role_arn}' is a protected administrative role "
                "and cannot be delegated via PassRole."
            )

        # 2. Check Service Restriction (iam:PassedToService)
        if target_service.lower() not in [s.lower() for s in self.allowed_target_services]:
            raise PrivilegeEscalationError(
                f"Unauthorized service delegation: Role '{target_role_arn}' cannot be passed to '{target_service}'. "
                f"Allowed services: {self.allowed_target_services}"
            )

        # 3. Check Explicit Role Whitelist (No wildcard matching)
        if target_role_arn not in self.allowed_role_arns:
            raise PrivilegeEscalationError(
                f"PassRole unauthorized: Role '{target_role_arn}' is not present in authorized role whitelist."
            )

        # 4. Check aws:SourceArn Condition if configured
        if self.source_arn_whitelist and source_arn:
            if source_arn not in self.source_arn_whitelist:
                raise PrivilegeEscalationError(
                    f"PassRole rejected by aws:SourceArn constraint: Source '{source_arn}' is not authorized."
                )

        return True

    def build_secure_policy(self, statement_id: str, role_arns: List[str], target_service: str = "ec2.amazonaws.com") -> Dict[str, Any]:
        """Constructs a compliant, least-privilege IAM policy document for PassRole."""
        for arn in role_arns:
            if self.is_role_protected(arn):
                raise PrivilegeEscalationError(f"Cannot include protected role '{arn}' in policy document")

        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Sid": statement_id,
                    "Effect": "Allow",
                    "Action": "iam:PassRole",
                    "Resource": list(role_arns),
                    "Condition": {
                        "StringEquals": {
                            "iam:PassedToService": target_service
                        }
                    }
                }
            ]
        }
