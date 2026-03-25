# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

---

## Session Protocol

**At the start of each session, always ask:**
> What would you like to work on today?

Wait for explicit response before taking action. This ensures alignment on priorities and scope.

**For complex implementation tasks**, use EnterPlanMode to explore the codebase, design a solution, and get approval before coding.

**For tracking progress** on multi-step work, use TaskCreate/TaskUpdate to manage task status.

**For persistent information**, save to the memory system at `C:\Users\aabou\.claude\projects\C--Users-aabou-PycharmProjects-OsirisDevworks-sc-profile-editor\memory\`. This carries context across sessions.

---

## Development Workflow

### 1. Planning Phase
When tackling non-trivial changes:
- **Enter planning mode** (`EnterPlanMode` tool) to explore the codebase and design the solution
- Walk through the plan step-by-step
- **Iterate with the user** until the full plan is approved
- Identify affected files, testing strategy, and documentation updates needed

### 2. Implementation Phase
- Implement changes step-by-step, checking in between logical blocks
- Keep changes focused and minimal (avoid scope creep)
- Follow existing code patterns and conventions (see Code Patterns section)
- Update relevant documentation alongside code changes
- Run manual testing to verify behavior

### 3. Testing Phase
- Test both **Standard view** (3-column) and **Detailed view** (6-column)
- Verify exports work in all formats (CSV, PDF, Word, Graphics)
- Test label editing and persistence
- Check version displays correctly in window title
- Test all tabs: Controls Table, Device View, Config, About
- **For device detection work:** Test with actual hardware if available

### 4. Documentation Phase
- Update `docs/CHANGELOG.md` under `[Unreleased]` section with changes
- Update `README.md` if user-facing functionality changed
- Update `docs/DEVELOPMENT.md` if build/setup changed
- Add comments only where logic isn't self-evident

### 5. Commit & Review Phase
- Draft commit message summarizing the change
- **Show commit message for review** before committing
- Create clear, descriptive commits (avoid "Fix stuff")
- Use conventional commit format when appropriate

### 6. Version Management
No version increment needed until release is ready. When releasing:
- **Patch** (0.8.2 → 0.8.3): Bug fixes only
- **Minor** (0.8.2 → 0.9.0): New features or device support
- **Major** (0.8.2 → 1.0.0): Breaking changes or major rewrites

---

## Project Overview

**SC Profile Editor** is a desktop application for Star Citizen players to edit and export their control profiles in human-readable formats. It generates visual diagrams of controller layouts and exports bindings to PDF, Word, CSV, and graphical formats.

- **Platform:** Windows only (PyInstaller executable)
- **Language:** Python 3.12+
- **GUI Framework:** PyQt6
- **Current Version:** 0.8.2 (released 2026-02-07)
- **Status:** Active development

---

## Project Architecture

### High-Level Data Flow

```
Load Profile (XML)
    ↓
Parse XML → Detect Devices → Generate Labels → Display Table
    ↓
Apply Device Mappings & Template Selection
    ↓
Edit Labels → Save Overrides → Update Device View & Table
    ↓
