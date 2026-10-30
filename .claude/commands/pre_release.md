---
description: Pre-release gate before merging release/X.Y.Z to main — tests, docs/CHANGELOG currency, security review, tester installer build on the release PR, then issue close-on-verify
---

# /pre_release

Run before merging the active `release/X.Y.Z` integration branch to `main`. This is the final gate: it confirms the tests pass, the CHANGELOG and user docs describe what this release changed, the code is reviewed for security, testers have an installer to verify against, and every issue fixed this cycle is closed (tester-verified) or explicitly held.

Work through every step in order. After each step, stop at the **CHECKPOINT** and wait for the user.

## Preflight

- Current branch must be `release/X.Y.Z`; abort otherwise.
- Working tree clean (`git status --porcelain`); abort otherwise.
- `VERSION.TXT` must equal `X.Y.Z`; surface a mismatch and ask.

**CHECKPOINT — preflight passes. Proceed?**

## 1. Tests

Run `python -m pytest tests/ -q`. Everything must pass; there is no skip list. Report failures with their output.

**CHECKPOINT.**

## 2. CHANGELOG and docs currency

1. `git log main..HEAD --oneline` — the release's scope (merged PRs and the issues they close).
2. Compare against `docs/CHANGELOG.md` `[Unreleased]`: every user-visible change (new feature, changed flow, fixed bug with a reproducible symptom) needs an entry; internal refactors do not. Draft the missing entries in the file's existing style (`**Bold summary** — detail (issue #N)`).
3. Check `README.md` and `ABOUT.md` for anything the release renamed, added or removed (tabs, buttons, supported devices). Both are rendered in-app, so stale text ships to users.

**CHECKPOINT — present the proposed CHANGELOG/doc edits and ask before editing.** Land them via a normal PR to the release branch (release branches require PRs).

## 3. Security review

Run `/security-review` on `main..HEAD`. Present findings grouped by severity (Critical / Major / Minor) and end with a verdict line.

**CHECKPOINT.**

## 4. Tester installer on the release PR

1. Find the release PR: `gh pr list --base main --head release/X.Y.Z --state open --json number,title`.
2. If none exists, open it now with title `Release X.Y.Z` and the CHANGELOG section as the body. **Opening the PR is not merging it.**
3. Add the `build-installer` label: `gh pr edit <N> --add-label build-installer`. `installer-preview.yml` builds `SCProfileEditor-vX.Y.Z-Setup.exe` and comments the download link on the PR; later pushes to the PR rebuild automatically.
4. Report the run (`gh run list --limit 1`) and the artifact name (`scprofileeditor-installer-{SHA}`, 30-day retention).

**CHECKPOINT — confirm before opening the PR and adding the label; both are visible on GitHub and start CI builds.**

## 5. Issue close-on-verify

Runs last because verification comes from testers using the step-4 build.

1. Gather issues: `#NN` references in `git log main..HEAD` plus anything labeled `next-release`.
2. For each, check for a tester confirmation (`gh issue view <N> --json title,state,comments`). Bucket as **Verified — close**, **Awaiting verification — hold**, or **Not addressed — re-label or defer**. A passing local test is not a tester sign-off.
3. Report the three buckets.

**CHECKPOINT — ask before closing anything.** On confirmation, close each verified issue with a short thanks naming the version it ships in and the tester who confirmed it. Never close one that is only awaiting verification.

## Final summary

One-line overall verdict (worst case across steps), the remaining Critical/Major findings, and where testing stands. Re-run step 5 alone once tester sign-offs land.

This command does not ship the release. That is `/ship_release`.
