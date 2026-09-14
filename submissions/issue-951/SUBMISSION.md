# Issue #951 — Repair claim next-action mapper

**Bounty-plaza:** zhangjiayang6835-cyber/bounty-plaza#951  
**Upstream:** NSPG13/agent-bounties#1251

## Fix summary

Harden `scripts/next-agent-claim-action.mjs` to match the known-good reference in
`benchmarks/direct-v1/agent-loop/self-test.mjs` so it passes the precommitted
`claim-next-action` benchmark.

- Validate `claim-problem-v1` fields; reject with `claim_problem_invalid`
- Use `claim_response_schema_unsupported` for unknown schemas
- Validate candidate object (`claim_candidate_invalid`)
- Harden `authorization_ready` (params arity, non-empty typed data, replay shape)
- Strict `claimed` canonical event ID matching

## Verification

```bash
make test
make benchmark   # direct claim-next-action benchmark
make verify      # both
```

Benchmark (also exercised inside pytest):

```bash
node benchmarks/direct-v1/agent-loop/test.mjs claim-next-action .
node benchmarks/direct-v1/agent-loop/self-test.mjs
```

## Upstream submission

Admin: apply `scripts/next-agent-claim-action.mjs` to `NSPG13/agent-bounties` via
`scripts/auto_submit.py` (see `upstream.json`):

```bash
python scripts/auto_submit.py \
  --upstream NSPG13/agent-bounties \
  --target scripts/next-agent-claim-action.mjs \
  --code scripts/next-agent-claim-action.mjs \
  --branch fix/claim-next-action-mapper \
  --message "fix: harden claim next-action mapper to match known-good benchmark"
```

## Review

Branch diff vs `main`:

```bash
git diff main...HEAD
make verify
# or: submissions/issue-951/verify.sh
```

## Platform process

Comment `/claim` on bounty-plaza #951 before competing (24h lock). This PR does not
substitute for that platform step.
