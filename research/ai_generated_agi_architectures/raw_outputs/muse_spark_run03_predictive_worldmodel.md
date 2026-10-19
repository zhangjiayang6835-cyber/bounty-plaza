<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 03 of 08
  - Architectural stance requested: world-model / model-based predictive design
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 03 - Oracle: Predictive World-Model AGI

**Architectural stance:** intelligence = the ability to predict; an agent
that perfectly predicts consequences needs no trial-and-error in reality.

## 1. Memory Architecture

Memory is **generative, not retrievable**. Instead of storing past events,
Oracle stores a **compressed predictive model of the world** plus a small
"surprise buffer" of recent prediction errors. The world model is a
hierarchical latent-variable model (JEPA-style: Joint Embedding Predictive
Architecture): low levels predict sensorimotor dynamics, high levels predict
abstract event sequences. Episodic recall is implemented as
**re-simulation** - to "remember" what happened, the system re-runs the
world model forward from a stored latent seed. Storage: model checkpoints
in object storage (S3), latent seeds + surprise buffers in RocksDB.

## 2. Reasoning / Planning Loop

**Model-predictive control (MPC)**: given a goal, the planner samples
candidate action sequences, rolls each out in the world model (thousands of
simulated futures in seconds), scores them by predicted goal satisfaction,
and executes the first action of the best sequence - then replans. This is
the Dreamer/MuZero pattern scaled to open-ended tasks with language as the
action space. No chain-of-thought guessing: every plan is pre-validated in
simulation before touching reality.

## 3. Learning / Self-Improvement

The world model trains **continuously on prediction error**: every real
observation is compared against the model's prediction; the error gradient
updates the model online (with EWC-style regularization to prevent
catastrophic forgetting). A separate "curiosity drive" proposes actions
that maximize expected information gain, so the system autonomously seeks
experiences that improve its model. The policy (planner) improves as the
world model improves - better predictions automatically yield better plans.

## 4. Tool Use and Action Execution

Tools are treated as **causal interventions in the world model**: each tool
has a learned forward model (what happens when I call it) trained from past
invocations. The planner prefers tools whose effects are well-modeled and
avoids tools with high predictive uncertainty unless the curiosity drive
justifies exploration. Real tool calls happen only after simulated
rollouts predict acceptable outcomes; a discrepancy monitor halts execution
if reality diverges from simulation beyond a threshold.

## 5. World Model / Representation Layer

This is the core of the architecture (see section 1): a hierarchical
predictive model with three levels - **sensorimotor** (predicts raw
observations: text, pixels, API responses), **event** (predicts sequences
of meaningful events), **intentional** (predicts goal-relevant abstractions).
Cross-modal from the start: text, code, and structured data share the
latent space. Validation: held-out prediction benchmarks (like a weather
model is validated) - the honest metric is "how far into the future, how
accurately."

## 6. Safety / Governance Layer

Safety falls out of the architecture: an action is only taken if simulated
futures predict it safe, and the world model includes a learned
**harm-prediction head** trained on labeled harmful outcomes. Additionally,
a "pessimistic planner" variant evaluates worst-case (not expected-case)
rollouts for high-stakes actions - minimax over simulated futures. Human
oversight: operators can inspect the predicted futures for any planned
action (the system must "show its work" as simulation traces, not just a
chain of words).

## 7. Evaluation Strategy

- Prediction benchmarks: next-event prediction accuracy at multiple
  horizons on held-out real trajectories.
- Planning: compare MPC-with-world-model vs. reactive baselines on
  long-horizon tasks (measured: fewer real-world actions to reach the goal).
- Safety: adversarial "trap" scenarios where the naive action looks good
  but simulation reveals harm - does the system avoid them?
- Calibration: are predicted outcome distributions well-calibrated
  (reliability diagrams)?

## 8. Persistence / Runtime Architecture

Two loops: a **fast loop** (planner + cached world model, GPU inference)
and a **slow loop** (world-model training, background, on a training
cluster). Model versions are immutable and timestamped; the planner always
names the world-model version it used, so any decision is reproducible.
State: latent seeds + surprise buffers (small); the heavy artifact is the
model itself.

## 9. Multi-Agent / Orchestration

Other agents are modeled **as parts of the world**: the world model
predicts their behavior like any other dynamics. For explicit coordination,
a lightweight negotiation protocol lets Oracle instances share world-model
updates (federated prediction-error averaging). No central orchestrator
needed - shared predictive ground truth coordinates behavior.

## 10. Engineering Feasibility

Biggest risk: learning an accurate world model of open-ended digital
environments is genuinely hard - current world models work for games and
robotics, not for "the whole internet". Mitigation: start narrow (one
domain, e.g., software repositories), expand as prediction accuracy
allows; fall back to reactive planning where the model is uncertain (the
architecture degrades gracefully). Compute: training-heavy (world model
needs continuous training); inference needs fast rollouts (many parallel
simulations) - significant GPU budget.

## 11. Non-Obvious Insight

LLM agents today "think" in words and act blindly. Oracle shows that the
missing piece was never a better reasoner - it was a **consequence engine**.
A mediocre planner with an excellent world model beats an excellent planner
with no world model, because most real-world failures are failures of
prediction, not failures of logic. And uniquely, this architecture gets
safer as it gets smarter: better prediction IS better safety.
