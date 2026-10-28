---
description: Open the next release/X.Y.Z branch off main and bump VERSION.TXT (major|minor|patch)
---

# /start_release

Open the next integration branch per the release model in `docs/RELEASE_PROCESS.md`. Bumps `VERSION.TXT` and commits the kickoff change locally. Does **not** push — the user pushes when ready.

## Argument

`$ARGUMENTS` — required, one of `major`, `minor`, `patch`:

- `major`: `X.Y.Z` → `(X+1).0.0`
- `minor`: `X.Y.Z` → `X.(Y+1).0`
- `patch`: `X.Y.Z` → `X.Y.(Z+1)`

If `$ARGUMENTS` is empty or not exactly one of the three values, abort and ask. Do not guess.

## Procedure

Stop on the first failure of any step.

1. **Validate the argument** (case-sensitive). Otherwise abort: `"/start_release requires one of: major, minor, patch"`.
2. **Read `VERSION.TXT`**, strip whitespace, split on `.` into exactly three non-negative integers. Abort with the offending content if that fails.
3. **Compute** `NEW_VERSION` and `NEW_BRANCH = release/NEW_VERSION`.
4. **Safety preconditions**, abort on the first failure:
   - On `main` (`git branch --show-current`). *"Switch to main before starting a release."*
   - Clean working tree (`git status --porcelain` empty). List offending files otherwise.
   - `main` up to date: `git fetch origin main`; if `git rev-list --count main..origin/main` > 0, abort: *"Local main is behind origin/main. Pull before starting a release."* If the fetch fails (offline), warn and proceed.
   - `NEW_BRANCH` exists neither locally (`git rev-parse --verify`) nor on origin (`git ls-remote --heads origin NEW_BRANCH`).

   **CHECKPOINT — about to create `NEW_BRANCH` and bump `VERSION.TXT` from `<current>` → `NEW_VERSION`. Confirm to proceed.** Wait for the user.

5. `git checkout -b NEW_BRANCH` from `main`.
6. Overwrite `VERSION.TXT` with `NEW_VERSION` plus a single trailing newline (UTF-8, no BOM). `installer.iss` reads this file at compile time, so nothing else needs a version edit.
7. Leave `docs/CHANGELOG.md` alone; the `## [NEW_VERSION]` section is created at ship time by `/ship_release`.
8. Commit `VERSION.TXT` only:

   ```
   Bump version to NEW_VERSION

   Branch-opening commit for the NEW_VERSION integration target.
   ```

9. **Report**: branch created, old → new version, and the scope reminder:
   - `patch` → *"Patch branches accept only bug fixes and minor polish. Flag any feature work as scope-mismatch."*
   - `minor` → *"Minor branches accept features and additional device support."*
   - `major` → *"Major branches accept breaking changes."*
   - *"Branch is local only — push with `git push -u origin NEW_BRANCH` when ready. PRs target this branch, not main."*

## Notes

- Never pushes, never tags. Tags are created by `release.yml` when the branch merges to `main`.
- If another `release/X.Y.*` branch is still open on origin, surface it in the report; opening the next one before the current one ships is unusual.
