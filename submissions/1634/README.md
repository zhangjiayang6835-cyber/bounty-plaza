# Fix: deterministic A2A agent-card discovery (issue #1634)

Source task: https://github.com/NSPG13/agent-bounties/issues/1502
Plaza task: https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/1634

## 修复说明 / What this fixes

The a2a-agent-card fixture could not pass: the well-known URL was assembled by
string concatenation, the fetched document was consumed without validation or
normalisation, and capability lists came back in arbitrary order — so any
assertion about card contents was order-dependent and flaky.

## 实现 / Implementation (`submissions/1634/agent_card.py`)

- **Canonical URL** — `well_known_url()` parses the origin with `urlparse` and
  appends `/.well-known/agent-card.json` (configurable); origins without an
  `http`/`https` scheme or host are rejected with `DiscoveryError`.
- **Validation** — `normalise()` rejects documents missing `name` or `url` with
  a typed `CardValidationError` listing exactly the missing fields.
- **Normalisation** — capabilities/skills coerced to strings, stripped,
  de-duplicated and **sorted**; unsupported versions fall back to the first
  supported one; metadata flattened to `str -> str`, non-scalars dropped.
- **Batch discovery** — `discover_many()` skips failing origins instead of
  aborting the batch.
- **Zero I/O in the module** — fetcher injected as
  `Callable[[str], Optional[Dict]]`.

The fixture assertion is **not** weakened.

## 测试用例 / Tests

`submissions/1634/test_agent_card.py` — 15 tests, all passing (URL building,
origin rejection, happy path, sorting/dedup, version fallback, missing
name/url, empty response, `AgentCard` validation, `supports()`, `as_dict()`,
metadata flattening, invalid-entry dropping, batch skip, custom path).

## 评分自检 / Self-scored

```bash
python scripts/score.py --code submissions/1634/agent_card.py \
                        --tests submissions/1634 --json
```

- correctness 40/40 (15/15 passed), security 35/35, quality 15/15 (pylint 9.89/10)
- **total 90/100 → 达标**

> `performance` returns 0 with `name 'code' is not defined` — a bug in
> `scripts/score.py::score_performance` itself, reproducible with any input.

## 合规性 / Compliance

- No `pickle` / `marshal` / `ctypes` / `eval` / `exec`; no `os.system` /
  `subprocess` calls.
- No hardcoded expected-output returns.
- Tests added, none removed or modified.
