# SC Profile Editor - Claude Development Workflow

**Last Updated:** 2026-03-20
**Project:** SC Profile Editor v0.8.2
**Tech Stack:** Python 3.12+, PyQt6, PyInstaller, Windows-only

---

## Session Protocol

**At the start of each session, always ask:**
> What would you like to work on today?

Wait for your explicit response before taking any action. This ensures alignment on priorities and scope.

---

## Development Workflow

### 1. Planning Phase
When tackling non-trivial changes:
- **Enter planning mode** to explore the codebase and design the solution
- Walk through the plan step-by-step
- **Iterate with you** until the full plan is approved
- Identify affected files, testing strategy, and documentation updates needed

### 2. Implementation Phase
- Implement changes step-by-step, checking in between logical blocks
- Keep changes focused and minimal (avoid scope creep)
- Follow existing code patterns and conventions
- Update relevant documentation alongside code changes
- Run manual testing to verify behavior

### 3. Testing Phase
- Test both **Standard view** (3-column) and **Detailed view** (6-column)
- Verify exports work in all formats (CSV, PDF, Word, Graphics)
- Test label editing and persistence
- Check version displays correctly in window title
- Test all tabs: Controls Table, Device View, Config, About
- **For device detection work:** Test with Thrustmaster T16000 + Throttle if available

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

## Key Commands

```bash
# Development
python src/main.py                     # Run app locally

# Build
python scripts/build/build_exe.py      # Build executable (no version bump)
python scripts/build/build_exe.py --increment patch   # Build + patch bump
python scripts/build/build_exe.py --increment minor   # Build + minor bump

# Installer (requires Inno Setup 6)
cmd //c scripts\build\build_installer.bat  # Build installer only
cmd //c scripts\build\build_all.bat        # Build exe + installer
```

---

## Important Files & Locations

