---
description: Verify user-facing strings, README, ABOUT and the CHANGELOG match the current app
---

# /docs_sync_check

Cross-check the app's user-facing surface against the docs. Catches drift introduced when a button or tab is renamed in code but the doc still describes the old name, when a device template is renamed but README still lists the old name, or when a feature ships without a docs update. `README.md` and `ABOUT.md` are both rendered inside the app (About tab), so stale text ships to users.

## Severities

- **Critical** — `README.md` or `ABOUT.md` fails to render in-app (markdown the renderer chokes on, or a missing bundled file after a rename).
- **Major** — a workflow step in `README.md` (Quick Start, Common Tasks, Reference) no longer matches the code, or a user-facing control is described under a name that no longer exists.
- **Minor** — a feature or device mentioned in `ABOUT.md` or README's feature/device lists has been removed or renamed but isn't workflow-critical.

## Inputs

- `src/gui/*.py` — window title, tab names, button/menu labels, dialog text, status messages.
- `visual-templates/template_registry.json` — template display names (README lists supported devices).
- `README.md` — Quick Start, Common Tasks, Reference, Troubleshooting.
- `ABOUT.md` — feature summary, acknowledgements.
- `docs/CHANGELOG.md` — `[Unreleased]` must describe every user-visible change on the branch.

## Checks

1. **Bundled docs still load** *(Critical)*: `ABOUT.md` and `README.md` are read via `get_resource_path`; confirm both are in `scripts/build/build_exe.py`'s `--add-data` list and parse as markdown.
2. **String drift** *(Major)*: pull every user-facing literal from `src/gui/` (tab names, button text, dialog titles) and check whether README/ABOUT refer to any of them by a name no longer in the code. Flag `doc:line → code:line` with the suspected new wording.
3. **Workflow currency** *(Major)*: README's Common Tasks cover loading a profile, editing labels, remapping a binding, Device View, Config tab device mapping, exports. If the branch diff touched any of those flows, surface the matching README section for review.
4. **Device list parity** *(Minor, escalate to Major if a how-to names the device)*: every non-deprecated template name in `template_registry.json` should appear where README lists supported devices, and vice versa.
5. **CHANGELOG parity** *(Major)*: compare `git log <base>..HEAD --oneline` with `[Unreleased]`; every user-visible change needs an entry.

## Output

Group findings by severity, one per line: `doc-file:line → code-file:line — short description`.

End with a one-line **verdict**: **Clean**, **Minor issues**, or **Needs attention** (any Critical or Major).

After the verdict, **CHECKPOINT — pause and ask whether to draft doc updates for the Critical/Major findings, or move on.** Do not edit docs without confirmation — surface, don't auto-correct.
