---
description: Lint the current diff against SC Profile Editor's documented standards
---

# /standards_check

Audit the branch diff (`git diff $(git merge-base HEAD <base>)...HEAD`, plus any working-tree changes) against the project's documented standards in `CLAUDE.md` and `docs/DEVELOPMENT.md`. Report findings with file:line references and severity. **Do not auto-fix without confirmation.**

- **Critical** — breaks correctness, the packaged build, or the XML round-trip. Must fix before merge.
- **Major** — wrong but won't immediately break. Should fix before merge.
- **Minor** — stylistic or "consider" notes. Optional.

## Checks

- **Bundled resource lookup** *(Critical)*: any `open(...)`, `Path(...)` or `os.path.join(...)` that reaches a bundled file (`visual-templates/`, `example-profiles/`, `default-bindings/`, `assets/`, `UNBIND_ALL.xml`, `label_overrides.json`, `README.md`, `ABOUT.md`, `VERSION.TXT`) without going through the `_MEIPASS`-aware `get_resource_path()` helper. Works in dev, breaks in the installer.
- **Build data list** *(Critical)*: a new bundled file or folder that is not in `scripts/build/build_exe.py`'s `--add-data` list (and the matching list in `docs/DEVELOPMENT.md`).
- **Bare `src/` imports** *(Critical)*: new modules must import the same way their neighbours do (`from parser.xml_parser import …`, resolved by `--paths src`). A mix of `src.parser` and `parser` imports breaks the frozen build.
- **activationMode on axes** *(Critical)*: any code path that writes `activationMode` for an input `InputValidator.is_analog_axis()` says is analog, or that writes a default mode the user did not pick (the v0.10.2 hat bug: an explicit `press` overrides the game's `hold`). `None` means "game default" and must stay omitted in the XML.
- **Settings access** *(Major)*: direct `QSettings(...)` construction outside `src/utils/settings.py`. Use `AppSettings` so keys and the registry path stay in one place.
- **Label resolution** *(Major)*: display labels must resolve through `src/utils/label_overrides.py` (custom → global → auto-generated). A new code path that formats an action name directly bypasses user overrides.
- **Template registry** *(Major)*: new templates need `device_match_patterns` that match the SC product string case-sensitively, a `product_ids` list where the VID/PID is known, and `field_mapping.json` next to the PDF. Composite devices route through `device_splitter.py`; don't special-case them in the manager.
- **Version source** *(Major)*: any literal version string in code, `installer.iss`, or docs other than `VERSION.TXT`. The window title, installer and release tag all derive from that file.
- **Logging** *(Minor)*: `print()` in `src/` instead of the module `logger`.

## Code duplication / DRY

- **Copy-paste blocks** *(Major)*: 5+ line blocks in the diff that appear verbatim elsewhere. Report both locations.
- **Magic literals** *(Minor)*: SC input prefixes (`js1_`, `kb1_`, `mouse1_`, `gp1_`), the PIDVID GUID suffix, QSettings keys, template ids repeated in 2+ places without a named constant.
- **Near-duplicate functions** *(Minor)*: a new function structurally identical to an existing one, differing only in a literal or a call target.

Calibration: 3+ occurrences → recommend extraction; 2 → "consider"; never propose a single-use helper.

## Output

Group findings by severity, one per line: `file:line — short description — fix hint`.

End with a one-line **verdict**: **Clean**, **Minor issues**, or **Needs attention** (any Critical or Major).

After the verdict, **CHECKPOINT — pause and ask whether to draft fixes for the Critical/Major findings, or move on.** Wait for the answer before doing anything else.