### Core Documentation
- `VERSION.TXT` - Current version (e.g., "0.8.2")
- `README.md` - End-user guide (displayed in app's About tab)
- `docs/CHANGELOG.md` - Version history and release notes
- `docs/DEVELOPMENT.md` - Developer setup and build instructions
- `docs/CLAUDE.md` - This file, project context for AI assistants
- `docs/RELEASE_PROCESS.md` - Complete release workflow checklist

### Configuration
- `label_overrides.json` - Global default labels (bundled with app)
- `label_overrides_custom.json` - User custom labels (stored in AppData)
- `visual-templates/template_registry.json` - Device template definitions

### Code Structure
```
src/
├── main.py                    # Entry point
├── gui/
│   ├── main_window.py        # Main window, tabs, exports
│   ├── qtpdf_device_widget.py # PDF device viewer
│   └── remap_dialog.py       # Button remapping dialog
├── parser/
│   ├── xml_parser.py         # SC profile XML parsing
│   └── label_generator.py    # Human-readable labels
├── exporters/                # CSV, PDF, Word exporters
├── graphics/
│   └── pdf_template_manager.py # PDF template system
├── models/                   # Data models
└── utils/
    ├── device_splitter.py    # Composite device handling
    └── input_detector.py     # Joystick/keyboard/mouse detection

visual-templates/            # Device templates
├── template_registry.json   # Device configuration
└── [device_id]/
    └── *.pdf               # Device templates
```

---

## Code Patterns & Conventions

### Label System (Three-Tier Priority)
1. **Custom** - User's personal label overrides (AppData)
2. **Global** - Default labels bundled with app
3. **Auto-generated** - Fallback if no override exists

Labels update in real-time across table and device graphics.

### Device Template System
- PDF-based templates with interactive form fields
- QtPdf for native rendering (no Chromium)
- PyMuPDF for PDF field access
- Pattern-based device matching in `template_registry.json`
- Supports composite devices (stick + module) via device splitter

### Input Detection
- Joystick buttons/axes via `pygame` event pumping
- Keyboard keys via `pynput`
- Mouse buttons via `pynput`
- 10-second timeout with cancel option
- Thread-safe with Qt signals

### Data Flow
```
Load Profile → Parse XML → Detect Devices → Generate Labels → Display Table
                                    ↓
                         Apply Device Mappings
                                    ↓
Edit Labels → Save Overrides → Update Device View
                                    ↓
Export → Apply Filters → Generate Output (CSV/PDF/Word/PNG)
```

---

## Recent Changes (v0.8.2)

### Completed Fixes
1. **Duplicate Action Bindings** - Two-pass deduplication in on_bindings_changed_from_table()
2. **Device Mapping Not Applied** - New profiles now respect Device Mapping from Config tab
3. **Device Detection UI** - display_profile() called after devices are added
4. **Button Detection** - Comprehensive logging added for "all buttons as button 1" issue
5. **Device Filter Empty Table** - Only hide rows if device doesn't match filter
6. **Device-to-Joystick Mapping UI** - Improved layout with better spacing and minimum widths

### Pending Issues
- **Issue #14** - Button detection reporting all buttons as button 1 (diagnostic logging in place)
- **Issue #16** - Device View tab should work now that devices are properly detected

---

## Testing Checklist

Before submitting changes:
- [ ] App runs without errors: `python src/main.py`
- [ ] Load a profile - table populates correctly
- [ ] Filter by text, device, action map - rows show/hide properly
- [ ] Edit labels - changes persist and update Device View
- [ ] Standard view (3-column) displays correctly
- [ ] Detailed view (6-column) displays correctly
- [ ] Export to CSV - file created with correct data
- [ ] Export to PDF - formatting looks correct
- [ ] Export to Word - formatting looks correct
- [ ] Device View - PDF displays and clickable fields work
- [ ] Version displays in window title
- [ ] All four tabs work: Controls Table, Device View, Config, About

For device-specific testing (when applicable):
- [ ] Device detection works in Device Mapper (Config tab)
- [ ] Device mapping persists across profile loads
- [ ] Button detection with Thrustmaster T16000 works correctly
- [ ] Device View correctly shows mapped buttons

---

## Related Projects

Cross-reference patterns from other Osiris Devworks projects:

- **citizen-bot** (Discord bot)
  - Planning phase required for all non-trivial features
  - Unit tests written alongside implementation
  - Feature branch workflow with code review before merge
  - PostgreSQL database with migration scripts

- **sc-localization-editor** (Similar Python + PyQt6 desktop app)
  - Modular architecture (gui, models, parser, merger, utils)
  - QSettings for persistent configuration
  - Similar build process with PyInstaller + Inno Setup

- **battlestations.sc** (React frontend)
  - Strict naming conventions and data structures
  - Comprehensive Claude guidelines for consistency

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
- Update CHANGELOG.md alongside code changes
- Keep README.md aligned with actual user workflow
- Document new features in DEVELOPMENT.md
- Keep this file (CLAUDE.md) current with project state

### Testing
- Test both view modes (Standard and Detailed)
- Test all export formats
- Test on Windows (primary platform)
- Test with actual hardware when doing input detection work

---

## When You Get Stuck

1. **Check existing code** - Look at similar implementations in the codebase
2. **Review DEVELOPMENT.md** - May contain troubleshooting for common issues
3. **Check git history** - `git log -p` can show how similar features were implemented
4. **Ask for clarification** - Use AskUserQuestion to align on approach before implementing

---

## This Workflow

This document serves as the **authoritative guide for AI assistants** on how to work effectively with the SC Profile Editor codebase. It reflects patterns from across Osiris Devworks projects, tailored to the specific needs of this Windows-only PyQt6 desktop application.

Key principles:
- **Session start** - Always ask what to work on
- **Planning first** - Understand scope before coding
- **Iterative approach** - Check in step-by-step
- **Documentation driven** - Changes update docs alongside code
- **Minimal, focused** - Avoid scope creep and over-engineering
- **Testing thorough** - Both view modes, all export formats
