# Synthesis - A Proposed Combined Architecture for Cognitive-OS

This document extracts the strongest idea from each of the 8 collected
proposals and composes them into one coherent architecture recommendation
for Cognitive-OS planning. Every choice below is traceable to a specific
run (cited in brackets).

## Design Principles (distilled)

1. **Boring substrate, clever organization** [run06, run08]: build on
   proven infrastructure (files, Postgres, standard serving); spend
   innovation budget on organization and verification, not new runtimes.
2. **Cumulative by construction** [run01, run05]: every deployment must get
   smarter over time, even with frozen weights.
3. **Verification before execution for the irreversible** [run04, run07]:
   the cost of checking must scale with the cost of being wrong.
4. **No unsupervised minds** [run07]: every agent, subagent, and update
   pipeline operates under explicit granted authority.

## Proposed Architecture: "Cognitive-OS Reference v0"

### Substrate layer [run06 + run01]
- **File-backed working state**: git-versioned workspace per task, human
  readable (`PLAN.md`, `MEMORY.md`, `LESSONS.md`). This is the primary
  interface for both the agent and the operator.
- **Tiered long-term memory** behind the files: episodic event log
  (TimescaleDB) feeding a nightly consolidation job that maintains a
  semantic knowledge graph (Neo4j) and a procedural skill library
  (versioned scripts + pgvector index). The agent reads/writes files; the
  consolidation pipeline maintains the tiers invisibly.
- **Learned memory policy** [run01]: a small controller decides
  write/promote/evict, starting from heuristics, upgraded to a learned
  policy once the baseline is measured.

### Cognition layer [run02 + run03]
- **Planner-executor split** with a **predictive check**: before executing
  any multi-step plan, roll it out against a lightweight learned forward
  model of tool effects [run03, scoped to tools not the whole world -
  honest about feasibility]. Plans whose simulated outcomes look bad are
  revised before touching reality.
- **Critic quorum** [run02]: high-stakes plans require majority approval
  from 2+ diverse reviewer models before execution.

### Verification & governance layer [run04 + run07]
- **Contract-checked tools**: every tool declares pre/post-conditions;
  the composition of a planned tool chain is symbolically checked (Z3)
  before execution. Tools without contracts run sandboxed.
- **Capability grants** [run07]: sessions start with an explicit,
  budgeted set of tool capabilities; escalation needs re-authorization.
- **Mandatory human approval** for the irreversible set (payments, data
  deletion, external messaging, permission changes) - no exceptions, no
  "the model was confident" bypasses.

### Learning layer [run05, gated by run07]
- **Nightly consolidation** (memory tiers + skill extraction) runs always.
- **Weight updates** run weekly at most, behind a regression gate:
  capability-retention suite + alignment suite must pass, else automatic
  rollback. Full update ledger (signed batches, hyperparams, evals).
- Self-modification is classified as the highest-privilege operation and
  needs human sign-off [run07].

### Baseline discipline [run08]
- Maintain an **Occam instance** (single model + retrieval, no tiers, no
  quorum) running the same eval suite. Every architectural addition to the
  reference design must beat Occam on a pre-registered metric to stay.
  Complexity must be earned, quarterly.

## Phased Build Plan

- **Phase 1 (weeks)**: file-backed agent + tool contracts for the top-5
  riskiest tools + human approval list. (run06 + run04-lite)
- **Phase 2 (1-2 months)**: episodic log + consolidation pipeline
  (KG + skill library), critic quorum on high-stakes branches.
  (run01 + run02)
- **Phase 3 (quarter)**: capability grants, predictive tool-effect checks,
  weekly gated weight updates with ledger. (run07 + run03-scoped + run05)
- **Continuous**: Occam baseline evals; ablation review each quarter.

## What This Synthesis Deliberately Excludes

- A full open-world predictive model [run03's core bet]: judged not yet
  feasible; replaced by scoped tool-effect models.
- Unrestricted continual weight updates: allowed only behind the
  regression gate, because silent drift is the top long-term risk.
- Pure multi-agent swarm as the default topology [run02]: adopted
  selectively (critic quorum) rather than as the whole architecture,
  to contain coordination overhead.

## Traceability Matrix

| Synthesis element | Source run(s) |
|---|---|
| File-backed working state | run06 |
| Tiered memory + consolidation | run01 |
| Learned memory policy | run01 |
| Predictive tool-effect check | run03 (scoped) |
| Critic quorum | run02 |
| Tool contracts + symbolic check | run04 |
| Capability grants, delegation attenuation | run07 |
| Human approval for irreversible | run01, run02, run06, run07, run08 (consensus) |
| Gated weight updates + ledger | run05 (+ run07 gate) |
| Occam baseline discipline | run08 |