Export → Apply Filters & View Mode → Generate Output (CSV/PDF/Word/PNG)
```

### Core Components

#### 1. **Action Registry System** (`src/registry/action_registry.py`)
- Loads complete action database from `UNBIND_ALL.xml` (1,085 actions across ~50 actionmaps)
- Loaded at startup, indexed by action name and organized by category
- Used for: dropdown suggestions, action validation, label generation
- The BLANK profile (`example-profiles/BLANK.xml`) extends this with all 1,085 actions

#### 2. **Parser & Label Generation** (`src/parser/`)
- `xml_parser.py`: Parses Star Citizen profile XML files, extracts bindings and actionmaps
- `label_generator.py`: Creates human-readable labels for actions using three-tier system (see below)

#### 3. **Label Override System** (`src/utils/label_overrides.py`)
- **Tier 1 (Custom)**: User-edited labels stored in `label_overrides_custom.json` (AppData)
- **Tier 2 (Global)**: Default labels in `label_overrides.json` (bundled with app)
- **Tier 3 (Auto-generated)**: Fallback from action name if no override exists
- Labels update in **real-time** across table and device graphics

#### 4. **Device Graphics System** (`src/graphics/`, `src/gui/qtpdf_device_widget.py`)
- PDF-based device templates with interactive form fields
- QtPdf (native Qt renderer) for lightweight PDF viewing (no Chromium)
- PyMuPDF (fitz) for PDF manipulation and form field access
- Pattern-based device matching in `visual-templates/template_registry.json`
- Supports **composite devices** (stick + module) via `device_splitter.py`
- Clickable PDF fields open RemapDialog for action assignment

#### 5. **Input Detection System** (`src/utils/input_detector.py`)
- **Joystick**: Buttons, axes, POV/hat switches via `pygame`
- **Keyboard**: Keys with modifier support (Ctrl, Alt, Shift) via `pynput`
- **Mouse**: Button clicks (5-button mice) via `pynput`
- Integrated into RemapDialog for convenient rebinding
- 10-second timeout with cancel option
- Thread-safe with Qt signal/slot architecture

#### 6. **Main Window & Tabs** (`src/gui/main_window.py`)
- **Controls Table Tab**: Filterable, sortable table of all bindings (two view modes)
- **Device View Tab**: Interactive PDF with labeled buttons (updates in real-time)
- **Config Tab**: Device detection, device-to-joystick mapping, SC profiles directory
- **About Tab**: Project info and acknowledgements
- System tray integration (minimize-to-tray with optional disable)

#### 7. **Exporters** (`src/exporters/`)
- CSV, PDF, Word, and PNG/PDF graphic exports
- Respect current view mode (Standard or Detailed) and active filters
- All include profile info and device lists

### Supported Devices
- **VKB:** Gladiator (EVO/SCG), Gunfighter (MCG/SCG), Space Sim Module (SEM), Throttle Quadrants, F16 MFD, STECS
- **VPC:** MongoosT-50CM3
- **Thrustmaster:** T.16000M, TWCS Throttle

---

## Key Commands

```bash
# Development
python src/main.py                                # Run app locally

# Build Executable
python scripts/build/build_exe.py                # Build without version bump
python scripts/build/build_exe.py --increment patch   # Build + patch version bump
python scripts/build/build_exe.py --increment minor   # Build + minor version bump
python scripts/build/build_exe.py --increment major   # Build + major version bump

# Build Installer (requires Inno Setup 6)
cmd //c scripts\build\build_installer.bat       # Build installer only (exe must exist)
cmd //c scripts\build\build_all.bat             # Build both exe and installer

# Testing
# (No automated test suite - see Testing Guide section below)
```

---

## Important Files & Locations

### Core Documentation
- `CLAUDE.md` - This file (AI assistant guide)
- `README.md` - End-user guide (also displayed in app's About tab)
- `VERSION.TXT` - Current version (e.g., "0.8.2")
- `docs/CHANGELOG.md` - Version history and release notes
- `docs/DEVELOPMENT.md` - Developer setup and build instructions
- `docs/RELEASE_PROCESS.md` - Complete release workflow checklist

### Configuration Files
- `label_overrides.json` - Global default labels (bundled with app, 72 common actions)
- `label_overrides_custom.json` - User custom labels (stored in AppData, persists across sessions)
- `visual-templates/template_registry.json` - Device template definitions and patterns

### Key Source Directories
```
src/
├── main.py                           # Application entry point, logging setup
├── gui/
│   ├── main_window.py               # Main window, all four tabs, exports
│   ├── qtpdf_device_widget.py       # PDF device viewer (QtPdf-based, native Qt)
│   ├── remap_dialog.py              # Button remapping dialog with input detection
│   ├── config_tab.py                # Device management and device-to-joystick mapping
│   ├── control_editor.py            # [Used internally by table editing]
│   └── input_filter_dialog.py       # Input detection filter dialog
├── parser/
│   ├── xml_parser.py                # SC profile XML parsing
│   └── label_generator.py           # Human-readable label generation
├── exporters/
│   ├── csv_exporter.py              # CSV export
│   ├── pdf_exporter.py              # PDF export
│   ├── word_exporter.py             # Word document export
│   ├── graphic_exporter.py          # PNG/PDF graphic export
│   └── xml_exporter.py              # XML profile export (for saving modified profiles)
├── graphics/
│   ├── pdf_template_manager.py      # PDF template loading and caching
│   └── template_manager.py          # [Legacy, check if still used]
├── models/
│   └── profile_model.py             # Data structures: Binding, Action, ControlProfile
├── registry/
│   └── action_registry.py           # Action database from UNBIND_ALL.xml
└── utils/
    ├── settings.py                  # Application settings persistence (QSettings)
    ├── label_overrides.py           # Label override manager (custom + global)
    ├── input_detector.py            # Input detection (joystick, keyboard, mouse)
    ├── device_joystick_mapper.py    # Device-to-joystick mapping storage
    ├── device_splitter.py           # Composite device handling (stick + module)
    ├── input_validator.py           # Input code validation
    ├── version.py                   # Version management utilities
    └── single_instance.py           # Ensure only one app instance runs

