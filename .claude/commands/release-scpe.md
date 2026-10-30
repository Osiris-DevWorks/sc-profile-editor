This command conducts all the steps related to releasing the latest version of SCPE.

# Invocation

To invoke, type `/release-scpe`

# Instructions

The release flow mirrors smart-citizen and is split into three commands. Run them in order; each one has its own checkpoints:

1. `/start_release major|minor|patch` — opens `release/X.Y.Z` off `main` and bumps `VERSION.TXT` (done at the start of a cycle, not at ship time).
2. `/pre_release` — tests, CHANGELOG/doc currency, security review, tester installer build on the release PR, issue close-on-verify.
3. `/ship_release` — finalize the CHANGELOG section, local smoke-test installer, merge the release PR to `main`. The merge triggers `.github/workflows/release.yml`, which tags, builds the installer and publishes the GitHub Release.

The full model is documented in `docs/RELEASE_PROCESS.md`.
