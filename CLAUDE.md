# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Session Protocol

At the start of each session, ask:
> What would you like to work on today?

Wait for an explicit response before taking action.

For non-trivial implementation tasks, use `EnterPlanMode` to design and align on the approach before coding. For multi-step work, use `TaskCreate`/`TaskUpdate`. Cross-session context lives in the memory system at:
`C:\Users\aabou\.claude\projects\C--Users-aabou-PycharmProjects-OsirisDevworks-sc-profile-editor\memory\`

---

## Project Overview

**SC Profile Editor** — Windows desktop app for Star Citizen players to view, edit, and export their control profiles in human-readable formats (CSV, PDF, Word, PNG).

- **Stack:** Python 3.12+, PyQt6, PyMuPDF, pygame, pynput, PyInstaller
- **Platform:** Windows only
- **Current version:** see `VERSION.TXT` (authoritative — the window title and `installer.iss` should match it)
- **Sibling project:** `../smart-citizen/` shares architectural DNA (PyQt6 + QSettings + PyInstaller + Inno Setup); patterns are usually transferable.

---

## Architecture

### Data flow

```
Load Profile (XML)
   → Parse XML → Detect Devices → Generate Labels → Display Table
   → Apply Device Mappings & Template Selection
   → Edit Labels → Save Overrides → Update Device View & Table
   → Export → Apply Filters & View Mode → CSV / PDF / Word / PNG
```

### Load-bearing concepts (not obvious from reading the code)

**Action Registry (`src/registry/action_registry.py`)** — At startup, loads ~1,085 actions across ~50 actionmaps from `UNBIND_ALL.xml` (project root). This is the universe of every possible binding; `example-profiles/BLANK.xml` is a profile that materializes all of them. The registry powers dropdown suggestions, validation, and auto-label generation.

**Three-tier label override system (`src/utils/label_overrides.py`)** — Every action's display label resolves through:
1. **Custom** — user edits, persisted in `label_overrides_custom.json` under AppData (`C:\Users\{user}\AppData\Local\SC Tools\...`).
2. **Global** — defaults bundled with the app in `label_overrides.json` (project root, ~72 common actions).
3. **Auto-generated** — derived from the action name as a last resort.

Edits propagate **in real time** to both the Controls Table and the Device View PDF via Qt signals. When debugging "why is this label wrong?", check tiers 1 → 2 → 3 in that order.

**PDF-based device templates (`src/graphics/pdf_template_manager.py`, `src/gui/qtpdf_device_widget.py`)** — Devices are visualized as PDFs with interactive form fields (no Chromium — uses native QtPdf for rendering, PyMuPDF/fitz for field manipulation). Pattern matching from `visual-templates/template_registry.json` maps a profile's device name to a template directory.

**Composite devices (`src/utils/device_splitter.py`)** — Some hardware presents as a stick + add-on module (e.g., VKB Gladiator + SEM module). The splitter logic separates a single physical device into multiple logical templates so each gets its own diagram.

**Input detection (`src/utils/input_detector.py`)** — Joystick (pygame), keyboard with modifier support (pynput), mouse (pynput). Runs in a thread with a 10-second timeout; communicates with the UI via Qt signals. Used by the Remap Dialog.

**Settings persistence** — `QSettings` writes to the Windows registry under this user. Window geometry, last-opened profile, and view options are auto-saved.

**PyInstaller resource paths** — All bundled resources are loaded via a `_MEIPASS`-aware helper. When adding new bundled assets, route the lookup through that helper or the packaged build will fail to find them in dev paths.

```python
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder when packaged
    except AttributeError:
        base_path = os.path.dirname(...)  # dev path
    return os.path.join(base_path, relative_path)
