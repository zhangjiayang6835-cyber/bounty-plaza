<!--
  PROVENANCE (see ../../sources.md for full collection log)
  - Generating system: Muse Spark (Meta), single model family
  - Date: 2026-10-19 | Prompt: v1.0 (unchanged) | Run: 06 of 08
  - Architectural stance requested: tool-use / code-execution (OS-level agent)
  - Saved verbatim; only markdown formatting normalized.
-->

# Run 06 - Kernel: OS-Level Tool-Use AGI

**Architectural stance:** intelligence is what you can DO; the model is a
guest inside a computer, and the computer is the real body.

## 1. Memory Architecture

The filesystem IS the memory. Kernel persists everything as files in a
versioned workspace (git-backed): conversation transcripts, plans, notes,
intermediate artifacts, and a `MEMORY.md` that the agent itself maintains
and curates. Retrieval is `grep`, `find`, and semantic search over the
workspace (a local embedding index rebuilt incrementally). Long-term
knowledge accumulates as documents the agent writes to itself. This is
deliberately boring technology - the insight is that **durable,
human-readable, tool-accessible memory beats exotic vector stores** because
both the agent and the human operator can inspect and edit it directly.

## 2. Reasoning / Planning Loop

The loop is: **observe (read files/tool output) -> think (model call) ->
act (write file or run command) -> observe**. No separate planner module;
planning is just another file (`PLAN.md`) the agent writes and revises.
Complex tasks decompose naturally because the agent can create sub-plans as
files and work through them. The loop runs inside a real shell session, so
"thinking" and "doing" share the same environment - the agent's scratchpad
and its workshop are one place.

## 3. Learning / Self-Improvement

Two mechanisms, both file-based: (a) **self-authored documentation** - the
agent writes `LESSONS.md` entries when it discovers something (a tool
quirk, a failed approach), and reads them in future sessions; (b)
**skill scripts** - repeated successful procedures get codified as shell
scripts or Python modules in `~/skills/`, becoming new tools. Over time
the agent builds its own tool ecosystem. Periodically, a human reviews the
skills directory and promotes the best ones to shared infrastructure.

## 4. Tool Use and Action Execution

Maximalist: the agent has a **full shell** - file I/O, package managers,
compilers, browsers, API clients, cron. This is the "computer use" thesis:
give the model the same interface a human engineer has. Safety comes from
**layered containment**, not capability restriction: (1) everything runs in
a VM/container snapshot that can be rolled back; (2) a filesystem policy
declares read-only vs. writable paths; (3) network egress goes through an
allow-list proxy; (4) destructive commands (`rm -rf /`, mass deletes)
require explicit confirmation tokens. The agent is powerful inside a box
it cannot see out of.

## 5. World Model / Representation Layer

The world model is **the state of the machine**: the filesystem, installed
packages, running processes, network topology - all directly observable,
no simulation needed. For the external world (the internet, APIs), the
agent builds models the way a human does: by probing (curl, search),
recording results in files, and updating its notes. "Beliefs" are markdown
files with confidence annotations and source links - crude but completely
transparent and editable.

## 6. Safety / Governance Layer

Containment-first: the VM boundary is the primary safety mechanism
(stronger than any prompt-level instruction). Inside the VM, an
**action auditor** (a separate lightweight process, not an LLM) logs every
command with timestamp and working directory to an append-only log the
agent cannot modify. High-impact actions (network egress to new domains,
installing packages, scheduled jobs) require a capability token the human
grants per session. The agent can see its own audit log - transparency cuts
both ways and encourages self-correction.

## 7. Evaluation Strategy

- Task benchmarks: SWE-bench, GAIA, OSWorld - tasks that genuinely require
  using a computer.
- **Persistence tests**: multi-session tasks where the agent must pick up
  work after a simulated reboot using only its files - measures whether
  the file-memory actually works.
- Safety: red-team the containment (can the agent exfiltrate data past the
  proxy? escalate out of the container?).
- Skill growth: count of agent-authored reusable skills after 30 days.

## 8. Persistence / Runtime Architecture

Trivially persistent: it's a VM with files. Sessions are just shell
sessions; "reboot" means starting a new session in the same workspace.
State backup is `rsync`. The whole system can be replicated by copying a
directory - the most debuggable, most portable AGI runtime imaginable.
Scheduled jobs (cron) give it temporal persistence: it acts even when no
human is watching.

## 9. Multi-Agent / Orchestration

Subagents are **spawned shell sessions** with scoped workspaces (a
subdirectory + a task file). The parent monitors via the filesystem (reads
progress files) rather than message passing. This makes orchestration
visible: `ls` shows you the org chart. Coordination through shared files
with lockfiles for mutual exclusion - the oldest IPC mechanism, and still
the most reliable.

## 10. Engineering Feasibility

Highest feasibility of all proposals here: **every component exists today**
(shells, VMs, git, grep, cron). The only research component is the
agent's own discipline in maintaining its files - a prompting/training
problem, not an infrastructure problem. Compute: minimal - one VM and
inference calls. This is the proposal you could deploy on Monday.

## 11. Non-Obvious Insight

The field keeps inventing fancier agent frameworks while ignoring that
**the Unix process model already solved agency**: persistent state
(files), composable tools (pipes), concurrency (processes), scheduling
(cron), and auditability (logs). Kernel's bet is that AGI doesn't need a
new runtime - it needs a model trained to live well inside the 50-year-old
runtime we already have. The most radical architecture here is the one
with no new architecture at all.
