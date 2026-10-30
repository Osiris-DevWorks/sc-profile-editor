---
description: Ship the active release/X.Y.Z — finalize the CHANGELOG section, smoke-test a local installer, merge to main (which auto-tags, builds and publishes the GitHub release), then offer the next branch. Run after /pre_release passes.
---

# /ship_release

Walk the release-ship sequence with checkpoints between each step. The merge to `main` has external side effects (tag, GitHub Release, Discord post), so confirm before each step.

## Preflight

Ships whichever `release/X.Y.Z` branch the user is on. Stop on the first failure.

- `git branch --show-current` matches `release/X\.Y\.Z`; extract `X.Y.Z`. Abort otherwise.
- Surface any *other* `release/*` branches on origin and ask the user to confirm this is the one.
- Clean working tree.
- `VERSION.TXT` equals `X.Y.Z`.
- `git fetch origin release/X.Y.Z`; abort if the local branch is behind origin.
- Advisory: if `/pre_release` does not appear to have run this session, remind the user and ask whether to continue.

**CHECKPOINT — preflight passes. Ready to finalize the CHANGELOG for `X.Y.Z`?**

## 1. Finalize the CHANGELOG section

`release.yml` builds the GitHub Release body from the `## [X.Y.Z]` section of `docs/CHANGELOG.md` (via `scripts/release_notes.py`) and **fails the release if that section is missing**.

1. Rename `## [Unreleased]` content into `## [X.Y.Z] - YYYY-MM-DD` (today's date) and leave a fresh empty `## [Unreleased]` above it.
2. Verify locally: `python scripts/release_notes.py X.Y.Z` prints the section.
3. Land it via a PR to the release branch (branch protection blocks direct pushes), then pull.

**CHECKPOINT — CHANGELOG section confirmed. Build a local installer for smoke-testing?**

## 2. Build the installer locally (smoke test only)

**The distributed installer is built by `release.yml`, not by this command.** The local build exists so the user can install and smoke-test before the public release.

```powershell
.venv\Scripts\python.exe scripts\build\build_exe.py
powershell -NoProfile -Command "& 'C:\Users\<you>\AppData\Local\Programs\Inno Setup 6\ISCC.exe' installer.iss"
```

Output: `dist\SCProfileEditor-vX.Y.Z-Setup.exe`. Do not attach it to a GitHub release by hand; that races with the workflow.

**CHECKPOINT — installer built. Install it, load a profile, check the Controls Table, Device View and an export. Do not proceed without an explicit go.**

## 3. Merge the release PR (this is the ship)

The push to `main` triggers `release.yml`, which reads `VERSION.TXT`, auto-tags `vX.Y.Z`, runs the tests, builds the installer, publishes the GitHub Release with the CHANGELOG section as its body, and posts the Discord notification.

1. Confirm the release PR (`release/X.Y.Z` → `main`) is green and approved.
2. Merge it with a merge commit (`gh pr merge <N> --merge`), never squash: the release branch history is the record.

**CHECKPOINT — merged. Watch the `Release` workflow (`gh run watch`) and confirm the installer is attached to the release and the Discord post landed.**

## 4. Close resolved issues

Review open issues fixed in this release that were held in `/pre_release` step 5 awaiting verification; close the ones now confirmed. Present a table of what was closed and why.

**CHECKPOINT.**

## 5. Update the website tile

Per `docs/RELEASE_PROCESS.md`: in `../osiris-devworks-website/src/data/projects.ts` bump the static `version` fallback and refresh `features`/`status`/screenshots for the SC Profile Editor entry. Pushing that repo's `main` deploys it.

## 6. Open the next integration branch

Ask: *"Open the next branch now? `patch` gives you `release/X.Y.(Z+1)` for bug fixes. Reply `patch`, `minor`, `major`, or `skip`."* On a bump arg, defer to `/start_release`.

## Final report

- `Shipped vX.Y.Z`
- Release URL
- Next integration branch (or none yet)
- Reminder: download the published installer once and smoke-test it.
