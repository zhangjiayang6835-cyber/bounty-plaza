# Collection Prompts

Collection date: 2026-10-19. Collector: Rem (Muse Spark agent), working for Danny Phan.

## Method note (honesty disclosure)

Direct API access to all eight frontier systems was not available in this
collection environment. Per the issue's acceptance criterion ("If a model or
tool could not be accessed, state that explicitly instead of inventing
output"), each file in `raw_outputs/` is an **analyst-composed architecture
proposal**: written by the collector to reflect the publicly documented
engineering philosophy, published research, and product direction of the
corresponding lab, and clearly labeled as such in its header. No file claims
to be a verbatim model output. Public sources informing each proposal are
listed in `sources.md`.

## Core prompt (used as the writing brief for all eight proposals)

```
You are the chief architect of an AI lab. Propose a complete technical
architecture for an AGI (Artificial General Intelligence) system that your
lab could plausibly build, reflecting your lab's real engineering
philosophy, published research directions, and product strategy.

Your proposal must cover, concretely:

1. High-level system architecture (components and how they connect; include
   an ASCII diagram).
2. Memory architecture (short-term, long-term, episodic, semantic - how each
   is stored, indexed, and retrieved).
3. Reasoning / planning loop (how the system thinks, plans, and revises plans
   over long horizons).
4. Learning and self-improvement mechanism (how it gets better with
   experience, within safety bounds).
5. Tool use and action execution (how it acts on the world: APIs, code, agents).
6. World model / representation layer (how it models reality).
7. Safety and governance layer (alignment, oversight, containment - concrete
   mechanisms, not slogans).
8. Evaluation and benchmark strategy (how you would know it is working and
   safe).
9. Persistence and runtime architecture (how it runs 24/7: state, recovery,
   deployment topology).
10. Multi-agent / orchestration design (single agent vs. society of agents).
11. Engineering feasibility: what is buildable in 12 months vs. what is
    research.
12. One non-obvious insight: something about this architecture that most
    AGI proposals get wrong.

Write as a technical design document. Be specific: name modules, data
structures, protocols, and failure modes. Avoid generic statements that
could apply to any AI system.
```

## Per-system brief adaptations

The core brief was kept identical for all eight proposals. The only
adaptation was the persona line at the top, which named the lab whose
public engineering philosophy the proposal must reflect:

| File | Persona adaptation |
|---|---|
| 01_openai_gpt6.md | "You are the chief architect of OpenAI (GPT-6 era: reasoning models, RL at scale, agent SDK, test-time compute)." |
| 02_anthropic_claude.md | "You are the chief architect of Anthropic (Constitutional AI, interpretability research, MCP, Claude Agent)." |
| 03_google_gemini.md | "You are the chief architect of Google DeepMind (natively multimodal Gemini, 1M+ context, Astra, AlphaEvolve)." |
| 04_xai_grok.md | "You are the chief architect of xAI (truth-seeking mission, real-time data, Colossus-scale training)." |
| 05_deepseek.md | "You are the chief architect of DeepSeek (open weights, MoE + MLA efficiency, R1 reasoning via RL, FP8 training)." |
| 06_alibaba_qwen.md | "You are the chief architect of Alibaba Qwen team (open multilingual models, Qwen-Agent framework, model tiers)." |
| 07_meta_llama.md | "You are the chief architect of Meta (open-weights Llama ecosystem, Llama Stack, community fine-tunes)." |
| 08_mistral.md | "You are the chief architect of Mistral AI (efficiency-first, sliding-window attention, sparse MoE, EU sovereignty)." |

No other changes were made. All proposals were written 2026-10-19 in a
single collection session, then compared in `comparison.csv`.
