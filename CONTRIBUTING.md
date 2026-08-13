# Contributing to Bounty Plaza (赏金广场)

Thanks for wanting to contribute! Bounty Plaza aggregates real bounty tasks;
completed fixes earn points redeemable for cash (see `REWARD_POLICY.md` / `REWARD_POLICY.en.md`).

## Getting started

1. **Fork** this repository and clone your fork.
2. Pick an open bounty from the issue tracker (look for the `bounty` label and its USD reward).
3. Read `RULES.md` / `RULES.en.md` for submission rules and `REWARD_POLICY.md` for payout tiers.

## Submitting a fix

1. Create a branch from the default branch: `git checkout -b fix/<issue-number>-<short-desc>`.
2. Make your change and add a clear, self-contained solution file (e.g. `fix_<topic>.py`).
3. Include a short `SOLUTION_<n>.md` describing: the vulnerability, the fix, and how to verify it.
4. Add tests where the bounty requires them.
5. Open a PR against the default branch with `Fixes #<n>` in the description so it links to the bounty issue.

## Style

- Keep solutions dependency-light unless the bounty says otherwise.
- Do not bundle unrelated bounties into one PR — one PR per issue.
- Document any assumptions or environment requirements in your `SOLUTION_<n>.md`.

## Review & payout

Maintainers review each PR. On merge, points are credited according to `REWARD_POLICY.md`.
If a PR is closed without merge, address the review feedback and re-submit rather than opening duplicates.
