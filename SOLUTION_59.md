# Solution for Bounty #59 - AWS IAM Privilege Escalation via PassRole + EC2

## Vulnerability

The application uses overly permissive IAM roles that allow privilege escalation through the `iam:PassRole` permission combined with EC2 instance launch. An attacker with `iam:PassRole` can pass a privileged role to a new EC2 instance and gain those privileges.

## Solution

1. Add trust policy constraints on roles
2. Limit PassRole to specific roles
3. Use permission boundaries
4. Implement least-privilege IAM policies

## Files Modified

- `fix_aws_iam.py`: IAM privilege escalation prevention

Closes #59