visual-templates/                    # Device template resources
├── template_registry.json          # Device definitions, patterns, button mappings
└── [device_id]/                    # Per-device folders
    └── *.pdf                       # PDF template with fillable form fields

scripts/build/                      # Build automation
├── build_exe.py                    # Standard PyInstaller build script
├── build_all.bat                   # Batch script: build exe + installer
├── build_installer.bat             # Batch script: build installer only
├── BUILD_INSTRUCTIONS.md           # How to use build scripts
└── discord_notify.py               # Discord release notifications

example-profiles/                   # Sample Star Citizen profiles
├── BLANK.xml                       # Master template with all 1,085 actions
└── [preset profiles]               # Pre-configured starting points

deprecated/                         # Old code (SVG/PNG/OCR system, removed in v0.4.0)
├── gui/
├── graphics/
├── scripts/
└── template_files/
```

---

## Code Patterns & Conventions

### Label System (Three-Tier Priority)
1. **Custom** - User's personal label overrides (stored in AppData)
2. **Global** - Default labels bundled with app (72 common actions)
3. **Auto-generated** - Fallback using action name if no override exists

```python
# Labels update in real-time across table and device graphics
# When user edits a label:
# 1. Save to custom overrides JSON
# 2. Emit signal to update table
# 3. Emit signal to update device view PDF
```

### Device Template System
- PDF-based templates with interactive form fields
- QtPdf for native rendering (no Chromium dependency)
- PyMuPDF for PDF field access and manipulation
- Pattern-based device matching (supports wildcards and multiple patterns)
- Automatic button range detection and mapping
- Composite device support via `device_splitter.py` (e.g., stick + SEM module)

### Input Detection
- Joystick buttons/axes via `pygame` event pumping
- Keyboard keys via `pynput` (supports modifiers: Ctrl, Alt, Shift)
- Mouse buttons via `pynput` (5-button mice supported)
- 10-second timeout with cancel option
- Thread-safe with Qt signals for UI updates

### Settings Persistence
- Uses PyQt6's `QSettings` (stored in Windows registry for this user)
- Auto-saves window geometry, last opened profile, view settings
- See `src/utils/settings.py` for AppSettings class

### Resource Paths (PyInstaller Compatibility)
```python
# Handles both dev and packaged execution
def get_resource_path(relative_path):
    try:
        base_path = sys._MEIPASS  # PyInstaller temp folder
    except:
        base_path = os.path.dirname(...)  # Dev path
    return os.path.join(base_path, relative_path)
