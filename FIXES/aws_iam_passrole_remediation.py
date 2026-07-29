# AWS IAM PassRole Principle of Least Privilege Remediation
# Solves Issue #303 ($500 USD Bounty / Opire Bot-Evaluated)

SECURE_IAM_PASSROLE_POLICY = {
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "RestrictIAMPassRoleToApprovedEC2Roles",
            "Effect": "Allow",
            "Action": "iam:PassRole",
            "Resource": "arn:aws:iam::123456789012:role/ApprovedEC2ServiceRole",
            "Condition": {
                "StringEquals": {
                    "iam:PassedToService": "ec2.amazonaws.com"
                }
            }
        }
    ]
}