```

**Single-instance lock (`src/utils/single_instance.py`)** — Windows mutex prevents two copies of the app from racing on the AppData JSON files.

### GUI shape

`src/gui/main_window.py` hosts four tabs: **Controls Table** (filterable bindings, two view modes — Standard 4-col / Detailed 6-col), **Device View** (interactive PDF), **Config** (device detection + device-to-joystick mapping + SC profiles dir), **About**. System tray integration supports minimize-to-tray.

### Where things live

```
src/                  application code (gui/, parser/, exporters/, graphics/, models/, registry/, utils/)
visual-templates/     per-device PDF templates + template_registry.json
example-profiles/     sample SC XML profiles incl. BLANK.xml (master with all 1,085 actions)
docs/                 CHANGELOG, DEVELOPMENT, RELEASE_PROCESS, CREATING_PDF_TEMPLATES
scripts/              ad-hoc utility scripts (NOT build scripts — see Build below)
deprecated/           old SVG/PNG/OCR system removed in v0.4.0; ignore unless excavating history
tests/                pytest unit tests (currently just test_parser.py)
```

---

## Commands

### Run / test

```bash
python src/main.py                                   # run app locally
pytest tests/                                        # run unit tests
pytest --cov=src tests/                              # with coverage
```

### Build

There is **no `scripts/build/build_exe.py` or `build_*.bat` in this repo** despite older docs referencing them. The actual release flow is orchestrated by the user-level `/release-scpe` skill, which invokes PyInstaller against `src/main.py` (output: `dist/SCProfileEditor-v{version}.exe`) and then compiles `installer.iss` with Inno Setup 6.

If you need to rebuild manually:

```powershell
.venv\Scripts\activate
pyinstaller --onefile --windowed --icon=assets\icon.ico `
    --add-data "VERSION.TXT;." `
    --add-data "label_overrides.json;." `
    --add-data "README.md;." `
    --add-data "assets;assets" `
    --add-data "visual-templates;visual-templates" `
    --add-data "example-profiles;example-profiles" `
    --add-data "default-bindings;default-bindings" `
    --add-data "UNBIND_ALL.xml;." `
    --name "SCProfileEditor-v$(Get-Content VERSION.TXT)" src\main.py

# Then build the installer (requires Inno Setup 6):
iscc installer.iss
```

Update `installer.iss` (`MyAppVersion`, `MyAppExeName`) and `VERSION.TXT` together — they must agree, or the installer will fail to find the exe.

### Versioning

Edit `VERSION.TXT` and `installer.iss` together. Bump:
- **Patch** (0.9.1 → 0.9.2) — bug fixes only
- **Minor** (0.9.1 → 0.10.0) — new features, additional device support
- **Major** — breaking changes

---

## Development workflow

1. **Plan** non-trivial changes in `EnterPlanMode` and align before coding.
2. **Implement** in focused chunks; check in between logical blocks.
3. **Test manually** — there's no UI test harness. At minimum: load a profile, verify the table populates, toggle Standard ↔ Detailed view, check that Device View and exports still work. Test with hardware when touching input detection.
4. **Document** alongside the change: update `docs/CHANGELOG.md` under `[Unreleased]`. Update `README.md` only when user-visible behavior changes.
5. **Commit** with a clear message that explains the *why*. Show the message before committing.

Test plans for past releases live in `test_plan.md` and `TEST_PLAN_v0.8.2.md` — useful as reference for what coverage looks like, but they are historical, not living checklists.

---

## Debugging starting points

- **Wrong label appearing:** check tier 1 (`label_overrides_custom.json` in AppData) before tier 2 (`label_overrides.json` in repo root).
- **Device template not found:** verify the device name pattern in `visual-templates/template_registry.json` matches the profile's device string (case-sensitive); composite devices route through `device_splitter.py`.
- **Input detection misbehaving:** confirm the device is detected in the Config tab first; pygame event pumping and pynput listeners both run in `src/utils/input_detector.py`.
- **Build can't find a bundled file:** ensure the lookup goes through the `_MEIPASS`-aware resource-path helper, and that the file is included in the PyInstaller `--add-data` list.
- **Verbose logging:** flip `logging.INFO` → `logging.DEBUG` in `src/main.py`.

---

## Related projects (workspace siblings)

- **`../smart-citizen/`** — closest sibling architecturally (PyQt6 + QSettings + PyInstaller + Inno Setup). Look here first when you need a precedent.
- **`../battlestations/`** — React frontend, also Star Citizen — unrelated stack but shared domain vocabulary.
- Workspace-level `../CLAUDE.md` documents the broader Osiris DevWorks layout.
