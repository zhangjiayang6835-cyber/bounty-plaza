```python
import json

def get_shortest_runbook():
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
            }
        ]
    }
    return json.dumps(runbook, separators=(',', ':'))

if __name__ == "__main__":
    print(get_shortest_runbook())
```