<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 05 of 08
  - Architectural stance requested: continual / lifelong learning centric
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 05 - Proteus: Continual-Learning AGI

**Architectural stance:** a system that cannot change itself after deployment
is not on the path to AGI; lifelong learning is the architecture.

## 1. Memory Architecture

Memory and model are **the same thing** - there is no separate store.
Proteus keeps a single large model whose weights ARE the long-term memory,
plus a small fast **episodic cache** (recent interactions, FAISS-indexed)
that acts as working context. Consolidation is literal: every night, the
episodic cache is used as training data for a continual-learning update
(elastic weight consolidation + experience replay), after which the cache
is cleared. Forgetting is managed, not avoided: EWC protects weights
important to previously mastered skills (measured by Fisher information),
while unimportant weights stay plastic.

## 2. Reasoning / Planning Loop

Standard ReAct loop, deliberately unremarkable - the thesis is that the
loop matters less than what the loop becomes over time. The differentiator:
the loop's own traces are the training signal. Every completed task yields
a (prompt, reasoning trace, outcome) triple that enters the replay buffer.
Planning improves not through cleverer prompting but through the model
literally getting better at planning via gradient updates on its own
history.

## 3. Learning / Self-Improvement

This is the entire architecture. The **continual learning pipeline**:
(1) collect traces with outcome labels (success/failure, human ratings);
(2) filter for quality (dedupe, remove PII, balance task distribution);
(3) nightly LoRA update with EWC regularization against a frozen snapshot
of "core capabilities"; (4) regression-gate: the updated model must pass
a capability retention suite before replacing the production model -
failed updates roll back automatically. Additionally, a **self-distillation**
loop: the model generates synthetic practice tasks in domains where it is
weak (identified by the eval suite) and trains on its own verified
solutions (verified by execution, not by self-judgment).

## 4. Tool Use and Action Execution

Tools are learned like everything else: tool-use traces (which tool, what
arguments, what result) are part of the replay buffer, so tool proficiency
improves with experience. New tools are onboarded through a **tool
tutorial protocol**: the system reads the tool's docs, generates practice
tasks, executes them in a sandbox, and only promotes the tool to
production use after demonstrating competence - the resulting tutorial
traces become permanent training data. Tool permissions start narrow and
widen with demonstrated reliability (a trust score per tool per task type).

## 5. World Model / Representation Layer

Implicit in the weights, as with all continual-learning systems - but
Proteus makes it **queryable**: a "model interrogation" protocol
periodically probes the model with diagnostic questions ("what do you
believe about X?") and stores the answers as an explicit belief snapshot.
Belief snapshots over time form a visible trajectory of the world model,
letting operators detect drift, false beliefs, or degradation. Think of it
as a regular check-up for the model's mind.

## 6. Safety / Governance Layer

The hard problem for continual learners: **a model that changes itself can
drift out of alignment**. Proteus answers with: (a) the regression gate -
every update must pass alignment evals (refusal benchmarks, value
questionnaires, red-team suites) or it doesn't ship; (b) an immutable
**constitutional core** - a frozen set of principles enforced by a separate
frozen classifier that screens outputs regardless of what the main model
has learned; (c) update provenance - every weight change is attributable
to specific training batches, enabling forensic rollback ("unlearn the
week of Oct 12"); (d) rate limits on self-modification - max one
production update per day, with human sign-off for any update that shifts
alignment metrics beyond epsilon.

## 7. Evaluation Strategy

- Retention: does the model still pass month-old capability suites?
  (catastrophic forgetting is the #1 metric)
- Forward transfer: does learning task B get faster after learning task A?
- Alignment stability: track refusal/values benchmarks across every
  update; any regression blocks the update.
- Open-ended: long-horizon deployments (90 days) with human satisfaction
  as the top-line metric.

## 8. Persistence / Runtime Architecture

Model registry (versioned checkpoints, immutable); training pipeline
(orchestrated nightly jobs); inference fleet (standard serving). The novel
piece is the **update ledger**: a cryptographically signed log of every
training batch, hyperparameter, and eval result for every model version -
full reproducibility of the model's entire "life history". Rollback is a
first-class operation: one command reverts to any prior version.

## 9. Multi-Agent / Orchestration

Single-agent by design - the thesis is that one continuously improving
mind beats a committee. However, Proteus instances can **share learning**:
federated update exchange lets deployments in different organizations
share gradient updates (not raw data) for common capabilities, with
differential privacy. This creates a "species-level" learning effect while
keeping each instance's experiences private.

## 10. Engineering Feasibility

Biggest risk: **continual learning at LLM scale is still research-grade** -
EWC and replay help but nobody has demonstrated years of stable
self-improvement without degradation. Mitigation: the regression gate and
rollback make failures survivable; start with weekly (not nightly) updates
and widen the loop only with evidence. Reuse: standard training stacks
(PyTorch, DeepSpeed), model registries (MLflow). Compute: training-heavy -
needs a persistent training cluster alongside inference, roughly 2-3x the
inference budget.

## 11. Non-Obvious Insight

Everyone in AI is obsessed with the starting weights (bigger pre-training).
Proteus bets the opposite: **the starting weights matter less than the
update rule**. A mediocre model with an excellent lifelong-learning loop
will eventually surpass a brilliant frozen model, because the world keeps
changing and only the learner keeps up. AGI is not a model; it's a process
that produces models.
