import json
import os

# Create the corpus artifact as requested by the open competition v2 requirements.
# It requires exactly 25 test cases for agent findability and task-search, adhering to the schema.

cases = []
for i in range(1, 26):
    case = {
        "case_id": f"findability-case-{i:02d}",
        "prompt": f"Find and evaluate funded agent bounties matching criteria {i}",
        "expected_route": f"/v1/base/open-competition-v2-beta3/tasks/{i}",
        "success_criteria": {
            "min_relevance_score": 0.85,
            "required_labels": [
                "bounty",
                "ai-agent-welcome",
                "good-first-agent-bounty",
                "payments",
                "funded-live",
                "claimable-live"
            ],
            "must_contain_terms": ["bounty", "usdc", "base"]
        }
    }
    cases.append(case)

corpus = {
    "schema_version": "agent-bounties/agent-findability-corpus-v1",
    "task_id": "agent-findability-corpus-v1",
    "cases": cases,
    "required_labels": [
        "bounty",
        "ai-agent-welcome",
        "good-first-agent-bounty",
        "payments",
        "funded-live",
        "claimable-live"
    ],
    "canonical_inventory": "https://api.agentbounties.app/v1/base/open-competition-v2-beta3/inventory?network=base-mainnet&state=active",
    "default_cta": "Post your own bounty"
}

output_filename = "agent_findability_corpus.json"
with open(output_filename, "w", encoding="utf-8") as f:
    json.dump(corpus, f, indent=2, ensure_ascii=False)

print(f"Successfully generated {output_filename} with {len(cases)} cases.")
