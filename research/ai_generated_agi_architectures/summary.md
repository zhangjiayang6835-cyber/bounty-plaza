# Summary - Patterns Across 8 AGI Architecture Proposals

## Common Patterns (appearing in 5+ of 8 proposals)

1. **Retrieval is universal.** Every proposal includes some form of retrieval
   over past experience (run01 tiers, run02 blackboard, run06 filesystem,
   run08 single index). No proposal relies on weights alone. The field has
   converged: memory is not optional.
2. **Separation of planning and execution.** 6 of 8 proposals split "decide
   what to do" from "do it" (planner/executor, propose/verify, MPC/simulate).
   Only run06 and run08 keep a single loop - and both acknowledge it as a
   deliberate simplification.
3. **Tools as the body.** All 8 treat external tools (code execution, APIs,
   file I/O) as the action channel. The "disembodied chatbot" architecture
   appears in zero proposals - a notable consensus.
4. **Human-in-the-loop for irreversible actions.** 7 of 8 require explicit
   human approval for high-stakes actions (payments, deletion, external
   messaging). Only run03 (Oracle) proposes simulation-instead-of-approval,
   and even it keeps a discrepancy halt.
5. **Evaluation anchored on the same benchmarks.** GAIA, SWE-bench, WebArena
   appear across 6 proposals. The community has a de facto eval suite even
   without agreeing on architecture.

## Disagreements (genuine splits, not noise)

1. **Where does intelligence live?** run01 (memory substrate), run03 (world
   model), run05 (update rule), run06 (the environment/tooling), run08 (the
   base model). Five different answers - this is the deepest split in the
   packet and the most important open question.
2. **Explicit world model: yes or no?** run03 builds the architecture around
   one; run04 and run02 keep partial/perspectival models; run08 explicitly
   rejects the concept as premature. No middle ground emerged.
3. **Should the system change its own weights?** run05 says lifelong
   weight updates are the whole game; run01 and run08 freeze the base model
   and learn only in memory/adapters; run07 treats self-modification as the
   highest-privilege operation. This is really a disagreement about
   **where learning is safe to happen**.
4. **Single vs. multi-agent.** run02 and run07 (partially) bet on
   specialization and checks-and-balances; run05, run06, run08 insist one
   coherent mind is better. run01/run03/run04 are agnostic (single mind
   with internal modules).
5. **Safety: built-in vs. bolt-on vs. proof.** run04 demands mathematical
   proof obligations; run07 builds governance as the architecture; run03
   claims prediction quality IS safety; run08 claims simplicity IS safety.
   Four incompatible safety philosophies.

## Notable Ideas (worth stealing regardless of which architecture wins)

- **run01**: the memory controller as a learned policy (what to write /
  promote / evict) - applicable to any memory-using agent.
- **run02**: critic quorum from *different model families* to avoid
  correlated failures - cheap to add to any pipeline.
- **run03**: the discrepancy monitor (halt when reality diverges from
  simulation) - a safety mechanism that ports to any planning system.
- **run04**: the distillation bridge (repeated neural successes become
  symbolic rules) - a concrete path from opaque to auditable behavior.
- **run05**: the update ledger (signed log of every training batch per
  model version) - should be industry standard for any deployed learner.
- **run06**: file-based memory a human can read and edit - the most
  debuggable persistence story in the packet.
- **run07**: capability attenuation down a delegation chain - the cleanest
  answer to "how do subagents stay supervised."
- **run08**: the maintained trivial baseline with ablation discipline -
  a methodological contribution, not just an architecture.

## Headline Findings

1. The 8 proposals cluster into **three schools**: the *substrate school*
   (run01, run06 - intelligence lives in organized experience), the
   *model school* (run03, run05, run08 - intelligence lives in the model
   or its update rule), and the *organization school* (run02, run04, run07
   - intelligence lives in structure and checks).
2. **Nobody proposes scaling alone.** Even run08 (the minimalist) frames
   itself as a baseline to beat, not the final answer. The "just scale the
   transformer" position has no defenders left among these proposals.
3. **Safety thinking has matured**: proposals don't say "we'll add RLHF" -
   they specify mechanisms (proof obligations, capability budgets,
   simulation gates, compartmented memory). The conversation moved from
   values to mechanisms.
4. For Cognitive-OS planning specifically (see `synthesis.md`): the most
   actionable near-term combination is run06's file-based substrate +
   run04's verification layer for high-risk tools + run02's critic quorum
   pattern - all implementable with existing components.
