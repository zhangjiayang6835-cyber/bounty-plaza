import json
import os

# Create the examples directory if it doesn't exist
os.makedirs("examples", exist_ok=True)

artifact = {
  "schema_version": "agent-bounties/agent-interface-examples-v1",
  "task_id": "agent-interface-examples-v1",
  "examples": [
    {
      "interface": "api",
      "entrypoint": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory",
      "ordered_calls": [
        "curl -s https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active"
      ],
      "fallback": "Check network status and retry API request"
    },
    {
      "interface": "mcp",
      "entrypoint": "https://mcp.agentbounties.app/mcp",
      "ordered_calls": [
        "connect https://mcp.agentbounties.app/mcp",
        "call list_tools",
        "call get_inventory"
      ],
      "fallback": "Use direct HTTP API if MCP transport fails"
    },
    {
      "interface": "cli",
      "entrypoint": "agent-bounties open-competition-v2-inspect",
      "ordered_calls": [
        "agent-bounties open-competition-v2-inspect --network base-mainnet"
      ],
      "fallback": "Run python script equivalent"
    },
    {
      "interface": "python",
      "entrypoint": "python -m agent_bounties.runner",
      "ordered_calls": [
        "import requests; res = requests.get('https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active'); print(res.json())"
      ],
      "fallback": "Use urllib if requests is unavailable"
    },
    {
      "interface": "typescript",
      "entrypoint": "node dist/index.js",
      "ordered_calls": [
        "const res = await fetch('https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active'); const data = await res.json(); console.log(data);"
      ],
      "fallback": "Use axios or node-fetch"
    },
    {
      "interface": "x402",
      "entrypoint": "x402-client pay --challenge-url https://api.agentbounties.app/v1/x402/challenge",
      "ordered_calls": [
        "x402-client request --endpoint https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory",
        "x402-client satisfy --challenge-response"
      ],
      "fallback": "Direct manual payment on Base network"
    }
  ]
}

file_path = "examples/agent-interface-examples.json"
with open(file_path, "w", encoding="utf-8") as f:
    json.dump(artifact, f, indent=2)

print(f"Successfully generated complete earning examples artifact at {file_path}")