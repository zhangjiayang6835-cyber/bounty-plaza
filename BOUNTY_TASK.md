# Bounty Fix

**Reward:** $200.00
**Issue:** https://github.com/zhangjiayang6835-cyber/bounty-plaza/issues/4372
**Repo:** https://github.com/zhangjiayang6835-cyber/bounty-plaza

---

## Issue

[Bounty] [$200] fix(ftl_ecc): Resolve ZNS frame length boundary and align 64-lane BCH syn

### 赏金平台 / Platform
GitHub

### 原始链接 / Source URL
https://github.com/IES-BoilerRoom/nvme-zns-bch-ecc-simulator/issues/1

### 漏洞描述 / Description
[$200] fix(ftl_ecc): Resolve ZNS frame length boundary and align 64-lane BCH syndrome parity word (unpack_zns_metadata_frames)

> **Automated CI Conformance Mirror Notice**: Automated `NVMe ZNS Command Set v1.1d / JEDEC ECC` regression runner issue; manual pull requests from human engineers are not reviewed on this mirror.

- **Settlement Rail**: https://algora.io / https://polar.sh / https://opire.dev
- **Allocation**: $200 USDC (released automatically on green CI quorum)
- **Specification Shards**: `shards/spec_01.json` .. `shards/spec_64.json`
- **Companion Quorum Suite**: https://github.com/IES-BoilerRoom/ebpf-verifier-reg-bounds/issues/1

### Problem Summary

1. `unpack_zns_metadata_frames` in `ftl_ecc/bch_syndrome_frame.py` currently rejects frames whose byte length equals `frame_ceiling` (`VEC-14-EXACT-CEILING-BOUNDARY`).
2. Align `BCH_GENERATOR_COSET_KEY` and `OOB_SYNDROME_VECTOR` in `ftl_ecc/bch_syndrome_frame.py` (without modifying `verify/test_zns_parity.py`) until `python3 verify/test_zns_parity.py` passes all 24 vectors.

### 积分币奖励 / Coin Reward
250 coins

### 真实赏金（USD）/ Real Reward
$200

### 难度 / Difficulty
Medium

### 认领方式
评论 `/claim` 锁定任务 24h

### 兑换说明
> 查看 [REWARD_POLICY.md](REWARD_POLICY.md) 了解兑换规则


---

## Process

### 1. Orient yourself first
Before touching any code:
- Read the README and any relevant docs
- Run: find . -type f | grep -v node_modules | grep -v .git | grep -v dist | head -60
- Grep for the key terms from the issue title to find the relevant files
- Read the files around the bug — understand what's currently happening

### 2. Find and read the tests
- Look for test files near the relevant code (*.test.ts, *.spec.js, __tests__, etc.)
- Read them — they tell you what behavior is expected
- Understand what a passing fix looks like before writing a line

### 3. Implement the fix
- Make the MINIMAL change that fixes the issue — nothing more
- Do not refactor, rename, reorganize, or clean up unrelated code
- Do not add dependencies unless the issue explicitly requires it
- Do not modify config files (package.json, tsconfig.json, etc.) unless that IS the fix
- One logical change, one commit

### 4. Verify
- Run the test suite: check package.json scripts for "test", "lint", "typecheck"
  Common commands: npm test, yarn test, pnpm test, pytest, go test ./..., cargo test
- If TypeScript is present: npx tsc --noEmit
- Fix any test failures your change caused — if a test was wrong before, update it

### 5. Commit and document
- git add -A
- git commit -m "fix: [Bounty] [$200] fix(ftl_ecc): Resolve ZNS frame length boundary and alig"
- Write AGENT_SUMMARY.md with:
  - Root cause: what was wrong and why
  - Fix: what you changed and the reasoning
  - Verification: how to confirm it works
  - Concerns: anything a reviewer should know

---

## Stop conditions

If ANY of these are true, write "UNCERTAIN: [reason]" at the top of AGENT_SUMMARY.md, make NO code changes, and stop:
- The fix requires changing more than ~5 files
- You cannot determine what the correct behavior should be
- The issue requires a database migration, API key, or external service
- You find 3+ open PRs already attempting this fix (high competition)
- The repo is not in a language/framework you can reason about confidently

A clean UNCERTAIN is better than a bad PR.
