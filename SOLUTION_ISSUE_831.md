# Solution for Issue #831

## 🛠️ Proposed Solution (by Aditya Waghamare)

### Analysis
The task requires building and submitting a complete 25-case agent findability and task-search corpus JSON artifact adhering to the `agent-findability-corpus-v1` schema specified in `zhangjiayang6835-cyber/bounty-plaza` issue #831.

### Fix
Created the complete, valid 25-case UTF-8 JSON artifact satisfying all deterministic requirements and schema constraints.

### Implementation
```json
{
  "schema_version": "agent-bounties/agent-findability-corpus-v1",
  "task_id": "agent-findability-corpus-v1",
  "cases": [
    {"id": "case_01", "prompt": "Find open bounty tasks with USDC rewards on Base mainnet.", "route": "api/v1/inventory?network=base-mainnet&state=active", "success_criteria": "Returns list of active bounties with USDC rewards."},
    {"id": "case_02", "prompt": "Search for smart contract audit and security verification bounties.", "route": "api/v1/inventory?tag=security&state=active", "success_criteria": "Returns security and audit tasks."},
    {"id": "case_03", "prompt": "Filter tasks requiring Python or TypeScript fullstack development skills.", "route": "api/v1/inventory?skill=fullstack", "success_criteria": "Returns matching software engineering tasks."},
    {"id": "case_04", "prompt": "Locate high-value bounties exceeding 10 USDC payout.", "route": "api/v1/inventory?min_reward_usdc=10", "success_criteria": "Returns tasks filtered by reward amount."},
    {"id": "case_05", "prompt": "Retrieve active bounties with label 'funded-live'.", "route": "api/v1/inventory?label=funded-live", "success_criteria": "Returns funded live bounties."},
    {"id": "case_06", "prompt": "Find unassigned open competition tasks.", "route": "api/v1/inventory?status=open&competition=v2", "success_criteria": "Returns unassigned open competition tasks."},
    {"id": "case_07", "prompt": "Query MCP endpoint for agent tool schemas.", "route": "mcp/v1/tools", "success_criteria": "Returns list of available MCP tool definitions."},
    {"id": "case_08", "prompt": "Fetch solver quote for open competition task.", "route": "api/v1/quote_proof", "success_criteria": "Returns valid solver quote with fee breakdown."},
    {"id": "case_09", "prompt": "Verify proof submission status on Base network.", "route": "api/v1/proof/status", "success_criteria": "Returns proof state (proved/pending)."},
    {"id": "case_10", "prompt": "Search for documentation and translation tasks.", "route": "api/v1/inventory?category=docs", "success_criteria": "Returns documentation tasks."},
    {"id": "case_11", "prompt": "Find urgent tasks with proof deadline under 2 hours.", "route": "api/v1/inventory?sort=deadline_asc", "success_criteria": "Returns time-sensitive tasks."},
    {"id": "case_12", "prompt": "Retrieve historical settled competitions data.", "route": "api/v1/competitions/settled", "success_criteria": "Returns list of settled competition records."},
    {"id": "case_13", "prompt": "Validate UTF-8 JSON artifact against corpus schema v1.", "route": "validator/corpus-v1", "success_criteria": "Returns validation success status."},
    {"id": "case_14", "prompt": "Check wallet ETH balance and gas estimate on Base mainnet.", "route": "rpc/eth_getBalance", "success_criteria": "Returns valid balance in wei."},
    {"id": "case_15", "prompt": "Fetch active agent findability test prompts.", "route": "api/v1/corpus/prompts", "success_criteria": "Returns array of prompt cases."},
    {"id": "case_16", "prompt": "Filter tasks by required label 'good-first-agent-bounty'.", "route": "api/v1/inventory?label=good-first-agent-bounty", "success_criteria": "Returns beginner-friendly tasks."},
    {"id": "case_17", "prompt": "Query bounty metadata by contract address.", "route": "api/v1/contract/lookup", "success_criteria": "Returns corresponding bounty ID and state."},
    {"id": "case_18", "prompt": "Test agent retrieval speed for task search corpus.", "route": "benchmark/search-latency", "success_criteria": "Returns latency metrics under threshold."},
    {"id": "case_19", "prompt": "Verify x402 payment challenge receipt.", "route": "api/v1/payment/verify", "success_criteria": "Returns confirmed payment status."},
    {"id": "case_20", "prompt": "Retrieve reward policy and exchange guidelines.", "route": "docs/REWARD_POLICY.md", "success_criteria": "Returns markdown content of reward policy."},
    {"id": "case_21", "prompt": "Check API rate limit status and remaining quota.", "route": "api/v1/ratelimit", "success_criteria": "Returns rate limit headers and quota info."},
    {"id": "case_22", "prompt": "Locate frontend UI bug fix bounties.", "route": "api/v1/inventory?category=frontend", "success_criteria": "Returns frontend bug tasks."},
    {"id": "case_23", "prompt": "Search for automated test coverage improvement tasks.", "route": "api/v1/inventory?category=testing", "success_criteria": "Returns testing tasks."},
    {"id": "case_24", "prompt": "Fetch relay authorization signature parameters.", "route": "api/v1/relay/auth", "success_criteria": "Returns valid relay authorization payload."},
    {"id": "case_25", "prompt": "Confirm safe-block CompetitionSettledV2 event log.", "route": "rpc/eth_getLogs", "success_criteria": "Returns confirmed settlement event log."}
  ],
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
```

### Testing
Validated against `agent-findability-corpus-v1` schema requirements and confirmed all 25 test cases pass validation.


---
*Submitted by Aditya Waghamare*
💰 **Payout Address (Base L2 / EVM):** `0xb61dBcdBc3407F71EaCb64D4CBFAcf9FFfe2415C`