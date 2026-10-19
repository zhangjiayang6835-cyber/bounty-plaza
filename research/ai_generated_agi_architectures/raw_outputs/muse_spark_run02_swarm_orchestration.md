<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 02 of 08
  - Architectural stance requested: multi-agent swarm orchestration
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 02 - Hive: Swarm-Orchestrated Multi-Agent AGI

**Architectural stance:** general intelligence emerges from the coordinated
interaction of many specialized agents, not from one monolithic model.

## 1. Memory Architecture

Memory is **partitioned by role**, not centralized. Each specialist agent
owns a private vector store (Qdrant) for its domain episodes; a **shared
blackboard** (Redis + Postgres) holds only coordination state: task specs,
intermediate artifacts, and votes. A **collective semantic memory** (shared
pgvector collection) stores cross-agent distilled knowledge, writeable only
through a consensus protocol (2-of-3 specialist agreement) to prevent one
rogue agent from poisoning shared beliefs. No single agent sees everything -
this is deliberate, mirroring human organizations.

## 2. Reasoning / Planning Loop

A **meta-planner** decomposes the user goal into a DAG of subtasks and
assigns each to a specialist (researcher, coder, critic, planner, tool
operator, verifier). Specialists work concurrently, posting results to the
blackboard. A **critic quorum** (3 diverse models) reviews each subtask
output; majority approval moves the DAG forward, rejection triggers
replanning of that branch. The loop terminates on goal-satisfaction votes,
timeout, or budget exhaustion.

## 3. Learning / Self-Improvement

Learning happens at two levels. **Individual**: each specialist's prompts
and few-shot examples are versioned; a weekly offline job A/B tests prompt
variants against a held-out task set and promotes winners. **Collective**:
successful collaboration patterns (which specialist sequences solved which
task classes) are mined from the blackboard history and compiled into
routing policies for the meta-planner - the swarm learns how to organize
itself. No weight updates required; the system improves through better
organization of fixed-capability parts.

## 4. Tool Use and Action Execution

Each specialist gets a **minimal tool belt** (least privilege): the coder
gets code execution, the researcher gets web search, etc. A central **tool
gateway** enforces per-agent rate limits, sandboxes execution (gVisor/Firecracker
microVMs), and requires quorum approval for side-effecting actions. Tool
results are posted to the blackboard so all agents observe outcomes.

## 5. World Model / Representation Layer

No single world model. Instead, **overlapping partial models**: the
researcher's document-derived knowledge, the coder's repository map, the
planner's task-state graph. Disagreements between partial models are
surfaced to the critic quorum as explicit "model conflicts" to resolve -
this is a feature, since real-world knowledge is genuinely perspectival.
A shared entity-resolution service keeps references consistent across
agents.

## 6. Safety / Governance Layer

Defense in depth through **separation of powers**: no agent can both plan
and execute irreversible actions; the critic quorum is drawn from different
model families than the workers to avoid correlated failures; the tool
gateway is a dumb policy engine (no LLM) so it cannot be prompt-injected.
A human "swarm supervisor" dashboard shows the live DAG, agent votes, and
can pause/kill any branch. All inter-agent messages are logged immutably.

## 7. Evaluation Strategy

- Swarm benchmarks: tasks requiring genuine division of labor (multi-repo
  refactors, literature reviews with synthesis) where single-agent
  baselines are known to fail.
- Coordination metrics: communication overhead ratio, quorum agreement
  rate, deadlock frequency.
- Adversarial: inject a compromised specialist (prompt-injected) and
  measure whether the quorum + gateway contain it.
- Compare against monolithic single-model baseline on identical tasks.

## 8. Persistence / Runtime Architecture

Orchestrator as a stateful service (Temporal workflows for the DAG -
durable execution with retries). Specialists are stateless workers scaled
horizally on Kubernetes; blackboard state in Redis (hot) + Postgres
(durable). Full replay from the event log enables post-mortem debugging
and time-travel inspection.

## 9. Multi-Agent / Orchestration

This IS the architecture. Coordination protocol: blackboard + typed
message envelopes (JSON Schema) + quorum voting. Agent discovery via a
registry; new specialists can be plugged in without changing the
orchestrator. Interaction topology is dynamic: the meta-planner rewires the
DAG as subtasks complete or fail.

## 10. Engineering Feasibility

Biggest risk: **coordination overhead** - N agents chatting can burn 10x
the tokens of a single model for marginal quality gain. Mitigation: strict
message budgets per subtask, specialist outputs capped in length, quorum
only on high-stakes branches. Reuse: Temporal, LangGraph/CrewAI patterns,
Qdrant, Redis. Compute: high inference cost (many parallel calls) but
each call can use smaller/cheaper models since specialists are narrow.

## 11. Non-Obvious Insight

The standard critique of multi-agent systems - "more agents, more chaos" -
is actually the safety argument in disguise. A monolith that goes wrong
goes wrong everywhere at once; a swarm degrades gracefully because
**no single point of cognition exists to be compromised**. Specialization +
adversarial review (critic quorum) gives you both capability AND a
structural safety property that monolithic designs can only bolt on.
