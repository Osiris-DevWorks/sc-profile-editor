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

The build is scripted and mirrors `smart-citizen`:

```powershell
.venv\Scripts\activate
python scripts\build\build_exe.py     # PyInstaller --onedir -> dist\SCProfileEditor\SCProfileEditor.exe
iscc installer.iss                     # Inno Setup 6 -> dist\SCProfileEditor-v{version}-Setup.exe
scripts\build\build_all.bat           # both steps
```

`VERSION.TXT` is the only place the version lives: `src/utils/version.py` reads it at runtime, `scripts/build/build_exe.py` prints it, and `installer.iss` reads it at compile time through ISPP (`#define MyAppVersion Trim(FileRead(...))`). There is nothing else to bump.

The exe name is the stable `SCProfileEditor.exe` (not versioned) so Start Menu and desktop shortcuts survive upgrades; the installer's `[InstallDelete]` removes the pre-0.10.2 `SCProfileEditor-v*.exe` on upgrade.

Two PyInstaller details in `build_exe.py` are load-bearing and easy to lose if the arg list is edited:

- **`--paths src`** — tells PyInstaller that `src/` is a source root so the bare imports inside `main_window.py` (e.g. `from parser.xml_parser import …`) resolve at frozen-import time. Without it the exe crashes on launch with `ModuleNotFoundError: No module named 'parser'` (v0.10.0's first build shipped that way).
- **`--add-data "ABOUT.md;."`** — `main_window.py` reads `ABOUT.md` via `get_resource_path("ABOUT.md")` for the About tab. If missing, that tab silently fails to render.

When adding new bundled resources, two things must change together: the `--add-data` list in `build_exe.py`, **and** the lookup in code must route through the `_MEIPASS`-aware resource-path helper (otherwise it works in dev but breaks in the packaged build). In an onedir build `_MEIPASS` points at `dist\SCProfileEditor\_internal\`.

CI (`.github/workflows/ci.yml`) runs the tests and this build on every PR to `main` or `release/**`, and uploads the onedir as a 7-day artifact. Adding the `build-installer` label to a PR makes `installer-preview.yml` compile a full installer for testers (30-day artifact, link commented on the PR).

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

See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the release-branch model. The `/start_release`, `/pre_release` and `/ship_release` commands walk it with checkpoints; merging `release/X.Y.Z` into `main` triggers `release.yml`, which tags, builds and publishes.

---

## Adding device templates

See [CREATING_PDF_TEMPLATES.md](CREATING_PDF_TEMPLATES.md). New templates need: a PDF with form fields under `visual-templates/{device-id}/`, a corresponding entry in `visual-templates/template_registry.json`, and (if it's a composite device) handling in `src/utils/device_splitter.py`.

---

## Tech stack

PyQt6 (GUI + native QtPdf rendering), PyMuPDF (PDF form-field manipulation), python-docx, reportlab, Pillow, pygame (joystick input), pynput (keyboard/mouse input), PyInstaller (packaging), Inno Setup (Windows installer), pytest.
