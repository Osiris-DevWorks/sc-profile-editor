# Test Plan

The living tester checklist for the release in progress. Amr runs it on the `build-installer` preview build of the release PR (`release/X.Y.Z` → `main`) before it merges.

- Each feature pushed to the active `release/X.Y.Z` adds its own section under that release's heading, titled `### #issue: short name`, with concrete items a tester can mark pass or fail.
- `/pre_release` copies the release's sections into the release PR body.
- After the release ships, `/ship_release` clears the sections so the next release starts empty.

## Next release

_No features yet._
