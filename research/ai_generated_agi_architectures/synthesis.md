# Synthesis: MERIDIAN - A Combined Architecture for Cognitive-OS

## Design principle

Take the strongest *mechanism* from each proposal, not the strongest
*slogan*. Every component below is chosen because it solves a concrete
failure mode observed in real agent deployments, and every component
names its source proposal so the choice is auditable.

## Architecture: MERIDIAN (Modular, Evaluated, Rehearsed, Inspectable,
Distributed, Incrementally-trusted, Auditable Network)

```
                        +----------------------------+
                        |      DELIBERATION CORE     |  (from OpenAI:
                        |  reasoning model, variable |   variable test-time
                        |  test-time budget          |   budget + checkpoints)
                        +-------------+--------------+
                                      |
        +-----------------------------+-----------------------------+
        |                             |                             |
+-------v--------+           +---------v----------+       +----------v---------+
|  WORLD         |           |  UNIFIED TOOL BUS   |       |  MEMORY FABRIC     |
|  REHEARSAL     |           |  (MCP-compatible,   |       |  - episodic log    |
|  (from Google: |           |   from Anthropic)   |       |    (hash-chained,   |
|  simulate-     |           |  typed, sandboxed,  |       |    from Anthropic) |
|  then-act for  |           |  fully logged       |       |  - belief store    |
|  non-trivial   |           |                    |       |    w/ corroboration|
|  plans)        |           |                    |       |    (from xAI)      |
+-------+--------+           +---------+----------+       +----------+---------+
        |                              |                             |
        +------------------------------+-----------------------------+
                                       |
                        +--------------v--------------+
                        |   TRUST GOVERNOR            |
                        |   - capability budgets      |
                        |     (from DeepSeek: earn    |
                        |      action rights via      |
                        |      verification record)   |
                        |   - constitution checks     |
                        |     (from Anthropic)        |
                        |   - interpretability probes |
                        |     (from Anthropic)        |
                        |   - loud staleness alarms   |
                        |     (from xAI)              |
                        +-----------------------------+
```

## Component specifications (implementation-oriented)

### 1. Deliberation core
- A reasoning-class model run with a **per-task compute budget**
  (from OpenAI). Budget policy: spend is proportional to estimated
  uncertainty x stakes; a fixed formula, not vibes.
- **Deliberative checkpoints** every K tool calls: the core must emit a
  structured self-assessment (`on_track: bool`, `evidence: [...]`,
  `what_would_change_my_mind: [...]`) before continuing.

### 2. World rehearsal
- For plans above a complexity threshold, a **simulator rolls out the
  top-3 candidate trajectories** and scores them (from Google). v1: a
  lightweight textual/causal simulator; v2: multimodal where available.
- Rehearsal is mandatory before any irreversible action class
  (external messages, payments, physical actuation).

### 3. Unified tool bus (MCP-compatible)
- One protocol for tools, datastores, and sub-agents (from Anthropic).
  Every capability is declared, versioned, and logged.
- Sandboxed execution with capability tokens; tool results re-enter as
  observations, never as trusted facts (from xAI: corroborate, don't
  swallow).

### 4. Memory fabric
- **Episodic log:** append-only, hash-chained, per-run (from Anthropic).
- **Belief store:** claims carry corroboration scores + provenance
  (from xAI). Acting on a belief below the evidence threshold for the
  action's stakes is blocked by the Trust Governor.
- **Working memory:** the model's context window; long-horizon state
  lives in the fabric, not in the prompt.

### 5. Trust Governor (the safety core)
Combines three mechanisms instead of betting on one:
- **Capability budgets** (from DeepSeek): each agent instance accrues
  the right to take higher-stakes actions through a record of verified
  successes. New instances start untrusted.
- **Constitution checks** (from Anthropic): high-stakes actions require
  an explicit duty-check section in the reasoning trace.
- **Loud staleness** (from xAI): if the belief store's freshness SLA is
  breached, the system announces degraded mode instead of acting
  confidently on old data.

### 6. Multi-agent layer
- **Heterogeneous specialists** on the shared tool bus (from Meta):
  planner, researcher, coder, critic - drawn from different fine-tune
  lineages where available, so blind spots are uncorrelated.
- **Proposer/skeptic pairing** for contested decisions (from xAI).
- All inter-agent traffic goes through the logged tool bus - no side
  channels (from Anthropic).

### 7. Learning loop
- **Trajectory RL** on verifiable outcomes (from DeepSeek): weekly
  training rounds on episodes scored by task evals.
- **Distillation down the tiers** (from Qwen): every capability level
  gets a smaller sibling; degradation curves are measured and published.
- **Humans own the fitness function** (unanimous across all 8
  proposals): evals and the constitution change only by human decision.

### 8. Deployment topology
- **Reference: sovereign-capable** (from Mistral): the full stack must
  be able to run on owner-controlled infrastructure; air-gap operation
  is a tested configuration, not a brochure claim.
- **Federated memory option** (from Anthropic/Qwen): private episodes
  stay on-device; only consented distillations move upward.

## Build order (12-month roadmap)

| Phase | Months | Deliverable | Source patterns |
|---|---|---|---|
| 1 | 0-3 | Tool bus (MCP-compatible) + sandboxed exec + episodic log | Anthropic, OpenAI |
| 2 | 3-6 | Deliberation core with compute budgets + checkpoints; belief store with corroboration | OpenAI, xAI |
| 3 | 6-9 | Rehearsal simulator (textual v1) mandatory before irreversible actions; Trust Governor v1 (capability budgets) | Google, DeepSeek |
| 4 | 9-12 | Multi-agent layer (heterogeneous specialists, proposer/skeptic); trajectory RL loop; tiered distillation with published degradation curves | Meta, xAI, Qwen |

## What MERIDIAN deliberately does NOT include
- Recursive self-improvement of the training loop (unanimously gated
  across proposals; excluded until the eval science exists).
- A single general world simulator in v1 (Google's bet is noted as the
  highest-variance component; MERIDIAN starts with a lightweight
  rehearsal layer and earns the full simulator).
- Centralized silent learning from private episodes (rejected on
  Anthropic/Mistral grounds).

## Why this synthesis is concrete enough to build from
Every component names: its inputs/outputs (tool bus schemas), its data
structures (hash-chained log, belief records with scores), its gating
rule (budgets, thresholds, mandatory rehearsal classes), and its build
phase. A team reading this can produce work tickets; a team reading a
philosophical synthesis cannot.
