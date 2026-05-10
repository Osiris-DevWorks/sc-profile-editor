# Star Citizen Profile Editor — Development Guide

A desktop application for editing and converting Star Citizen control profile XML files into human-readable formats (PDF, Word, CSV) with annotated device graphics.

> For end-user documentation, see [README.md](../README.md). For architecture and AI-assistant context, see [CLAUDE.md](../CLAUDE.md).

The current version lives in `VERSION.TXT` and is the source of truth — keep `installer.iss` (`MyAppVersion`, `MyAppExeName`) in sync with it.

---

## Setup

**Prerequisites:** Python 3.12+, Git, Inno Setup 6 (for installer builds only).

```powershell
git clone <repository-url>
cd sc-profile-editor

python -m venv .venv
.venv\Scripts\activate           # PowerShell / cmd
# source .venv/bin/activate      # bash / WSL

pip install -r requirements.txt
```

---

## Running

```bash
python src/main.py
# or:
python -m src.main
```

Logging level is set in `src/main.py` — flip `logging.INFO` → `logging.DEBUG` for verbose output.

---

## Testing

There is no UI test harness; the unit tests cover the parser only.

```bash
pytest tests/
pytest --cov=src tests/
```

For UI / device / export work, manual smoke testing is required. `test_plan.md` and `TEST_PLAN_v0.8.2.md` at the repo root are historical references for what coverage typically looks like.

---

## Project layout

```
sc-profile-editor/
├── src/                     # application code (gui/, parser/, exporters/, graphics/, models/, registry/, utils/)
├── tests/                   # pytest unit tests
├── visual-templates/        # device PDF templates + template_registry.json
├── example-profiles/        # sample SC XML profiles incl. BLANK.xml
├── default-bindings/        # default SC keybind references
├── assets/                  # icons, images bundled with the app
├── scripts/                 # ad-hoc utility scripts (NOT build scripts — see Building below)
├── deprecated/              # old SVG/PNG/OCR system removed in v0.4.0
├── docs/                    # CHANGELOG, DEVELOPMENT (this file), RELEASE_PROCESS, CREATING_PDF_TEMPLATES
├── CLAUDE.md                # AI-assistant context and architecture overview
├── README.md                # end-user guide (also rendered in the About tab)
├── VERSION.TXT              # current version (single source of truth)
├── installer.iss            # Inno Setup script — must be kept in sync with VERSION.TXT
├── label_overrides.json     # bundled global label defaults
├── requirements.txt
└── UNBIND_ALL.xml           # full SC action database (loaded by action_registry at startup)
```

See [CLAUDE.md](../CLAUDE.md#architecture) for the architecture walkthrough (data flow, three-tier label override system, PDF template system, composite devices, `_MEIPASS` resource paths).

---

## Building

There is **no in-repo build script** despite older docs referencing `scripts/build/build_exe.py` or `build_*.bat`. The actual release flow is orchestrated by the user-level `/release-scpe` skill, which runs PyInstaller against `src/main.py` and then compiles `installer.iss` with Inno Setup.

### Manual exe build

```powershell
.venv\Scripts\activate
$version = (Get-Content VERSION.TXT).Trim()

pyinstaller --onefile --windowed --icon=assets\icon.ico `
    --paths src `
    --add-data "VERSION.TXT;." `
    --add-data "label_overrides.json;." `
    --add-data "README.md;." `
    --add-data "ABOUT.md;." `
    --add-data "UNBIND_ALL.xml;." `
    --add-data "assets;assets" `
    --add-data "visual-templates;visual-templates" `
    --add-data "example-profiles;example-profiles" `
    --add-data "default-bindings;default-bindings" `
    --name "SCProfileEditor-v$version" src\main.py
```

Output: `dist\SCProfileEditor-v{version}.exe`.

Two flags are easy to forget and cause silent runtime failures:

- **`--paths src`** — tells PyInstaller that `src/` is a source root so the bare imports inside `main_window.py` (e.g. `from parser.xml_parser import …`, `from models.profile_model import …`) resolve at frozen-import time. Without it, the runtime `sys.path.insert` in `main_window.py:33` doesn't help — PyInstaller's frozen import system uses a pre-baked module table, not live `sys.path`. v0.10.0's first build shipped without this and crashed with `ModuleNotFoundError: No module named 'parser'` on every launch.
- **`--add-data "ABOUT.md;."`** — `main_window.py` reads `ABOUT.md` for the About tab via `get_resource_path("ABOUT.md")`. If it's not bundled, the About tab silently fails to render even though the rest of the app works.

When adding new bundled resources, two things must change together: the `--add-data` list above, **and** the lookup in code must route through the `_MEIPASS`-aware resource-path helper (otherwise it works in dev but breaks in the packaged build).

### Manual installer build

Requires Inno Setup 6 on PATH (`iscc`).

```powershell
iscc installer.iss
```

`installer.iss` reads from `dist\SCProfileEditor-v{version}.exe`, so build the exe first. The installer output also lands in `dist\`.

---

## Version management

`VERSION.TXT` is the source of truth — `installer.iss` and the window title both consume it. Helpers in `src/utils/version.py`:

- `get_version()`
- `increment_version(version, type)` — `'patch' | 'minor' | 'major'`
- `set_version(version)` — writes `VERSION.TXT`

Bump policy:
- **Patch** (0.9.1 → 0.9.2) — bug fixes only
- **Minor** (0.9.1 → 0.10.0) — new features, additional device support
- **Major** — breaking changes or major rewrites

When you bump `VERSION.TXT`, also update `installer.iss` (`MyAppVersion`, `MyAppExeName`) in the same commit.

---

## Release

See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the full checklist. The `/release-scpe` skill automates most of it.

---

## Adding device templates

See [CREATING_PDF_TEMPLATES.md](CREATING_PDF_TEMPLATES.md). New templates need: a PDF with form fields under `visual-templates/{device-id}/`, a corresponding entry in `visual-templates/template_registry.json`, and (if it's a composite device) handling in `src/utils/device_splitter.py`.

---

## Tech stack

PyQt6 (GUI + native QtPdf rendering), PyMuPDF (PDF form-field manipulation), python-docx, reportlab, Pillow, pygame (joystick input), pynput (keyboard/mouse input), PyInstaller (packaging), Inno Setup (Windows installer), pytest.
