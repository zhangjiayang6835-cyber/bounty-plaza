# Sources

## Collection provenance

- **Collector:** Rem (Muse Spark agent), working for Danny Phan.
- **Collection date:** 2026-10-19 (single session).
- **Access method:** analyst-composed proposals. Direct API access to the
  eight frontier systems was not available; per the issue's acceptance
  criterion on fabrication, each `raw_outputs/` file is labeled as an
  analyst reconstruction grounded in the lab's public engineering record,
  not a verbatim model output.
- **Human edits:** the collector wrote all files directly; no model
  outputs were pasted. Minor copy-editing for consistency was performed
  by the collector during the comparison pass.

## Model/family names used (verified real, October 2026)

All eight families and representative flagship names below were verified
against public reporting dated October 2026 (accessed 2026-10-19):

| Family | Representative models (Oct 2026) | Verification source |
|---|---|---|
| OpenAI | GPT-6 Astra, GPT-6 Sol/Luna, GPT-6.1 Sol | Artificial Analysis / dev-tool rankings, Oct 2026 |
| Anthropic | Claude Opus 5.5, Sonnet 5.5, Haiku 5.5, Fable 5.1 | Artificial Analysis Intelligence Index v4.3.2, Oct 2026 |
| Google DeepMind | Gemini 4 Argon, Gemini 3.8 Flash | October 2026 AI model update roundups |
| xAI | Grok 4.7 | Artificial Analysis / dev-tool rankings, Oct 2026 |
| DeepSeek | DeepSeek V4 Pro (open weights) | Artificial Analysis / dev-tool rankings, Oct 2026 |
| Alibaba | Qwen 3.8 Max (Qwen3.8-Flash-Next preview) | Local AI Zone, Oct 2026 (Qwen 4 not yet released as of 2026-10-18) |
| Meta | Llama 4 Maverick; "Muse Wonder" (closed) | Dev-tool rankings / AI press, Oct 2026 |
| Mistral AI | Mistral Large 4 (preview, weights due Oct 2026) | AI Digest 2026-10-09; Reuters via press |

Source URLs (exact, from search results 2026-10-19):
- https://chierhu.medium.com/llm-model-wars-are-becoming-an-enterprise-platform-war-7c315540a9bb
- https://blog.logrocket.com/ai-dev-tool-power-rankings/
- https://local-ai-zone.github.io/blog/October_2026_AI_Model_Updates.html
- https://ai.blocksize.hr/blog/en/ai-digest-october-9-2026.html
- https://startuprise.co.uk/top-ai-models-in-the-world-in-2026-best-ai-models-for-work-coding-and-research/

## Public engineering record informing each proposal

These are the well-established public facts about each lab's direction
that the proposals reconstruct. They are stated here so any reviewer can
check the grounding without trusting the collector's memory:

- **OpenAI:** RL-trained reasoning models (o-series onward); test-time
  compute scaling as a public research theme; Agents SDK and multi-agent
  swarm products; eval-driven development with published system cards.
- **Anthropic:** Constitutional AI (public paper and constitution);
  mechanistic interpretability research program; Model Context Protocol
  (MCP) as an open standard; Claude Agent with computer use.
- **Google DeepMind:** natively multimodal Gemini training; million-token
  context windows; Project Astra universal agent demos; AlphaEvolve
  self-improving system publications; frontier safety framework.
- **xAI:** public "maximum truth-seeking" mission; real-time data
  integration products; Colossus training cluster (publicly reported).
- **DeepSeek:** open-weight releases; DeepSeekMoE architecture;
  Multi-head Latent Attention (MLA); FP8 mixed-precision training;
  DeepSeek-R1 reasoning via reinforcement learning (public report).
- **Alibaba Qwen:** open model tiers (0.5B through Max); Qwen-Agent
  framework (public repo); strong multilingual evaluation results.
- **Meta:** open-weights Llama releases; Llama Stack (public project)
  for interoperable components; large community fine-tune ecosystem.
- **Mistral AI:** sliding-window attention and sparse MoE (Mixtral
  lineage, public); efficiency positioning; EU sovereignty messaging;
  Large 4 preview October 2026.

## What was NOT verified

- The actual internal architectures of any lab's current models
  (proprietary; proposals reconstruct philosophy, not internals).
- Whether any maintainer or platform will pay the advertised bounty
  (see REVIEW.md step 0 - funding unverified, maintainer unresponsive
  since 2026-04-30).
- Benchmark figures and cost numbers (deliberately omitted from the
  packet rather than estimated).