```

### Single Instance Management
- `src/utils/single_instance.py` ensures only one app instance runs
- Uses Windows mutex pattern for process locking
- Prevents duplicate windows and file lock conflicts

---

## Testing Guide

### Manual Testing Checklist

Before submitting changes, test the following:

**App Launch & Basic Operations**
- [ ] App runs: `python src/main.py` (no errors)
- [ ] Window title shows correct version (e.g., "v0.8.2")
- [ ] Window geometry persists across restarts
- [ ] System tray icon appears when minimized

**Profile Loading & Display**
- [ ] Load a profile - table populates with correct binding count
- [ ] All four tabs load without errors
- [ ] Standard view (3-column) displays: Action, Label, Input, Device
- [ ] Detailed view (6-column) displays: All above plus Code and Action Name
- [ ] Toggle "Show Detailed" - columns appear/disappear correctly

**Filtering & Searching**
- [ ] Text search filters rows correctly (searches all columns)
- [ ] Device filter shows/hides rows by device
- [ ] Action Map filter shows/hides rows by category
- [ ] "Hide Unmapped Keys" filters properly
- [ ] "Clear Filters" resets all filters and view options
- [ ] Filters persist when toggling Standard/Detailed view

**Label Editing**
- [ ] Double-click label cell - text auto-selects
- [ ] Type new label - change appears immediately
- [ ] Press Enter - change persists in table
- [ ] Device View updates in real-time
- [ ] Delete label (press Delete) - reverts to global/auto-generated label
- [ ] Custom labels persist across profile loads (global to all profiles)

**Device View Tab**
- [ ] PDF displays without errors
- [ ] Device dropdown lists all available templates
- [ ] Switching devices updates PDF correctly
- [ ] Button labels display on PDF
- [ ] Labels update when you edit them in Controls Table
- [ ] Clicking a PDF button opens RemapDialog (if implemented)

**Input Detection**
- [ ] Remap Dialog opens on pencil icon click
- [ ] "Detect Input" button works:
  - [ ] Press joystick button - detects correctly
  - [ ] Press keyboard key - detects correctly (letter, number, function keys)
  - [ ] Press with modifiers (Ctrl+A, Alt+P, Shift+Down) - detects correctly
  - [ ] Press mouse button - detects correctly
- [ ] "Change Input Binding" dropdown has searchable list
- [ ] Detects and applies device mappings from Config tab

**Config Tab**
- [ ] "Refresh Devices" detects connected input devices
- [ ] "Connected Devices" lists keyboard, mouse, and joysticks
- [ ] Device-to-Joystick Mapping shows available slots (js1, js2, js3)
- [ ] "Auto-Populate" assigns connected joysticks
- [ ] "Save Configuration" persists mappings
- [ ] Device mappings apply to new profiles after save

**Exports**
- [ ] Export to CSV - file created, opens in Excel, data looks correct
- [ ] Export to PDF - formatting looks correct, includes profile info
- [ ] Export to Word - formatting looks correct, table renders properly
- [ ] Export Graphic - PNG/PDF created with labels visible
- [ ] Exports respect current view mode (Standard or Detailed)
- [ ] Exports respect active filters (only shows filtered rows)

**Device-Specific Testing** (when applicable)
- [ ] Device detection works in Device Mapper (Config tab)
- [ ] Device mapping persists across profile loads
- [ ] Clicking buttons on Device View PDF opens dialog
- [ ] Device View labels match custom overrides

### Testing with Hardware

If testing device detection or input detection:
1. Connect physical device (joystick, keyboard, mouse)
2. In Config tab: Click "Refresh Devices" - device should appear
3. In Remap Dialog: Click "Detect Input" - click physical button/key
4. Verify correct input code appears

---

## Debugging Tips

### Enable Logging
Logging is configured in `src/main.py`:
```python
def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
```

Increase verbosity in `main.py` by changing `logging.INFO` to `logging.DEBUG` for more detailed output.

### Debug Input Detection Issues
- Check `src/utils/input_detector.py` for pygame event handling
- Verify device is detected in Config tab before testing input detection
- Enable pygame logging to see event queue:
  ```python
  import os
  os.environ['SDL_AUDIODRIVER'] = 'dummy'  # Disable audio for testing
  ```

### Debug Device Template Loading
- Check that `visual-templates/template_registry.json` exists and is valid JSON
- Verify device pattern matches profile's device name (case-sensitive)
- In `src/graphics/pdf_template_manager.py`, add logging to `get_template_path()`
- Ensure PDF files exist in matching directory under `visual-templates/`

### Debug Label Override Issues
- Check `label_overrides.json` (bundled) vs `label_overrides_custom.json` (AppData)
- AppData path: `C:\Users\{user}\AppData\Local\SC Tools\...`
- Verify JSON is valid if manually editing
- Clear AppData custom file to reset to defaults

### Debug XML Parsing Issues
- Check that profile XML is valid Star Citizen format
- In `src/parser/xml_parser.py`, add logging around binding extraction
- Compare with example profiles in `example-profiles/` folder

### Debug Build Issues
- Ensure `VERSION.TXT` exists in project root
- Check that all bundled resources are included in PyInstaller spec
- Clear `build/` and `dist/` directories before rebuilding
- Verify `requirements.txt` dependencies are installed: `pip install -r requirements.txt`

---

## Recent Changes & Current Status

### v0.8.2 (Released 2026-02-07) - Current Stable Release
**Major Fixes:**
1. **XML Export Critical Fixes** - Bindings no longer lost when saving; ALL actions written to XML
2. **Device Detection** - Joystick devices now properly detected for all profiles
3. **Device View PDF Clicking** - PDF button clicking works reliably with proper device mappings
4. **Action Counting** - Fixed inflated counts from overlay system duplication

**Key Issues Addressed:**
- Duplicate actions no longer accumulate exponentially on save/reload
- Device filter no longer hides unmapped actions (fixed in earlier patch)
- Device-to-Joystick mapping UI improved with better layout
- Device detection UI now shows device count correctly

### Development Branch (vkb-sem-fixes)
**In Progress:**
- VKB Space Sim Module (SEM) mapping improvements
- Additional device template support
- UI enhancements (clear all button, file path display)

### Known Issues
- **Issue #14**: Button detection reporting all buttons as button 1 (diagnostic logging added, needs testing with hardware)
- **Issue #16**: Device View tab should work now that devices are detected (verify with hardware)

### Pending Features
- More device templates (additional Thrustmaster, Logitech, Virpil models)
- Profile comparison tool (see differences between two profiles)
- Auto-update mechanism
- Linux/macOS support (currently Windows-only)

---

## Best Practices

### Code Quality
- Keep changes focused and minimal
- Avoid over-engineering (single-use code > premature abstractions)
- Only add comments where logic isn't self-evident
- Delete unused code completely (no `# removed` comments)

