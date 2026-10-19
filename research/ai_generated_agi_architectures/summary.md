# Summary: Common Patterns, Disagreements, and Notable Ideas

## Common patterns (7 of 8 or 8 of 8 agreement)

1. **The agency loop is settled.** Every proposal independently converges
   on plan -> act -> observe -> re-plan with explicit persistent state.
   No proposal defends a purely reactive or purely deliberative extreme.
   This is the strongest consensus in the packet.
2. **Tools are load-bearing.** All eight treat tool use (code execution,
   APIs, search) as a first-class subsystem with sandboxing and logging -
   not an accessory. The agent *is* the loop plus its tools.
3. **Episodic records are universal.** Every proposal keeps a structured
   log of what the agent did; they differ only in where it lives and who
   can read it.
4. **Verification beats prediction.** Six of eight proposals include an
   explicit "check before commit" step (simulation, debate, proof,
   checker model). The field has moved past blind autoregressive action.
5. **Tiered deployment.** Seven of eight separate a "thinking" tier from
   execution tiers by cost/capability - the economics of inference demand
   it regardless of philosophy.
6. **Human-set fitness.** Even the most self-improving proposals
   (DeepSeek, Google) keep humans defining the eval/fitness function. No
   proposal endorses open-ended recursive self-improvement without gates.

## Fundamental disagreements

1. **What is scarce?** OpenAI: test-time compute. Anthropic: trustworthy
   oversight. DeepSeek: experiment cost. Mistral: owner trust. Google:
   simulation fidelity. This single disagreement explains most
   architectural differences - each system optimizes a different scarcity.
2. **Where does safety live?** Layer school (OpenAI, Google, xAI: monitors
   and shells around the core) vs. property school (Anthropic, DeepSeek,
   Mistral: legibility, verifiability, auditability as intrinsic
   properties). The property school is more ambitious and less proven.
3. **Memory centralization.** Central knowledge graph (OpenAI) vs.
   federated permissioned stores (Anthropic) vs. compressed attention
   (DeepSeek, Mistral) vs. community packs (Meta). No consensus; this is
   the least mature subsystem across all proposals.
4. **Openness.** Four proposals treat open weights as architecturally
   load-bearing (DeepSeek, Qwen, Meta, Mistral); four treat frontier
   capability as requiring centralized control. The disagreement is
   values-deep and will not be resolved by benchmarks.
5. **World models.** Separate learned simulator (Google), implicit
   grounded dynamics (DeepSeek), two-speed belief system (xAI),
   language-agnostic causal core (Qwen). Four different answers to "how
   does it model reality."

## Notable ideas worth stealing (one per proposal)

- **OpenAI:** deliberative checkpoints with RL-trained calibrated
  self-assessment - process supervision as a runtime pattern.
- **Anthropic:** MCP as the single protocol for tools, data, *and*
  sub-agents - one audit surface for all external capability.
- **Google:** simulate-then-act in a natively multimodal representation -
  planning without translation loss.
- **xAI:** beliefs with corroboration scores and provenance chains;
  "loud staleness" (announce old information instead of silently using it).
- **DeepSeek:** capability budgets - the right to act in high-stakes
  domains is earned through a verification record, not granted by role.
- **Qwen:** degradation curves published per tier - honest, measured
  statements of what smaller models can and cannot do.
- **Meta:** heterogeneous agent societies where model diversity is itself
  a safety property (uncorrelated blind spots).
- **Mistral:** air-gap evals - "can the whole system run offline?" as a
  pass/fail acceptance test.

## What the packet does NOT establish

- Which architecture would actually win on benchmarks - these are
  design proposals, not experimental results.
- Cost figures - deliberately omitted; they would be fabricated.
- Any claim about unreleased models - all family names used are real and
  current as of October 2026 (see sources.md).
