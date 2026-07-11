# fix_aws_iam.py
"""
AWS IAM Privilege Escalation Protection for issue #59.

An attacker with `iam:PassRole` can pass a privileged role to a new
EC2 instance, Lambda function, or other service to gain elevated privileges.

Mitigation: Trust policy constraints, condition keys, and least privilege.
"""


class AWSIAMProtection:
    """Protect against AWS IAM privilege escalation."""

    @staticmethod
    def get_secure_passrole_policy():
        """
        Secure iam:PassRole policy with conditions.

        This limits which roles can be passed to which services.
        """
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": "iam:PassRole",
                    "Resource": "arn:aws:iam::123456789012:role/SpecificRole",
                    "Condition": {
                        "StringEquals": {
                            "iam:PassedToService": [
                                "ec2.amazonaws.com",
                                "lambda.amazonaws.com",
                            ]
                        },
                        "ArnLike": {
                            "aws:PrincipalArn": [
                                "arn:aws:iam::123456789012:role/TrustedCallerRole",
                            ]
                        },
                    },
                },
            ],
        }

    @staticmethod
    def get_trust_policy_with_constraints():
        """
        Trust policy with conditions to prevent privilege escalation.
        Adds conditions that limit what actions can be performed.
        """
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": "ec2.amazonaws.com",
                    },
                    "Action": "sts:AssumeRole",
                    "Condition": {
                        "StringEquals": {
                            "aws:SourceAccount": "123456789012",
                        },
                        "ArnLike": {
                            "aws:SourceArn": [
                                "arn:aws:ec2:us-east-1:123456789012:instance/*",
                            ],
                        },
                    },
                },
            ],
        }

    @staticmethod
    def get_permission_boundary():
        """
        Permission boundary to limit what a role can do.
        Even if a user has admin permissions, the boundary restricts them.
        """
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Deny",
                    "Action": [
                        "iam:CreateUser",
                        "iam:CreateRole",
                        "iam:DeleteUser",
                        "iam:DeleteRole",
                        "iam:AddUserToGroup",
                        "iam:AttachUserPolicy",
                        "iam:AttachRolePolicy",
                        "iam:PassRole",
                        "kms:DeleteKey",
                        "kms:ScheduleKeyDeletion",
                        "s3:PutBucketPolicy",
                        "s3:DeleteBucketPolicy",
                        "s3:PutLifecycleConfiguration",
                    ],
                    "Resource": "*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ec2:*",
                        "lambda:*",
                        "s3:GetObject",
                        "s3:PutObject",
                    ],
                    "Resource": "*",
                },
            ],
        }

    @staticmethod
    def get_ec2_secure_role_policy():
        """Secure IAM role for EC2 with least privilege."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/ec2/*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "ssm:DescribeInstanceInformation",
                        "ssm:ListInstanceAssociations",
                    ],
                    "Resource": "*",
                },
            ],
        }

    @staticmethod
    def check_privilege_escalation_vectors(policy):
        """
        Check an IAM policy for common privilege escalation vectors.
        Returns list of findings.
        """
        findings = []

        # Check for wildcard PassRole
        for stmt in policy.get("Statement", []):
            actions = stmt.get("Action", [])
            resources = stmt.get("Resource", [])
            conditions = stmt.get("Condition", {})

            if isinstance(actions, str):
                actions = [actions]
            if isinstance(resources, str):
                resources = [resources]

            for action in actions:
                # Check for unrestricted PassRole
                if action in ("iam:PassRole", "*") and not conditions:
                    if "*" in resources or action == "*":
                        findings.append({
                            "severity": "critical",
                            "type": "unrestricted_passrole",
                            "description": (
                                "iam:PassRole allows passing any role "
                                "to any service, enabling privilege escalation"
                            ),
                            "fix": "Add Condition with iam:PassedToService "
                                "and limit Resource to specific roles",
                        })

                # Check for wildcard on sensitive actions
                if action in (
                    "iam:*",
                    "organizations:*",
                    "kms:DeleteKey",
                    "kms:ScheduleKeyDeletion",
                    "s3:PutBucketPolicy",
                    "s3:DeleteBucketPolicy",
                    "glue:CreateUserDefinedFunction",
                    "glue:UpdateUserDefinedFunction",
                ):
                    findings.append({
                        "severity": "high",
                        "type": "sensitive_wildcard_action",
                        "description": f"Wildcard on sensitive action: {action}",
                        "fix": "Restrict to specific sub-actions",
                    })

        return findings

    @staticmethod
    def get_lambda_secure_role_policy():
        """Secure IAM role for Lambda with least privilege."""
        return {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Action": [
                        "logs:CreateLogGroup",
                        "logs:CreateLogStream",
                        "logs:PutLogEvents",
                    ],
                    "Resource": "arn:aws:logs:*:*:log-group:/aws/lambda/*",
                },
                {
                    "Effect": "Allow",
                    "Action": [
                        "dynamodb:PutItem",
                        "dynamodb:GetItem",
                        "dynamodb:Query",
                    ],
                    "Resource": "arn:aws:dynamodb:*:*:table/SpecificTable",
                },
            ],
        }

    @staticmethod
    def get_cloudtrail_config():
        """
        CloudTrail configuration to detect privilege escalation attempts.
        """
        return {
            "trail_name": "privilege-escalation-audit",
            "s3_bucket_name": "company-cloudtrail-bucket",
            "include_global_service_events": True,
            "is_multi_region_trail": True,
            "enable_log_file_validation": True,
            "data_events": [
                {
                    "type": "DataEvent",
                    "resources": [
                        {"type": "AWS::S3::Object", "values": ["arn:aws:s3:::bucket/*"]},
                    ],
                },
            ],
        }

    @staticmethod
    def get_guardduty_configuration():
        """
        GuardDuty configuration to detect privilege escalation.
        """
        return {
            "enable": True,
            "features": {
                "RUNCLOUDTRAIL": {"status": "ENABLED"},
                "RUNDNSLOGGING": {"status": "ENABLED"},
                "RUNS3LOGGING": {"status": "ENABLED"},
            },
            "detector_config": {
                "finding_publishing_frequency": "FIFTEEN_MINUTES",
                "data_sources": {
                    "s3_logs": {"enable": True},
                    "kubernetes": {"enable": True},
                },
            },
        }