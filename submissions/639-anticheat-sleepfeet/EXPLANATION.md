# Fix for Bounty Plaza #639 — Anti-Cheat / Sleepfeet

## Upstream

- Issue: https://github.com/Iamgoofball/-tg-station/issues/138
- PR: https://github.com/Iamgoofball/-tg-station/pull/142

## What was wrong

Cheaters were using wallhacks, aimbots, autoclickers, and automation of the
**sleepfeet** pattern (sending move/click input while asleep or knocked out).
Wallhacks are mostly client-side; the actionable server-side gaps were missing
detection/hard-blocks for sleepfeet automation and weak escalation for
aimbot/autoclick signals.

## What we changed

1. **Sleepfeet** — hard-block `client/Move` and `Click` while sleeping/knocked
   out (unless `TRAIT_SLEEPIMMUNE`), escalate to admins after spam thresholds,
   write a system note.
2. **Aimbot** — escalate strong middle-drag → left-click hits even when the
   minute click cap is not hit.
3. **Autoclick** — escalate repeated per-second click-limit trips.
4. Keep existing BYOND build blacklist for wallhack-prone clients.

## Layout

| Path | Purpose |
|------|---------|
| `anticheat.py` | Python reference of the heuristics (Plaza scoring) |
| `tests/test_anticheat.py` | pytest coverage |
| `patch/anticheat.dm` | DreamMaker module |
| `patch/upstream.patch` | Full diff for `Iamgoofball/-tg-station` |

## How to verify

```bash
cd submissions/639-anticheat-sleepfeet
PYTHONPATH=. pytest -q tests/
```
