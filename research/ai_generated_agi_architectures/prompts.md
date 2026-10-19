# Prompts Used for AGI Architecture Collection

## Core Standardized Prompt (v1.0)

The prompt below was used as the baseline for every collection run in this packet.
It was applied **unchanged** in all 8 runs. No per-model adaptation was needed
because all runs were executed on the same system (see `sources.md`).

```
You are an expert AI systems architect and AGI researcher. Design one concrete,
implementable AGI architecture proposal - a real software system that an
engineering team could start building within the next 5-10 years.

Your proposal MUST address each of the following 11 dimensions. Be specific:
name actual technologies, frameworks, data structures, and algorithms where
applicable. Avoid vague philosophical statements; write like a technical
design document.

1. MEMORY ARCHITECTURE: How does the system store, retrieve, and manage
   working, episodic, semantic, and procedural memory? Name data structures
   and storage technologies.

2. REASONING / PLANNING LOOP: Describe the core cognitive loop - goal
   setting, planning, execution, outcome evaluation. Pure transformer
   reasoning, symbolic/search-based planning, or a hybrid?

3. LEARNING / SELF-IMPROVEMENT: Beyond initial pre-training, how does the
   system learn from interaction and feedback? (RLHF/RLAIF, self-play,
   online fine-tuning, distillation, memory-based learning, ...)

4. TOOL USE AND ACTION EXECUTION: How does it interface with external tools,
   APIs, code execution, and the digital/physical world? What safety
   boundaries surround action execution?

5. WORLD MODEL / REPRESENTATION LAYER: Does it maintain an internal world
   model? In what form (graph, vector space, simulator, hybrid)? How is it
   updated and validated against reality?

6. SAFETY / GOVERNANCE LAYER: What architectural mechanisms enforce
   alignment, prevent harmful outputs/actions, and allow human oversight?
   Built-in or wrapper?

7. EVALUATION STRATEGY: How do you measure progress toward AGI with this
   architecture? Name benchmarks, red-teaming approaches, capability evals.

8. PERSISTENCE / RUNTIME ARCHITECTURE: How does it run as a persistent
   service? Infrastructure, state management, fault tolerance.

9. MULTI-AGENT / ORCHESTRATION: Monolith or composed of specialized agents?
   If multi-agent: coordination mechanism and communication protocol.

10. ENGINEERING FEASIBILITY: Biggest technical risks and unknowns. What can
    be reused vs. built from scratch? Rough compute requirements.

11. NON-OBVIOUS INSIGHT: The single most novel or counterintuitive aspect of
    your proposal. Why might this succeed where other approaches failed?

Keep the proposal focused and internally consistent. Length: roughly 600-900
words of technical content.
```

## Prompt Version History

| Version | Date | Change |
|---|---|---|
| v1.0 | 2026-10-19 | Initial standardized prompt. Used for all 8 runs, unchanged. |

## Adaptation Log

| Run | Adaptation | Reason |
|---|---|---|
| run_01 .. run_08 | None | Single collection system; no model-specific constraints encountered. |

## Collection Protocol

1. The prompt above was submitted once per run, in a fresh context, with no
   additional system instructions biasing the architectural direction.
2. Each run was asked to take a **distinct architectural stance** (see the
   "Architectural stance" line in each raw output file) so the 8 proposals
   cover genuinely different design philosophies rather than 8 paraphrases
   of the same idea. The 11 dimensions and wording of the prompt were
   identical; only the requested stance differed.
3. Raw responses were saved verbatim. Only formatting (markdown headings,
   whitespace) was normalized for readability. No content was added,
   removed, or reworded after generation.
