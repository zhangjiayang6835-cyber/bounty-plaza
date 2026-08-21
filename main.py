import os
import json

def generate_runbook():
    runbook = {
        "schema_version": "agent-bounties/agent-earning-runbook-v1",
        "task_id": "agent-earning-runbook-v1",
        "steps": [
            {
                "id": "inspect_profiles",
                "operation": "profiles",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "list_active",
                "operation": "inventory",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "build_artifact",
                "operation": "prepare_profile",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "quote_proof",
                "operation": "quote_proof",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "pay_challenge",
                "operation": "pay",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "sign_relay",
                "operation": "sign_relay",
                "success_state": "",
                "fallback": ""
            },
            {
                "id": "confirm_settled",
                "operation": "confirm",
                "success_state": "CompetitionSettledV2",
                "fallback": ""
            }
        ]
    }
    
    os.makedirs("output", exist_ok=True)
    with open("output/runbook.json", "w", encoding="utf-8") as f:
        json.dump(runbook, f, indent=2)

if __name__ == "__main__":
    generate_runbook()