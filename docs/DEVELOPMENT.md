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

There is no UI test harness. Unit tests cover the parser, DirectInput GUID parsing, label parsing, and joystick input translation / the mock backend; all run without hardware.

```bash
pytest tests/
pytest --cov=src tests/
```

For UI / device / export work, manual smoke testing is required, but it no longer needs real joysticks (see below).

### Working without joysticks (mock mode)

All joystick access goes through `src/utils/joystick_backend.py`. The default `PygameBackend` talks to real hardware; `MockBackend` serves virtual sticks from a JSON file instead.

```bash
python src/main.py --mock-joysticks                       # default preset; follows each profile you open
python src/main.py --mock-joysticks tests/fixtures/mock_devices/dual_vpc_alphas.json
SCPE_MOCK_JOYSTICKS=1 python src/main.py                 # same thing via env var
```

In PowerShell: `$env:SCPE_MOCK_JOYSTICKS = "1"; python src/main.py`.

**Mirror any profile.** With the default preset, the panel's **Match the profile I open** box is ticked: every profile you load (File > Load, last-opened, or a preset) rebuilds the virtual sticks from that profile's `<options type="joystick" Product="…">` entries, so its js1, js2… devices show up as connected with the right names and VID/PID, and every button and hat it binds has a control to click. **Load setup…** builds the sticks from any other SC profile `.xml` or devices `.json` and keeps them (it unticks the box). You can also start straight from a profile:

```bash
python src/main.py --mock-joysticks "C:/…/Controls/Mappings/layout_my_setup_exported.xml"
```

Counts are inferred from the profile: buttons = the highest one bound (at least 32), hats = the highest bound (at least 1), and all 8 standard axes. A missing instance (e.g. a profile that binds js3 but only lists js1/js2) gets a placeholder "Virtual stick js3" so numbering stays aligned. Untick the box if you want to see the "devices not connected" warning a mismatched profile normally triggers.

A **Virtual Joysticks** window opens next to the main window. Open a binding, press **Detect Input**, then click a button, hat arrow, or drag an axis slider past halfway: the Remap dialog receives `js2_button7`, `js1_hat1_up`, `js1_rotz` and so on, just as it would from a real stick. The Config tab lists the virtual devices, with VID/PID, so device-to-joystick mapping and Device View templates resolve as they would on the hardware machine. Keyboard and mouse detection still use the real keyboard and mouse.

**Device files** (`tests/fixtures/mock_devices/*.json`):

```json
{
  "devices": [
    {"name": "VKBsim Gladiator EVO R", "product": "{0200231D-0000-0000-0000-504944564944}",
     "buttons": 34, "hats": 1, "axes": 6}
  ],
  "script": [
    {"after_ms": 500, "kind": "button", "js": 1, "button": 5},
    {"after_ms": 900, "kind": "hat", "js": 1, "hat": 1, "value": "up"},
    {"after_ms": 1200, "kind": "axis", "js": 1, "axis": "rotz", "value": -0.9}
  ]
}
```

Copy `product` straight from an `<options type="joystick" Product="…">` line in an SC profile (or give `"vid"`/`"pid"` as hex strings) to mimic your own sticks. The optional `script` replays events each time detection starts; tests use it to run the real detection loop against recorded sequences (`tests/test_joystick_backend.py`, `recorded_session.json`).

The devices file's order is the js order: the first device is `js1`. Mock mode is a developer flag only; release builds behave exactly as before unless it is passed.

**Other routes** if you need Star Citizen itself to see a fake stick (not just SCPE): install vJoy on Windows and drive it from a feeder app or `pyvjoy`. SCPE's pygame backend picks vJoy devices up like any other stick, no mock mode needed. `test_plan.md` and `TEST_PLAN_v0.8.2.md` at the repo root are historical references for what coverage typically looks like.

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
