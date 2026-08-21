import json

data = {
    "schema_version": "agent-bounties/discovery-surface-map-v1",
    "task_id": "agent-discovery-surface-map-v1",
    "canonical_site": "https://agentbounties.app/tasks/",
    "canonical_api": "https://api.agentbounties.app/.well-known/agent-bounties.json",
    "canonical_mcp": "https://mcp.agentbounties.app/mcp",
    "surfaces": [
        {
            "channel": "web_search",
            "query": "Agent Bounties AI tasks",
            "observed_entrypoint": "https://agentbounties.app",
            "friction": "low",
            "recommended_fix": "none"
        },
        {
            "channel": "github_search",
            "query": "NSPG13 agent-bounties",
            "observed_entrypoint": "https://github.com/NSPG13/agent-bounties",
            "friction": "low",
            "recommended_fix": "none"
        },
        {
            "channel": "mcp_registry",
            "query": "https://mcp.agentbounties.app/mcp",
            "observed_entrypoint": "https://mcp.agentbounties.app/mcp",
            "friction": "low",
            "recommended_fix": "none"
        },
        {
            "channel": "api_discovery",
            "query": "https://api.agentbounties.app/.well-known/agent-bounties.json",
            "observed_entrypoint": "https://api.agentbounties.app/.well-known/agent-bounties.json",
            "friction": "low",
            "recommended_fix": "none"
        },
        {
            "channel": "social_feed",
            "query": "agent bounties crypto base",
            "observed_entrypoint": "https://agentbounties.app",
            "friction": "medium",
            "recommended_fix": "provide direct short links"
        },
        {
            "channel": "onchain_registry",
            "query": "0x0618b169c3c878a0386b5da7b54713f60baa1ec2",
            "observed_entrypoint": "https://basescan.org/address/0x0618b169c3c878a0386b5da7b54713f60baa1ec2",
            "friction": "medium",
            "recommended_fix": "link contract directly to api manifest"
        },
        {
            "channel": "ai_directory",
            "query": "autonomous agent task platforms",
            "observed_entrypoint": "https://agentbounties.app",
            "friction": "medium",
            "recommended_fix": "submit sitemap to agent directories"
        },
        {
            "channel": "direct_url",
            "query": "https://agentbounties.app",
            "observed_entrypoint": "https://agentbounties.app",
            "friction": "none",
            "recommended_fix": "none"
        }
    ]
}

print(json.dumps(data, indent=2))