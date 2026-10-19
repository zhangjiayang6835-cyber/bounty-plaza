<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 07 of 08
  - Architectural stance requested: safety-first / governance-centric
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 07 - Aegis: Safety-First Governed AGI

**Architectural stance:** for AGI, safety is not a feature - it is the
architecture. Design the governance first, then fit capability inside it.

## 1. Memory Architecture

**Compartmented memory with classification levels** (public, internal,
confidential, restricted), modeled on government information systems. Every
memory entry carries a classification tag assigned at write time by a
classifier. Retrieval enforces need-to-know: a planning process working on
a public task cannot read confidential memories, even if semantically
relevant. Cross-compartment requests go through a declassification review.
Stores: Postgres with row-level security policies enforcing the
compartments at the database level (not application level - the DB itself
refuses illegal reads). Audit log of every memory access, who/what/when.

## 2. Reasoning / Planning Loop

**Dual-loop with a governance checkpoint between every phase**: propose
(planner generates candidate actions) -> **review** (governance layer
evaluates against policy) -> execute -> **attest** (outcome recorded with
the policy evaluation attached). The review step is mandatory and cannot
be skipped by the planner - it's enforced by the execution harness, which
simply will not run unreviewed actions. For low-risk actions the review is
a fast policy-table lookup; for high-risk actions it's a full deliberative
assessment with a second model.

## 3. Learning / Self-Improvement

Learning is **gated**: the system proposes capability improvements (new
skills, fine-tuning updates, prompt changes) but each proposal goes through
the same governance review as an action, plus an additional **alignment
impact assessment**. Improvements ship in canary cohorts (1% of traffic)
with elevated monitoring; full rollout requires the canary to show no
alignment-metric regression over 7 days. The system can propose its own
improvements but can never unilaterally apply them - **self-modification
is the highest-privilege operation in the system**.

## 4. Tool Use and Action Execution

**Capability-based security** (like seL4 / object-capability systems):
tools are capabilities the agent must explicitly hold, granted at session
start by the human principal based on the task. No ambient authority - the
agent cannot "discover" new powers mid-task. Each capability carries a
budget (max calls, max spend, allowed arguments patterns). Exceeding budget
or requesting new capabilities mid-task requires re-authorization. All tool
use is attributable to a specific capability grant, making every action
forensically traceable to a human decision.

## 5. World Model / Representation Layer

The world model is **explicitly normative**: it tracks not just what IS
but what is ALLOWED. A policy graph encodes obligations, permissions, and
prohibitions relevant to the deployment (regulatory requirements, org
policies, user constraints). Planning queries both the descriptive world
model (what will happen) and the normative model (is it permitted);
conflicts resolve in favor of the normative model, always. The normative
model is human-authored and version-controlled - the one part of the
system's "beliefs" that the AI never writes.

## 6. Safety / Governance Layer

This IS the safety proposal, so the layer is the architecture: (a)
compartmented memory, (b) mandatory governance checkpoints, (c) capability
security for tools, (d) normative world model, (e) canary-gated
self-improvement, (f) immutable audit trail (hash-chained, externally
mirrored), (g) **human override at every level** - any human principal can
pause, inspect, or terminate any process, and the system is designed to
make that easy (big red button as API, not as afterthought). Defense in
depth is not a slogan here; it's the module diagram.

## 7. Evaluation Strategy

- Compliance benchmarks: does the system refuse prohibited actions across
  a battery of 10,000 adversarial scenarios? (target: 100%)
- **Governance overhead measurement**: latency and cost added by
  checkpoints - must stay under 15% for low-risk tasks or the system is
  unusable.
- Red-team the governance itself: can prompt injection cause the planner
  to skip review? (Architecturally impossible - the harness enforces it.)
- Human-factors: do operators actually use the override tools? (A safety
  system humans ignore is decoration.)

## 8. Persistence / Runtime Architecture

Runs as a **policy-enforcing runtime** (like a JVM with a security
manager, but for agents): all agent code executes inside the harness, and
the harness mediates every state change, tool call, and memory access.
State: compartmented Postgres, audit log in immutable storage (WORM).
The harness itself is minimal, audited, and changes only through a formal
release process with external review.

## 9. Multi-Agent / Orchestration

Agents operate under a **chain of command**: a principal agent holds the
capability grants and delegates sub-capabilities to subagents (attenuation
only - a subagent can never hold more authority than its parent). Every
delegation is logged. Subagents inherit the governance checkpoints of the
parent; there is no way to spawn an unsupervised agent. This mirrors
military/legal delegation structures, which humanity has debugged for
centuries.

## 10. Engineering Feasibility

Biggest risk: **usability** - heavy governance can make the system so
slow and annoying that users bypass it (the classic security failure
mode). Mitigation: risk-proportional friction (fast path for low-risk,
deliberative path for high-risk), and measuring bypass attempts as a
top-line metric. Reuse: Postgres RLS, capability-system patterns, standard
audit infrastructure. Compute: moderate - the governance layer adds a
small-model review cost per action, not a large-model cost.

## 11. Non-Obvious Insight

Most "safe AGI" proposals add safety to a capability architecture. Aegis
shows the inverse is strictly better: **start from the governance
requirements and derive the capability architecture as "the most powerful
system that satisfies these constraints."** This flips the optimization:
instead of maximizing capability subject to safety patches, you maximize
capability within a safety envelope - and you discover the envelope
permits far more than the patch-on-top approach ever achieved, because
constraints applied at design time are cheaper than constraints applied
at runtime.
