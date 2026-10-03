<content>
#!/usr/bin/env python3
"""
Script to fix IAM policies for PassRole security issues.
"""

import json
import sys
import argparse
from typing import Dict, List, Any


class IAMPolicyFixer:
    def __init__(self):
        self.changes = []
    
    def fix_policy(self, policy: Dict[str, Any], policy_name: str = "Unknown") -> Dict[str, Any]:
        """Fix an IAM policy for PassRole security issues."""
        fixed_policy = policy.copy()
        
        if "Statement" not in fixed_policy:
            fixed_policy["Statement"] = []
        
        new_statements = []
        
        for statement in fixed_policy["Statement"]:
            if self._is_passrole_statement(statement):
                # Fix the PassRole statement
                fixed_statement = self._fix_passrole_statement(statement, policy_name)
                new_statements.append(fixed_statement)
                
                # Check if this statement also allows EC2:RunInstances
                if self._allows_ec2_run_instances(statement):
                    # Split into separate statements
                    ec2_statement = self._split_ec2_statement(statement)
                    new_statements.append(ec2_statement)
            else:
                new_statements.append(statement)
        
        fixed_policy["Statement"] = new_statements
        return fixed_policy
    
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
    
    def _fix_passrole_statement(self, statement: Dict[str, Any], policy_name: str) -> Dict[str, Any]:
        """Fix a PassRole statement for security best practices."""
        fixed_statement = statement.copy()
        
        # Fix resource if it's a wildcard
        resource = fixed_statement.get("Resource")
        if resource == "*":
            # In a real scenario, you would replace this with specific role ARNs
            fixed_statement["Resource"] = "arn:aws:iam::{{ACCOUNT_ID}}:role/{{ROLE_NAME}}"
            self.changes.append(f"Policy {policy_name}: Replaced wildcard resource with specific role ARN")
        
        # Add conditions if missing
        if "Condition" not in fixed_statement:
            fixed_statement["Condition"] = {}
            self.changes.append(f"Policy {policy_name}: Added conditions to PassRole statement")
        
        # Add iam:PassedToService condition if missing
        if "iam:PassedToService" not in fixed_statement.get("Condition", {}):
            fixed_statement["Condition"]["iam:PassedToService"] = "ec2.amazonaws.com"
            self.changes.append(f"Policy {policy_name}: Added iam:PassedToService condition")
        
        # Add aws:SourceArn condition if missing
        if "aws:SourceArn" not in fixed_statement.get("Condition", {}):
            fixed_statement["Condition"]["aws:SourceArn"] = "arn:aws:ec2:{{REGION}}:{{ACCOUNT_ID}}:instance/*"
            self.changes.append(f"Policy {policy_name}: Added aws:SourceArn condition")
        
        return fixed_statement
    
    def _split_ec2_statement(self, statement: Dict[str, Any]) -> Dict[str, Any]:
        """Split EC2:RunInstances into a separate statement."""
        # Create a new statement with only EC2 actions
        ec2_statement = {
            "Effect": statement.get("Effect", "Allow"),
            "Action": ["ec2:RunInstances", "ec2:DescribeInstances"],
            "Resource": statement.get("Resource", "*")
        }
        
        # Add conditions if they exist and are relevant to EC2
        if "Condition" in statement:
            # Only keep conditions that make sense for EC2
            relevant_conditions = {}
            for key, value in statement["Condition"].items():
                if key.startswith("aws:") or key == "ec2:InstanceProfileType":
                    relevant_conditions[key] = value
            
            if relevant_conditions:
                ec2_statement["Condition"] = relevant_conditions
        
        return ec2_statement
    
    def get_changes(self) -> List[str]:
        """Get all changes made to the policy."""
        return self.changes
    
    def clear_changes(self):
        """Clear all changes."""
        self.changes = []


def load_policy(file_path: str) -> Dict[str, Any]:
    """Load an IAM policy from a JSON file."""
    try:
        with open(file_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading policy from {file_path}: {str(e)}")
        sys.exit(1)


def save_policy(policy: Dict[str, Any], file_path: str):
    """Save an IAM policy to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(policy, f, indent=2)
    except Exception as e:
        print(f"Error saving policy to {file_path}: {str(e)}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Fix IAM policies for PassRole security")
    parser.add_argument("input_file", help="Path to the input IAM policy JSON file")
    parser.add_argument("output_file", help="Path to save the fixed IAM policy JSON file")
    parser.add_argument("--policy-name", default="Unknown", help="Name of the policy for reporting")
    
    args = parser.parse_args()
    
    fixer = IAMPolicyFixer()
    policy = load_policy(args.input_file)
    
    fixed_policy = fixer.fix_policy(policy, args.policy_name)
    
    if fixer.get_changes():
        print(f"Fixed policy {args.policy_name}:")
        for change in fixer.get_changes():
            print(f"  - {change}")
        save_policy(fixed_policy, args.output_file)
        print(f"Fixed policy saved to {args.output_file}")
    else:
        print(f"No changes needed for policy {args.policy_name}")


if __name__ == "__main__":
    main()
</content>