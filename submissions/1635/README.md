# Fix: deterministic RPC failover regression (issue #1635)

Source task: https://github.com/NSPG13/agent-bounties/issues/1500
Plaza task: https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/1635

## 问题描述 / Problem

The rpc-failover fixture fails because the client had no deterministic
behaviour: endpoint selection depended on dict ordering, there was no attempt
budget, and a failing endpoint was retried forever instead of being taken out
of rotation. Any test asserting "endpoint B serves the request after endpoint A
fails" was flaky or impossible to express.

## 修复方案 / Fix

`rpc_failover.py` implements a small, dependency-free failover client:

- **Stable ordering** — candidates are sorted by `(priority desc, url)`, so the
  same input always yields the same route. No reliance on dict/set order.
- **Attempt budget** — `FailoverPolicy.max_attempts` caps how many transport
  calls a single `send()` may make.
- **Deterministic circuit breaker** — after `failure_threshold` consecutive
  failures an endpoint enters cooldown for `cooldown_ticks`. Cooldown is driven
  by an injectable `clock` callable, so tests advance time without sleeping.
- **Typed errors** — `AllEndpointsFailedError` carries the ordered attempt
  trail (`url: reason`), which is what the fixture asserts on.
- **No I/O in the module** — the transport is injected as
  `Callable[[str, str], TransportResult]`, so the whole thing is testable
  without network access.

The fixture assertion is **not** weakened: it still requires the request to be
served by the next healthy endpoint and still requires the failure trail to be
reported.

## 测试用例 / Tests

`test_failover.py` — 15 tests, all passing:

| Area | Cases |
|------|-------|
| Validation | empty url / bad weight / bad policy / empty endpoint list |
| Happy path | first endpoint serves; values propagated |
| Failover | primary fails → next candidate serves |
| Exhaustion | all endpoints fail → `AllEndpointsFailedError` with trail |
| Budget | never exceeds `max_attempts` calls |
| Circuit breaker | opens after threshold; expires after cooldown; reset on success |
| Ordering | stable priority ordering |
| Observability | `snapshot()` counters; no-available-endpoint case |

## 评分自检 / Self-scored

Run with the repo's own scorer:

```bash
pip install pytest pylint bandit
python scripts/score.py --code submissions/1635/rpc_failover.py \
                        --tests submissions/1635 --json
```

Result on our side:

- correctness 40/40 (15/15 passed)
- security 35/35 (no violations; no `eval`/`exec`/`subprocess`/`os.system`)
- quality 15/15 (pylint 10.00/10)
- **total 90/100 → 达标**

> Note: the `performance` dimension reports `0` with
> `执行失败: name 'code' is not defined`. That is a bug in
> `scripts/score.py::score_performance` itself (it reads a `code` variable that
> does not exist in that scope), not in this submission — it reproduces with
> any input file. Happy to send a one-line fix for the scorer separately.

## 合规性 / Compliance

- No `pickle` / `marshal` / `ctypes` / `eval` / `exec`.
- No `os.system` / `subprocess` calls.
- No hardcoded expected-output returns; every result is computed from inputs.
- Tests were added, not modified or removed.
