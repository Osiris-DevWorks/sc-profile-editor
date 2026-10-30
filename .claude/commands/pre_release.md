---
description: Pre-release sanity check before merging release/X.Y.Z to main — test coverage, docs sync, standards, security review, contributor + tester acknowledgement audit, tester installer build on the release PR, then issue close-on-verify
---

# /pre_release

Run before merging the active `release/X.Y.Z` integration branch to `main`. This is the final gate before the release ships — it confirms code quality, doc currency, test coverage, that every code contributor and tester is acknowledged in `ABOUT.md`, that testers have an installer to verify against, and that every issue fixed this cycle is closed (tester-verified) or explicitly held.

Mirrors smart-citizen's `/pre_release`. Three of its steps do not apply here and are omitted on purpose: the language coverage check (SCPE has no translations), the in-app Test Plan panel refresh (SCPE has no such panel), and the portable build (SCPE has no portable mode).

Work through every step in order. After each step, stop at the **CHECKPOINT** and wait for the user before continuing.

## Preflight

- Confirm the current branch is `release/X.Y.Z`. If not, abort and ask the user to switch.
- Confirm the working tree is clean (`git status --porcelain`). If dirty, abort.
- Confirm `VERSION.TXT` matches `X.Y.Z`. If mismatched, surface the discrepancy and ask before proceeding.

**CHECKPOINT — preflight confirms release branch is ready for audit. Proceed?** Wait for the user.

## 1. Test coverage check

Follow `.claude/commands/test_coverage_check.md`. Present findings grouped by severity (Critical / Major / Minor) and end with the verdict line.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 2. Docs sync check

Follow `.claude/commands/docs_sync_check.md`. Present findings grouped by severity and end with the verdict line. This is also where `docs/CHANGELOG.md` `[Unreleased]` is brought up to date with the branch's user-visible changes; draft the missing entries in the file's style (`**Bold summary** — detail (issue #N)`). Doc edits land via a normal PR to the release branch.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 3. Standards spot-check

Follow `.claude/commands/standards_check.md`. Present findings grouped by severity and end with the verdict line.

**CHECKPOINT — ready for the next check?** Wait for the user.

## 4. Security review

Run `/security-review` on `main..HEAD`. Present findings grouped by severity and end with the verdict line.

**CHECKPOINT — ready for the contributor audit?** Wait for the user.

## 5. Contributor & tester acknowledgement audit

Verify every code contributor and frequent tester is acknowledged in `ABOUT.md` (rendered in the About tab, so this is what users see).

### 5a. Build the contributor list

```bash
git log --format='%aN|%aE' --no-merges | sort -u
gh api "repos/Osiris-DevWorks/sc-profile-editor/contributors" --paginate --jq '.[] | {login: .login, contributions: .contributions}'
```

**Filter out**: the repo owner (`Osiris-DevWorks` / `Osiris DevWorks` / `Amr`), AI co-author trailers (`Claude`, `noreply@anthropic.com`), bot accounts (`*[bot]`), and anonymous commits with no name or GitHub login. Merge entries for one person committing under several name/email combinations; if unsure, surface the duplicates.

### 5b. Pull the current acknowledgement set

Read `ABOUT.md` → `## Acknowledgements` (the tester list) and any **Contributors** section. If `README.md` carries a matching section, read it too and treat drift between the two as a finding.

### 5c. Categorize each missing contributor

For every contributor not acknowledged: commit count (`git log --author='<email>' --no-merges --oneline | wc -l`) and a sample of files touched. **Substantial**: ≥3 commits or non-trivial `src/`, `scripts/`, `tests/` or `visual-templates/` changes. **Drive-by**: 1–2 commits, trivial files only.

### 5d. Tester candidates from issue reporters

```bash
gh issue list --state all --limit 1000 --json number,author --jq '.[].author.login' | sort | uniq -c | sort -rn
```

Flag everyone with **3 or more** reported issues as a candidate tester, then drop the owner, bots, anyone already in the Acknowledgements list, and anyone who is also a code contributor (credited as a contributor, never both). Issues mirrored from Discord name the real reporter in the body; attribute by that name, and list unattributable reports rather than guessing.

### 5e. Report

```
**Missing — substantial contributors** (suggest adding): …
**Missing — drive-by fixers** (consider adding, or skip): …
**Already acknowledged**: N covered.

**Tester candidates** (≥3 reported issues, not code contributors): …
```

Verdict: **Clean** (every substantial contributor acknowledged), **Minor issues** (only drive-bys missing or README/ABOUT drift), **Needs attention** (substantial contributors missing). Tester candidates are advisory and never block a release.

**CHECKPOINT — ask before drafting additions to `ABOUT.md` (and `README.md` if it carries the same list).** Do not edit without confirmation.

## 6. Tester installer build on the release PR

1. Find the release PR: `gh pr list --base main --head release/X.Y.Z --state open --json number,title`.
2. If none exists, open it now with title `Release X.Y.Z` and the CHANGELOG section as the body. **Opening the PR is not merging it.**
3. Add the label: `gh pr edit <N> --add-label build-installer`. `installer-preview.yml` builds `SCProfileEditor-vX.Y.Z-Setup.exe` and comments the download link on the PR; later pushes to the PR rebuild automatically. If the label was already present from an earlier round, remove and re-add it, or dispatch the workflow manually, so a build runs on the current head.
4. Report the run (`gh run list --limit 1`) and the artifact name (`scprofileeditor-installer-{SHA}`, 30-day retention).

**CHECKPOINT — confirm before opening the PR and adding the label; both are visible on GitHub and start CI builds.** Wait for the user.

## 7. Issue close-on-verify pass

Runs last because verification comes from testers using the step-6 build. On the day the audit runs, most issues will legitimately sit in "awaiting verification"; that is the expected outcome. Re-run this step alone once tester sign-offs come back, before the merge to `main`.

### 7a. Gather the release's issues

Union of: issues labeled `next-release` (`gh issue list --state open --label next-release --json number,title,author`) and every `#NN` referenced in `git log main..HEAD --oneline`.

### 7b. Classify each

Look for a confirming comment from the reporter or a tester on the preview build (`gh issue view <N> --json title,state,comments`). Bucket as **Fixed + tester-verified** (close), **Fixed, awaiting verification** (hold; a passing local test is not a tester sign-off), or **Not addressed** (flag for re-label or defer).

### 7c. Report

```
**Verified — close candidates:** …
**Awaiting verification — hold open:** …
**Not addressed — re-label or defer:** …
```

**CHECKPOINT — present the close / hold / flag list and ask before closing anything.** On confirmation, close each verified issue with a short thanks naming the version it ships in and crediting the tester who confirmed it. Never close one that is only awaiting verification.

## Final summary

One-line overall verdict for release readiness (the worst case across the checks), the remaining Critical/Major findings to address before the `release/X.Y.Z` → `main` merge, and any issues still open that were expected to ship. Say plainly where testing stands: the build is out, and anything step 7 left in "awaiting verification" is waiting on testers, not on the audit.

This command does not ship the release. That is `/ship_release`.
