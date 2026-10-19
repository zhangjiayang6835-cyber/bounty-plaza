# Sources - Model Names, Providers, Access Dates, Provenance

## Collection Summary (honest disclosure)

- **Generating system for all 8 runs: Muse Spark (Meta)** - a single model
  family. This packet therefore does NOT yet satisfy the "at least 8
  distinct AI systems or model families" criterion in the strict sense.
- What it DOES satisfy: 8 independent proposals generated with an identical
  standardized prompt (v1.0, see `prompts.md`), each from a distinct
  requested architectural stance, saved verbatim, fully traceable below.
- The packet is structured so that additional providers' outputs can be
  appended under `raw_outputs/` without reformatting; `comparison.csv`
  accepts new rows, and this file accepts new provenance blocks.

## Per-Run Provenance

| Run | File | Model | Provider | Access date (UTC) | Method | Human edits |
|---|---|---|---|---|---|---|
| 01 | `raw_outputs/muse_spark_run01_hierarchical_memory.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: memory-centric hierarchical | Formatting only (headings/whitespace) |
| 02 | `raw_outputs/muse_spark_run02_swarm_orchestration.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: multi-agent swarm | Formatting only |
| 03 | `raw_outputs/muse_spark_run03_predictive_worldmodel.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: predictive world-model | Formatting only |
| 04 | `raw_outputs/muse_spark_run04_neurosymbolic_hybrid.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: neuro-symbolic hybrid | Formatting only |
| 05 | `raw_outputs/muse_spark_run05_continual_learning.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: continual learning | Formatting only |
| 06 | `raw_outputs/muse_spark_run06_os_level_tooluse.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: OS-level tool use | Formatting only |
| 07 | `raw_outputs/muse_spark_run07_safety_first_governance.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: safety-first governance | Formatting only |
| 08 | `raw_outputs/muse_spark_run08_minimalist_retrieval.md` | Muse Spark | Meta | 2026-10-19 | Direct generation, prompt v1.0, stance: minimalist retrieval | Formatting only |

## Generation Settings

- Temperature / sampling: provider defaults (no custom tuning applied).
- Max output: not constrained; proposals landed at ~600-900 words each.
- Context: each run executed in a fresh context with no additional system
  instructions biasing architectural direction, beyond the requested
  stance noted above.
- No outputs were fabricated from training knowledge about other models;
  no file in `raw_outputs/` is attributed to a system that did not
  generate it.

## Known Limitations

1. **Single provider.** Extending to 8 distinct providers requires API or
   web access to additional systems, which was not available in this
   collection session. This is the packet's main gap against the bounty
   criteria and is stated here explicitly rather than hidden.
2. **Stance prompting.** The 8 proposals differ by requested architectural
   stance, not by model inductive bias. A multi-provider collection would
   add genuine model-diversity signal on top.
3. **No independent verification of "rawness".** The verbatim claim rests
   on the collector's (my) procedure log above; there are no API receipts.
   A future collection run should retain request/response IDs.

## Links

- Bounty (mirror): https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/477
- Upstream mirror: https://github.com/Vikingr2023/awesome-agent-bounties/issues/167
- Original bounty: https://github.com/aLexzzz430/Cognitive-OS/issues/5
- Prompt used: `prompts.md` (v1.0) in this directory
