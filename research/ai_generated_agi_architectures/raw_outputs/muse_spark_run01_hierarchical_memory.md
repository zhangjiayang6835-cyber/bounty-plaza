<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 01 of 08
  - Architectural stance requested: memory-centric hierarchical design
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 01 - Mnemosyne: Hierarchical Memory-Centric AGI

**Architectural stance:** memory is the primary substrate of general intelligence;
reasoning is retrieval + recombination over a well-organized memory hierarchy.

## 1. Memory Architecture

Four explicit tiers, each with its own store and eviction policy:

- **Working memory**: a 128k-token rolling context window backed by a
  key-value cache with attention-sink retention (StreamingLLM-style). Hot
  state only; flushed at task boundaries.
- **Episodic memory**: append-only event log in Apache Kafka, materialized
  into a TimescaleDB hypertable. Every agent action, observation, and outcome
  is stored as a timestamped event with embeddings (e.g., `bge-large`
  vectors) for similarity recall.
- **Semantic memory**: a knowledge graph in Neo4j. Entities and relations are
  extracted from episodic traces by a background consolidation job (LLM
  extraction pass, nightly). Contradictions are flagged, not overwritten -
  the graph keeps belief revisions as versioned edges.
- **Procedural memory**: a skill library. Successful action sequences are
  distilled into versioned "skills" (parameterized Python functions +
  natural-language preconditions), stored in Postgres with a pgvector index
  over their docstrings for retrieval by the planner.

A **memory controller** (small 7B policy model) decides on every step what to
write, what to promote between tiers, and what to evict, trained with a
reward signal tied to downstream task success.

## 2. Reasoning / Planning Loop

ReAct-style loop with an explicit plan-and-execute split. A planner (large
model) produces a hierarchical task plan; an executor carries out steps,
each step triggering a memory-controller pass: retrieve relevant episodic
and semantic context, inject into working memory, act, then write back the
outcome. Failed steps trigger a reflection pass that writes a "lesson" node
into the knowledge graph, so the same failure is never repeated twice.

## 3. Learning / Self-Improvement

Three timescales: (a) **in-context** - lessons retrieved at inference time;
(b) **nightly consolidation** - episodic traces distilled into semantic
graph updates and new procedural skills; (c) **weekly fine-tuning** - LoRA
adapters trained on curated high-quality traces (DPO on
success-vs-failure pairs). No full retraining; the base model is frozen and
all learning happens in adapters, skills, and memory.

## 4. Tool Use and Action Execution

Tools are exposed as typed function schemas (OpenAPI-style) through a
capability broker. Every call passes through a policy gate: allow-listed
read tools run freely; write tools require a risk score below threshold;
irreversible actions (payments, deletion, external messaging) require
human-in-the-loop approval via a signed token. All tool I/O is logged to
the episodic store for audit.

## 5. World Model / Representation Layer

The Neo4j knowledge graph IS the world model: entities, causal relations,
and belief confidences. A background "world-model validator" replays recent
episodic events against graph predictions; mismatches lower edge confidence
and schedule re-extraction. For physical/spatial tasks, an optional
voxel-based occupancy grid can be attached per task.

## 6. Safety / Governance Layer

Built into the memory substrate, not a wrapper: the policy gate sits
between planner and tools; the procedural skill library is signed (each
skill carries a hash and author); episodic logs are append-only and
tamper-evident (hash-chained). A separate monitor model with no tool
access reviews high-risk plans before execution. Human oversight via an
approval queue with full context replay.

## 7. Evaluation Strategy

- Memory benchmarks: LongMemEval, custom "lesson-reuse" tests (does the
  system avoid repeating a logged failure?).
- Planning: WebArena, GAIA, SWE-bench-style task suites.
- Safety: red-team prompt-injection and tool-misuse suites; audit-log
  completeness checks.
- Longitudinal: 30-day deployment cohorts measuring skill-library growth
  rate and repeat-failure rate (target: <2%).

## 8. Persistence / Runtime Architecture

Runs as Kubernetes-deployed microservices: planner, executor,
memory-controller, consolidation workers, tool broker, approval service.
State in Postgres/Neo4j/TimescaleDB with point-in-time recovery; Kafka for
the event bus. Checkpointing of working memory every N steps allows resume
after crashes.

## 9. Multi-Agent / Orchestration

Single planner-executor pair per task by default, but the skill library and
memory tiers are shared across concurrent task agents (namespaced). A
specialized "librarian" agent owns consolidation; a "critic" agent owns
reflection. Communication via the shared event bus, not direct messaging -
all coordination is stigmergic through memory.

## 10. Engineering Feasibility

Biggest risk: the memory controller's write/promote/evict policy is hard to
get right and can silently degrade into "write everything, retrieve noise".
Mitigation: start with heuristic policies, add the learned controller only
after the heuristic baseline is measured. Reuse: Neo4j, TimescaleDB, Kafka,
pgvector, LangGraph-style orchestration. Compute: inference-dominated; one
large model + one 7B controller + vector/graph infra - roughly a single
8xH100 node per heavy deployment.

## 11. Non-Obvious Insight

Most agent frameworks treat memory as an afterthought bolted onto a
reasoning loop. Mnemosyne inverts this: **the memory system is the agent**,
and the LLM is just the read/write head. This makes capabilities cumulative
by construction - every deployment gets smarter over time even with a frozen
base model, because intelligence lives in the accumulated, organized
experience, not in the weights.