### Git Workflow
- Create descriptive commit messages that explain the "why"
- Use conventional commit format when appropriate
- Commit frequently (logical, reviewable chunks)
- Never skip pre-commit hooks

### Documentation
- Update `docs/CHANGELOG.md` alongside code changes
- Keep `README.md` aligned with actual user workflow
- Document new features in `docs/DEVELOPMENT.md`
- Keep `CLAUDE.md` current with project state

### Testing
- Test both view modes (Standard and Detailed)
- Test all export formats
- Test on Windows (primary platform)
- Test with actual hardware when doing input detection work

### Building & Releasing
- Use `build_exe.py` with `--increment` flag for version bumps
- Always test built executable before releasing
- Update `docs/CHANGELOG.md` before each release
- See `docs/RELEASE_PROCESS.md` for complete workflow

---

## When You Get Stuck

1. **Check existing code** - Look at similar implementations in the codebase
2. **Review docs/** - Check DEVELOPMENT.md for troubleshooting
3. **Check git history** - `git log -p` shows how similar features were implemented
4. **Check memory** - See `C:\Users\aabou\.claude\projects\C--Users-aabou-PycharmProjects-OsirisDevworks-sc-profile-editor\memory\` for session context
5. **Ask for clarification** - Use AskUserQuestion to align on approach before implementing

---

## Related Projects

Cross-reference patterns from other Osiris Devworks projects:

- **citizen-bot** (Discord bot) - Planning required for non-trivial features, unit tests, feature branch workflow
- **sc-localization-editor** (Python + PyQt6) - Similar architecture, QSettings persistence, PyInstaller build process
- **battlestations.sc** (React frontend) - Strict naming conventions, comprehensive guidelines

---

**Last Updated:** 2026-03-25
**Version:** 0.8.2
