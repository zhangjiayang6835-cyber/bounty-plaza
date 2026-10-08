import os
import re

class BountyValidator:
    def __init__(self, directory):
        self.directory = directory
        self.required_headers = [
            "Overview", "Reward & Payment", "Objective", 
            "Technical Specification", "Required Deliverables", 
            "Evaluation Criteria", "Recursive Expansion"
        ]

    def check_structural_fidelity(self, content):
        score = 0
        for header in self.required_headers:
            if re.search(rf"#+.*{header}", content, re.IGNORECASE):
                score += 1
        return (score / len(self.required_headers)) * 100

    def validate_all(self):
        print("--- Starting DAXDA Bounty Validation Protocol ---")
        files = [f for f in os.listdir(self.directory) if f.endswith('.md')]
        if not files:
            print("Error: No bounty files found.")
            return

        for file in files:
            path = os.path.join(self.directory, file)
            with open(path, 'r') as f:
                content = f.read()
                fidelity = self.check_structural_fidelity(content)
                print(f"File: {file} | Structural Fidelity: {fidelity:.2f}%")
                
                if fidelity < 95:
                    print(f"  [!] WARNING: Low fidelity in {file}")
                else:
                    print(f"  [+] PASS: High fidelity detected.")

if __name__ == "__main__":
    validator = BountyValidator("bounties")
    validator.validate_all()
