<content>
#!/usr/bin/env python3
"""
Script to validate IAM policies for PassRole security best practices.
"""

import json
import sys
import argparse
from typing import Dict, List, Any

class IAMPolicyValidator:
    def __init__(self):
        self.violations = []
    
    def validate_policy(self, policy: Dict[str, Any], policy_name: str = "Unknown") -> bool:
        """Validate an IAM policy for PassRole security issues."""
        is_valid = True
        
        if "Statement" not in policy:
            self.violations.append(f"Policy {policy_name}: Missing 'Statement' field")
            return False
        
        for statement in policy["Statement"]:
            if self._is_passrole_statement(statement):
                is_valid = self._validate_passrole_statement(statement, policy_name) and is_valid
                
                # Check if this statement allows EC2:RunInstances
                if self._allows_ec2_run_instances(statement):
                    self.violations.append(
                        f"Policy {policy_name}: Statement allows both PassRole and EC2:RunInstances - potential privilege escalation"
                    )
                    is_valid = False
        
        return is_valid
    
    def _is_passrole_statement(self, statement: Dict[str, Any]) -> bool:
        """Check if a statement is a PassRole statement."""
        return (
            statement.get("Action") == "iam:PassRole" or
            (isinstance(statement.get("Action"), list) and "iam:PassRole" in statement.get("Action", []))
        )
    
    def _allows_ec2_run_instances(self, statement: Dict[str, Any]) -> bool:
        """Check if a statement allows EC2:RunInstances."""
        return (
            statement.get("Action") == "ec2:RunInstances" or
            (isinstance(statement.get("Action"), list) and "ec2:RunInstances" in statement.get("Action", []))
        )
    
    def _validate_passrole_statement(self, statement: Dict[str, Any], policy_name: str) -> bool:
        """Validate a PassRole statement for security best practices."""
        is_valid = True
        
        # Check for wildcard resource
        resource = statement.get("Resource")
        if resource == "*" or (isinstance(resource, list) and "*" in resource):
            self.violations.append(
                f"Policy {policy_name}: PassRole statement uses wildcard resource - restrict to specific roles"
            )
            is_valid = False
        
        # Check for conditions
        if "Condition" not in statement:
            self.violations.append(
                f"Policy {policy_name}: PassRole statement missing conditions - add service and ARN restrictions"
            )
            is_valid = False
        else:
            # Check for iam:PassedToService condition
            if "iam:PassedToService" not in statement.get("Condition", {}):
                self.violations.append(
                    f"Policy {policy_name}: PassRole statement missing iam:PassedToService condition"
                )
                is_valid = False
            
            # Check for aws:SourceArn condition
            if "aws:SourceArn" not in statement.get("Condition", {}):
                self.violations.append(
                    f"Policy {policy_name}: PassRole statement missing aws:SourceArn condition"
                )
                is_valid = False
        
        return is_valid
    
    def get_violations(self) -> List[str]:
        """Get all validation violations."""
        return self.violations
    
    def clear_violations(self):
        """Clear all validation violations."""
        self.violations = []


def load_policy(file_path: str) -> Dict[str, Any]:
    """Load an IAM policy from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading policy from {file_path}: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Validate IAM policies for PassRole security")
    parser.add_argument("policy_file", help="Path to the IAM policy JSON file")
    parser.add_argument("--policy-name", default="Unknown", help="Name of the policy for reporting")
    
    args = parser.parse_args()
    
    validator = IAMPolicyValidator()
    policy = load_policy(args.policy_file)
    
    is_valid = validator.validate_policy(policy, args.policy_name)
    
    if not is_valid:
        print(f"Policy validation failed for {args.policy_name}:")
        for violation in validator.get_violations():
            print(f"  - {violation}")
        sys.exit(1)
    else:
        print(f"Policy {args.policy_name} passed validation")
        sys.exit(0)


if __name__ == "__main__":
    main()
</content>