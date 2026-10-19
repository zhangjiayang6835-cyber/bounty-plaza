<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 04 of 08
  - Architectural stance requested: neuro-symbolic hybrid design
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 04 - Syllogism: Neuro-Symbolic Hybrid AGI

**Architectural stance:** neural networks guess, symbolic systems verify;
AGI needs both - intuition for breadth, logic for reliability.

## 1. Memory Architecture

Dual representation for everything: **neural memory** (vector embeddings
in pgvector for fuzzy associative recall) and **symbolic memory** (a
Datalog/Prolog-style fact store in Souffle or a custom triple store).
Every learned fact exists in both forms, linked by ID. Neural memory
handles "reminds me of..." retrieval; symbolic memory handles "prove
that..." queries. Procedural knowledge is stored as both neural skills
(embeddings of demonstrations) and symbolic operators (PDDL domain
definitions) so the planner can switch representations per subtask.

## 2. Reasoning / Planning Loop

**Generate-and-verify loop**: the neural policy proposes candidate plans
(fast, creative, possibly wrong); a symbolic verifier checks each against
hard constraints encoded in logic (preconditions, invariants, resource
bounds). Only verified plans execute. For domains with formal structure
(scheduling, configuration, code), the system can flip to **solver-first**
mode: encode the problem in SMT (Z3) and let the solver find the optimal
plan, with the neural model only translating between natural language and
formal encoding. Unverifiable domains (creative writing, open conversation)
run neural-only with a flag marking outputs as "unverified".

## 3. Learning / Self-Improvement

Two learning channels: **neural** (standard fine-tuning/DPO on traces) and
**symbolic** (inductive logic programming - generalizing rules from
examples, e.g., "every deployment that skipped staging failed" becomes a
symbolic constraint). A **distillation bridge** converts repeated neural
successes into symbolic rules (when the same pattern succeeds 50+ times,
propose it as a candidate rule for human or auto-approval) and converts
symbolic proofs into neural training data (proof traces as chain-of-thought
supervision). The system literally learns to be more logical over time.

## 4. Tool Use and Action Execution

Tools declare **formal contracts**: preconditions, postconditions, and
effects in a machine-checkable spec language (like TLA+ light). Before
executing a tool chain, the symbolic layer composes the contracts and
proves the composition safe (no precondition violations, no resource
overruns). Tools without contracts run in a sandbox with neural-only
oversight and are gradually "promoted" to contracted status as their
behavior is characterized. This makes tool use auditable by construction.

## 5. World Model / Representation Layer

Hybrid: a **causal graph** (symbolic, queryable, explainable) overlaid on a
**neural embedding space** (fuzzy, fast). The causal graph supports
counterfactual queries ("what if we had deployed on Tuesday?") via
do-calculus; the embedding space supports analogy ("this outage resembles
the 2024 cache incident"). A consistency maintainer flags where the two
disagree, and those disagreements become prioritized learning targets.

## 6. Safety / Governance Layer

The strongest safety story of any proposal here: **safety as proof
obligations**. Critical invariants (never exfiltrate credentials, never
delete without backup, spending caps) are encoded as symbolic constraints
that the verifier MUST prove before execution - not guidelines, but
mathematical guarantees within the modeled domain. Neural outputs that
cannot be verified are automatically routed to human review. The trusted
computing base (verifier + contract checker) is small, deterministic, and
formally tested - deliberately kept free of ML.

## 7. Evaluation Strategy

- Logic benchmarks: ProofWriter, FOLIO, custom contract-verification suites.
- Hybrid tasks: problems requiring both intuition and rigor (e.g., "find
  the cheapest valid cloud architecture under these 40 constraints").
- Measure the **verification coverage**: what fraction of executed plans
  carried a proof? Target: 100% for irreversible actions.
- Adversarial: can prompt injection smuggle an unverified plan past the
  verifier? (It shouldn't - the verifier doesn't read natural language.)

## 8. Persistence / Runtime Architecture

Stateless neural inference tier + stateful symbolic tier (fact store with
ACID transactions - SQLite/Postgres for facts, Z3 as a service). The
symbolic store is the system of record; neural caches are disposable.
Snapshots version both the fact base and the neural adapters together so
any past decision can be re-verified.

## 9. Multi-Agent / Orchestration

Role split along the neuro-symbolic line: **intuition agents** (neural,
propose) and **auditor agents** (symbolic, verify), in a mandatory
propose-verify pipeline. Multiple intuition agents can compete (best
verified proposal wins); there is exactly one auditor per safety domain,
and auditors are never neural - they run deterministic logic, so their
behavior is identical every time.

## 10. Engineering Feasibility

Biggest risk: the **formalization bottleneck** - writing correct symbolic
contracts for real-world tools and invariants is labor-intensive, and an
incomplete contract gives false confidence. Mitigation: start with
contracts only for the highest-risk tools; everything else stays
neural+sandboxed. Reuse: Z3, Souffle, PDDL planners, TLA+. Compute:
modest - symbolic reasoning is CPU-cheap; the neural side is standard
inference.

## 11. Non-Obvious Insight

The AI safety community debates whether to align the model or constrain
the system. Syllogism shows it's a false choice at the architecture level:
**keep the neural part as wild and creative as possible, and make the
symbolic part as rigid as possible**. Capability comes from the neural
side's freedom; safety comes from the symbolic side's refusal to negotiate.
Most hybrid proposals timidly blend the two; the winning move is to keep
them maximally separate and let verification be adversarial.
