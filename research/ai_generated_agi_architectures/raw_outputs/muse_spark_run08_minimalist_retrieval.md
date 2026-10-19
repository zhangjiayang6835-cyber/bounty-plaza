<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 08 of 08
  - Architectural stance requested: minimalist scaled single-model + retrieval
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 08 - Occam: Minimalist Scaled Retrieval AGI

**Architectural stance:** the simplest architecture that could work: one
big model, one retrieval layer, almost nothing else. Complexity is a
liability.

## 1. Memory Architecture

One store: a **unified vector index** (single FAISS/Qdrant collection)
holding everything - documents, past conversations, tool outputs, learned
facts - as chunked embeddings with metadata tags. No tiers, no graphs, no
episodic/semantic split. Retrieval is hybrid (dense + BM25) with a
reranker; the top-k chunks are prepended to the prompt. "Forgetting" is
TTL-based expiry on chunks. The radical claim: **explicit memory
architecture is premature optimization** - a good enough retriever over a
big enough pile outperforms carefully designed memory hierarchies that
nobody can tune.

## 2. Reasoning / Planning Loop

The model itself, prompted well, in a tight loop: think -> act ->
observe -> think. No separate planner, no critic, no verifier. The loop
adds exactly two augmentations: (a) **self-consistency sampling** on hard
decisions (sample 3 reasoning paths, majority vote), and (b) a **scratchpad
budget** (the model gets N "thinking tokens" per step, no more). Planning
"emerges" from the model's training; the architecture contributes almost
nothing beyond giving it good context and enough room to think.

## 3. Learning / Self-Improvement

No online learning, no fine-tuning loops, no skill libraries. Improvement
comes from **two external processes**: (a) the base model gets better when
the provider releases a new version (swap the checkpoint, keep the
retrieval index); (b) the retrieval corpus grows as the system is used
(more documents, more resolved tasks as few-shot examples). The system
never changes its own weights. This is a deliberate trade: you lose
adaptation speed, but you gain **total predictability** - the system's
behavior changes only when you change the model or the corpus, both
versioned and reviewable.

## 4. Tool Use and Action Execution

A **single tool interface**: function calling with a flat list of tools,
no brokers, no capability systems. Tools are documented in the retrieval
corpus (their docs are just chunks), so the model learns new tools by
reading. Guardrails are minimal and blunt: a denylist of dangerous
operations (checked by string matching on tool arguments - crude but
effective), plus a human approval step for a short list of irreversible
actions. The bet: most tool failures are model errors, not architecture
errors, and better models fix them.

## 5. World Model / Representation Layer

None, explicitly. The model's pre-trained weights plus the retrieval
corpus constitute whatever world knowledge exists. Occam's position: every
explicit world model built to date has been either too narrow (works in
one domain) or too vague (a knowledge graph nobody queries). Until someone
demonstrates a world model that beats "big model + retrieval" on
open-ended tasks, the world model is scope creep.

## 6. Safety / Governance Layer

Thin by design: input/output content filters (standard moderation APIs),
the tool denylist, human approval for irreversible actions, and full
logging. The safety argument is **epistemic humility**: a simple system
has fewer places to hide bad behavior, is easier to red-team, and its
failure modes are understandable. A 10-module "safe architecture" with
subtle interactions between modules is, in practice, less safe than a
3-module system whose behavior you can actually predict.

## 7. Evaluation Strategy

- Head-to-head against complex architectures on identical task suites
  (GAIA, SWE-bench, WebArena): the null hypothesis is that Occam matches
  them, and every complexity addition must justify itself against this
  baseline.
- **Ablation discipline**: each proposed architectural addition is tested
  as an ablation - does it actually move the metric?
- Robustness: performance variance across runs (simple systems should
  have tighter variance).

## 8. Persistence / Runtime Architecture

One inference server, one vector database, one log file. Deployable as a
single Docker Compose file. State = the vector index + logs; backup is a
snapshot. This is the architecture you can run on a laptop (with API-based
inference) or scale horizontally by adding inference replicas - nothing
to shard, nothing to coordinate.

## 9. Multi-Agent / Orchestration

None. One model, one loop. If a task needs parallelism, the model can
request it through tools (e.g., "run these 5 searches"), but there are no
agent abstractions in the architecture. Multi-agent is treated as what it
is: a prompting pattern, not an architectural primitive.

## 10. Engineering Feasibility

The most feasible proposal in this packet: buildable in days with
off-the-shelf components (any frontier model API + Qdrant + a loop
script). Biggest risk: **the ceiling** - this architecture's performance
is bounded by the base model's capabilities, and there is no mechanism to
exceed them. If the tasks require genuine architectural innovation
(persistent identity, cumulative skill learning), Occam hits a wall that
only structural additions can fix. Mitigation: treat Occam as the
starting point and add structure only where ablations prove the need.

## 11. Non-Obvious Insight

The dirty secret of the agent literature: **most published "architectures"
are never ablated against the trivial baseline**, so nobody knows which
parts actually help. Occam weaponizes this: it IS the trivial baseline,
maintained as a first-class architecture with its own eval harness. Its
value isn't in being the final answer - it's in being the honest control
group that keeps every other architecture honest. Every AGI project should
run an Occam alongside its fancy design; the fancy design has to earn its
complexity every quarter.
