# Release Process

**For:** Release managers - Creating and publishing new versions

SC Profile Editor uses the same release model as its sibling project `smart-citizen`: **long-lived release branches as integration targets**, and a merge to `main` that *is* the release. GitHub Actions does the tagging, building and publishing.

## Branching model

- After a release ships, the next `release/X.Y.Z` branch opens off `main` and `VERSION.TXT` bumps on it (`/start_release patch|minor|major`). That branch is the integration target until it ships.
- **The version in the branch name signals scope.** A patch branch (e.g. `release/0.10.2`) takes bug fixes and minor polish only; features and new device support wait for the next minor.
- **PRs target the active `release/X.Y.Z`, not `main`.** `main` only ever receives the release-branch merge.
- When the branch is stable, add the **`build-installer` label** to the release PR. `installer-preview.yml` builds `SCProfileEditor-vX.Y.Z-Setup.exe` as a 30-day artifact and comments the download link on the PR so testers can verify before anything reaches `main`.
- **Merging `release/X.Y.Z` → `main` is the release trigger.** Until then nothing on the release branch is "released".

Don't propose tagging or merging to `main` mid-integration; the user drives that handoff.

## Branch protection (GitHub settings, set once by the owner)

- **`main`**: classic branch protection, PR required. Already in place.
- **`release/*`**: a "Protect release branches" ruleset targeting `refs/heads/release/*` — require a pull request, require one approving review from the code owner (`.github/CODEOWNERS` gives `*` to `@Osiris-DevWorks`), block force-pushes and deletion. The owner (admin) bypasses it for the `/start_release` kickoff push.
- **Secrets**: `DISCORD_RELEASE_WEBHOOK_URL` for the release announcement (optional; the release still publishes without it).
- **Labels**: create `build-installer` once in the repo's label list.

## Version

`VERSION.TXT` is the sole source of truth. `src/utils/version.py` reads it at runtime, `scripts/build/build_exe.py` prints it, `installer.iss` reads it at compile time via ISPP, and `release.yml` derives the git tag from it. Nothing else is edited for a bump.

## Workflows

| Workflow | Trigger | What it does |
|---|---|---|
| `ci.yml` | PR to `main` or `release/**` | `pytest tests/`, PyInstaller onedir build, 7-day onedir artifact |
| `installer-preview.yml` | `build-installer` label on a PR, or manual | Tests, build, Inno Setup compile, 30-day installer artifact + PR comment |
| `installer-preview-cleanup.yml` | PR merged | Deletes that PR's preview artifacts |
| `release.yml` | Push to `main` (skips if `v{VERSION}` is already released), push of a `v*.*.*` tag, or manual with a tag | Tests, build, installer, auto-tag, GitHub Release with the `## [X.Y.Z]` CHANGELOG section as body, Discord post |
| `release-notify.yml` | Manual | Re-sends the Discord post for an existing tag |

## Release cycle

1. **Open the branch** — `/start_release patch` (or `minor`/`major`) on a clean, current `main`. Push it: `git push -u origin release/X.Y.Z`.
2. **Integrate** — normal PRs against `release/X.Y.Z`. Keep `docs/CHANGELOG.md` `[Unreleased]` current as changes land.
3. **Gate** — `/pre_release`: tests, CHANGELOG/doc currency, security review, open the release PR (`release/X.Y.Z` → `main`) and label it `build-installer`, then close tester-verified issues.
4. **Ship** — `/ship_release`: rename `[Unreleased]` to `## [X.Y.Z] - YYYY-MM-DD` (land via PR; `release.yml` fails without this section), build and smoke-test a local installer, then merge the release PR with a merge commit. The push to `main` runs `release.yml`.
5. **After** — watch the `Release` run, download the published installer once and smoke-test it, update the SC Profile Editor tile in `../osiris-devworks-website/src/data/projects.ts` (static `version` fallback, `features`, `status`, screenshots) and push that repo's `main`, then `/start_release patch` for the next cycle.

## Manual fallbacks

- **Re-run a failed release**: Actions → Release → Run workflow with the existing tag, or push the tag again.
- **Build locally**: `python scripts/build/build_exe.py` then `iscc installer.iss` (or `scripts\build\build_all.bat`). Output: `dist\SCProfileEditor-vX.Y.Z-Setup.exe`. Local builds are for smoke-testing; never attach one to a GitHub release by hand while `release.yml` is also publishing.
- **Release notes**: `python scripts/release_notes.py X.Y.Z` prints what the release body will be.

## GitHub Release format

Title: `SC Profile Editor vX.Y.Z` (set by the workflow). Body: the CHANGELOG section, so write CHANGELOG entries as release notes — user-facing, grouped under Added / Changed / Fixed, with issue numbers.
