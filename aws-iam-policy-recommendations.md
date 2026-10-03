<content>
# AWS IAM Policy Recommendations for PassRole Security

## Overview

This document provides recommendations for securing AWS IAM policies to prevent privilege escalation through the `iam:PassRole` permission.

## Problem

When an entity has both `iam:PassRole` and `ec2:RunInstances` permissions, it can launch an EC2 instance with a highly privileged role attached, then use user-data scripts to obtain temporary credentials, effectively escalating privileges.

## Recommended Solution

### 1. Implement Least Privilege for PassRole

Instead of granting broad `iam:PassRole` permissions, restrict it to specific roles that are absolutely necessary:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::ACCOUNT_ID:role/SpecificRoleName"
        }
    ]
}
```

### 2. Use Condition Keys for Additional Security

Add conditions to further restrict when PassRole can be used:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::ACCOUNT_ID:role/SpecificRoleName",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "ec2.amazonaws.com"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:ec2:REGION:ACCOUNT_ID:instance/*"
                }
            }
        }
    ]
}
```

### 3. Protect Sensitive Roles

For roles with highly sensitive permissions:

1. Deny all attempts to pass the role unless explicitly allowed:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Deny",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::ACCOUNT_ID:role/SensitiveRole",
            "Condition": {
                "Bool": {
                    "aws:PrincipalTag/RestrictPassRole": "false"
                }
            }
        }
    ]
}
```

2. Use MFA requirements for sensitive operations:
```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::ACCOUNT_ID:role/SensitiveRole",
            "Condition": {
                "Bool": {
                    "aws:MultiFactorAuthPresent": "true"
                }
            }
        }
    ]
}
```

### 4. Remove Wildcard Resources

Avoid using wildcards (`*`) in the Resource field. Instead, specify exact ARNs:

```json
// Bad
{
    "Effect": "Allow",
    "Action": "iam:PassRole",
    "Resource": "*"
}

// Good
{
    "Effect": "Allow",
    "Action": "iam:PassRole",
    "Resource": [
        "arn:aws:iam::ACCOUNT_ID:role/SpecificRole1",
        "arn:aws:iam::ACCOUNT_ID:role/SpecificRole2"
    ]
}
```

## Example Secure Policy for EC2 Launch with PassRole

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": "ec2:RunInstances",
            "Resource": [
                "arn:aws:ec2:REGION::image/AMI_ID",
                "arn:aws:ec2:REGION:ACCOUNT_ID:security-group/SecurityGroupID",
                "arn:aws:ec2:REGION:ACCOUNT_ID:subnet/SubnetID",
                "arn:aws:ec2:REGION:ACCOUNT_ID:volume/VolumeID"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::ACCOUNT_ID:role/EC2LimitedRole",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "ec2.amazonaws.com"
                },
                "ArnLike": {
                    "aws:SourceArn": "arn:aws:ec2:REGION:ACCOUNT_ID:instance/*"
                }
            }
        }
    ]
}
```

## Best Practices

1. **Regularly review IAM policies** for least privilege compliance
2. **Use IAM Access Analyzer** to identify policy risks
3. **Implement service control policies** in AWS Organizations for additional constraints
4. **Enable IAM credential reports** to monitor permissions
5. **Use IAM roles instead of long-term credentials** whenever possible
6. **Rotate credentials** regularly for sensitive accounts
</content>