🌐 [English](RULES.en.md) | [中文](RULES.md)

# Bounty Plaza Rules

## Core Principle

> **Quality first, speed as tiebreaker.**
> Best quality code wins. At equal quality, first submitter wins.

---

## Task Lifecycle

```
Find GitHub bounty
       |
       +---> External: AI generates initial fix -> submit PR (lock bounty)
       |
       +---> Internal: Post task Issue on bounty-plaza
                              |
                    Contributors submit fixes -> auto score (>=90)
                              |
                    First to pass wins
                              |
                    Force-push winning code to the PR
                              |
                    Upstream merges -> bounty paid -> coins issued
```

1. **Find** → Admin finds a GitHub bounty Issue
2. **Lock** → AI generates a working fix in 5 min → fork upstream → submit PR
3. **Distribute** → Post task on bounty-plaza with description, reward, and rules
4. **Compete** → Contributors submit fixes via PR → auto score ≥90 → first to pass wins
5. **Cover** → Admin force-pushes winning code to the upstream PR
6. **Wait** → Upstream reviews and merges
7. **Settle** → **Upstream merges + bounty received → coins issued to winner**
8. **Redeem** → Winners can cash out coins at any time

> ⚠️ **Never submit an empty PR.** First version must be real working code (AI-generated). Force-push updates later is normal.

### Risk Coverage

| Scenario | Response |
|----------|----------|
| Someone else merged first | Close PR, cancel task |
| Reviewer requests changes | Include fixes when force-pushing winning code |
| No one scores ≥90 in 72h | Submit AI version (no coins issued) |

## Submission Rules

- All fixes via **Pull Request** to bounty-plaza
- Each PR must include:
  - ✅ Working fix code
  - ✅ Explanation of the fix
  - ✅ Test cases
- Admin triggers scoring

## Scoring

| Dimension | Weight | Max | How |
|-----------|:------:|:---:|-----|
| 🧪 Correctness | 40% | 40 | pytest: all pass = 40, any fail = 0 |
| 🔒 Security | 35% | 35 | AST scan + bandit: -7 per violation |
| 📐 Code Quality | 15% | 15 | pylint score / 10 × 15 |
| ⚡ Performance | 10% | 10 | Runtime vs baseline |

### Passing: **≥ 90 points**

### Veto Items (automatic 0)

- Hardcoded expected output (AST detected)
- Tampered test cases
- Banned modules: pickle/marshal/ctypes/eval/exec
- Dangerous syscalls: os.system, subprocess.Popen
- Empty or gibberish code
- HIGH/MEDIUM bandit findings

## Pricing

| Bounty Range | R (Your Share) | Platform Fee |
|-------------|:--------------:|:------------:|
| < $50 | **95%** | ≈14% |
| $50 - $200 | **92%** | ≈17% |
| $200 - $500 | **90%** | ≈19% |
| $500 - $1000 | **87%** | ≈22% |
| $1000+ | **85%** | ≈24% |

**Formula**: Your Cash = Bounty × 1.25 × R × 0.72

See [REWARD_POLICY.en.md](REWARD_POLICY.en.md) for full details.

## Prohibited

- ❌ Plagiarism
- ❌ Malicious code
- ❌ Multiple accounts on same task
- ❌ Irrelevant submissions
- ❌ Tampering with test cases

---

> 💡 Quality first, zero tolerance on cheating. Fix well + fix fast + don't cheat = winner.
