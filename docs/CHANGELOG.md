# Changelog

**Version:** 0.6.1
**Date:** 2025-12-04
**For:** Users and developers - Version history and release notes

All notable changes to SC Profile Editor will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.2] - 2025-12-24

### Added
- **Virpil MongoosT-50CM3 Device Support** - Complete templates for left and right stick variants:
  - VPC MT-50CM3 (Left) - 32-button joystick template with slider control
  - VPC MT-50CM3 (Right) - 32-button joystick template with slider control
  - Interactive PDF templates with form fields for all button mappings
  - Comprehensive device matching patterns for various device name variations
  - Full field_mapping.json files with button-to-axis mappings
- **Single Instance Protection** - Application now prevents multiple instances:
  - Warning dialog if user tries to launch app while it's already running
  - Brings existing window to focus if another instance is attempted
  - Uses Qt LocalServer for cross-platform support

### Changed
- **Template Registry**: Updated with Virpil device entries and field mapping references
- **Device Template Build**: Now includes 21 device templates (up from 19)

## [0.7.1] - 2025-12-23

### Added
- **System Tray Integration** - Minimize-to-tray functionality:
  - New "System Tray" section in Config tab to enable/disable minimize-to-tray behavior
  - Minimize-to-tray setting defaults to disabled for backward compatibility
  - System tray icon always visible when app is running
  - Right-click tray menu with "Show" and "Exit" options
  - Click tray icon to restore window from tray
  - Notification balloon on first minimize-to-tray (educates users about the feature)
  - Tray icon setting persisted across app restarts

### Fixed
- **Device template matching** - Fixed T.16000M and TWCS duplicate templates:
  - Removed overly broad "T.16000M Throttle" pattern from TWCS Throttle template
  - Device matching now more precise, preventing false template matches
  - Device View dropdown now shows correct number of templates (T.16000M and TWCS separately, not duplicated)
- **Device extraction** - Fixed device detection for preset profiles:
  - Enhanced get_devices() to extract from `<options>` elements in `<ActionProfiles>` for preset profiles
  - Preset profiles without CustomisationUIHeader now correctly extract T.16000M and TWCS devices
  - Device View properly populates and displays templates for preset configurations
- **Input Binding Dialog Layout** - Reorganized RemapDialog for better UX:
  - Moved "Current Actions for This Button" section to top of dialog (better visual flow)
  - Moved "Change Input Binding" section below "Current Actions" (logical flow)
  - Swapped "Detect Input" and "Select manually" order - dropdown now comes first
  - "Detect Input" button now positioned to the right of dropdown (closer to OK button)
  - Improved overall dialog usability

### Changed
- **Window icon** - Set application window icon to match system tray icon for visual consistency

## [0.7.0] - 2025-12-12

### Added
- **Thrustmaster Device Templates** - Initial support for Thrustmaster HOTAS systems:
  - Thrustmaster T.16000M FCS Joystick - Complete with 16 buttons, hat switch, and 6-axis support
  - Thrustmaster TWCS Throttle Unit - Complete with 14 buttons, hat switch, and 4-axis support
  - Both templates include comprehensive field_mapping.json for button/axis mapping
- **Build System Enhancements**:
  - `.build-ignore` file support for excluding incomplete templates from builds and installers
  - Installer now copies from build output (dist/) instead of source, ensuring only complete templates are packaged
  - Incomplete templates remain in repository for future 0.7.x releases
- **Documentation Improvements**:
  - Comprehensive field_mapping.json documentation for complex button layouts and custom mappings
  - .build-ignore file usage guide for managing template development lifecycle
  - v0.7.0 Development Plan with completion workflow for remaining devices
  - Consistent Version/Date/For headers across all documentation
  - Clarified template completion workflow in CREATING_PDF_TEMPLATES.md

### Changed
- **Template Registry** - Updated to include new Thrustmaster device patterns for device matching
- **Development Workflow** - Established clear separation between complete (released) and incomplete (0.7.x development) templates

### Known Limitations for Future Releases (0.7.x)
Remaining incomplete device templates planned for 0.7.x versions (marked with `.build-ignore`):
- VKB STECS Throttle with variants (ATEM, Space Throttle Grip Left/Right, STEM module)
- VKB Throttle Quadrant V (standard and WW2 module)
- Virpil MongoosT-50CM3 (Left and Right stick variants)
These templates have PDF assets and need field mapping refinement before inclusion.

## [0.6.1] - 2025-12-03

### Added
- **Keyboard modifier support** - Full support for Ctrl, Alt, and Shift key modifiers:
  - Detect and generate modifier key combinations (Ctrl+A, Alt+P, Shift+Down, etc.)
  - Support for left and right modifier keys (lctrl, rctrl, lalt, ralt, lshift, rshift)
  - Automatic detection when using "Detect Input" button in RemapDialog
  - Correct handling of Ctrl+letter combinations (maps control characters back to letters)
  - Support for AltGr (Right Alt) on non-US keyboards
  - Input codes format: `kb1_{modifier}+{key}` (e.g., `kb1_lctrl+a`)
  - Human-readable display: "Keyboard Left Ctrl+A", "Keyboard Right Alt+P", etc.
- **Device Configuration Tab** (new "Config" tab):
  - View all connected devices with type, product name, and instance number
  - "Refresh Devices" button to re-detect connected devices
  - Configure device-to-joystick mappings (js1, js2, js3, etc.)
  - "Auto-Populate from Connected Devices" button to automatically map connected joysticks
  - "Save Configuration" button to persist device mappings to settings
  - Star Citizen profiles directory configuration with browse button
  - Helps maintain consistent bindings when devices connect in different order
- **Device hot-swap detection** - Devices plugged in after app startup are now detected:
  - Pygame joystick module reinitialized on each device refresh
  - Disconnected devices completely removed from connected list (no "(unavailable)" placeholders)
  - Device mapping automatically cleaned when devices disconnect
- **Device View enhancements**:
  - Always show profile devices with [DISCONNECTED] suffix when not connected
  - Warning popup when loading profile with disconnected devices
  - Status bar shows connection count (e.g., "3/5 connected")
  - "Show all templates" toggle to view unsupported devices (for manual selection)
- **Device View UX improvements**:
  - Hide "Change Input Binding" section when editing from Device View (input already determined by button clicked)
  - Cleaner, more focused dialog for managing actions on a specific button
- **Action rebinding dialog enhancements**:
  - Three-option dialog: Move, Duplicate, or Cancel
  - Move: Remove action from original button and bind to new one
  - Duplicate: Keep action on original button and add to new one (supports Star Citizen's multi-button mappings)
  - Makes it clear what action is being taken when rebinding
- **Duplicate action deduplication**:
  - Remove duplicate actions from "ALL" category dropdown
  - Remove duplicate actions from individual category dropdowns
  - Same action appearing in multiple maps or with multiple bindings now shown only once
  - Cleaner action selection experience with 585 unique actions instead of 621

### Fixed
- Fixed keyboard input detection that stopped working when editing mappings from control table (modal dialogs suppressed pynput listeners)
- Fixed joystick input detection to use pygame instead of unavailable python-dinput
- Fixed control table showing wrong device (now uses actual connected hardware instead of profile device)
- Fixed device filter missing keyboard and mouse options (now always shown)
- Fixed input detection not applying device mapping from Config tab (detected input now remapped based on configuration)
- Fixed Ctrl+letter modifier detection that was mapping to control characters (showing as squares/rectangles)
- Fixed AltGr (Right Alt on non-US keyboards) blocking regular key input detection
- Fixed duplicate actions appearing in "ALL" and category action dropdowns
- Fixed disconnected devices not being removed from mapping list (now completely removed when device disconnect detected)
- Fixed device not appearing in list after hot-plugging (now redetects on each refresh)

## [0.6.0] - 2025-11-19

### Added
- **Table-based input binding** - Direct input editing from Controls Table view:
  - New "Label" column for editable action labels (double-click to edit)
  - New "Input" column showing human-readable input descriptions with raw codes in tooltip
  - New "Edit" column with pencil icon buttons for each row
  - Click Edit button to open RemapDialog for that specific input/action
  - Supports full multi-action button editing from table interface
- **Enhanced RemapDialog with input selection**:
  - "Change Input Binding" group box at top of dialog
  - "Detect Input" button for automatic input detection
  - Searchable dropdown with all available inputs organized by device type
  - Manual input code selection from comprehensive list of keyboard, mouse, and joystick inputs
  - Automatically updates Device column when input binding changes
- **Device Configuration Tab** (new "Config" tab):
  - View all connected devices with type, product name, and instance number
  - "Refresh Devices" button to re-detect connected devices
  - Configure device-to-joystick mappings (js1, js2, js3, etc.)
  - "Save Configuration" button to persist device mappings to QSettings
  - Helps maintain consistent bindings when devices connect in different order
- **New Profile button**:
  - Quick create new profile from blank.xml without file dialog
  - Useful for starting fresh profiles with all 621 available actions
  - Default filename pattern suggested for new profiles
- **Device configuration persistence**:
  - New settings methods: get_device_config(), set_device_config(), clear_device_config()
  - Device mappings stored in QSettings for persistence across sessions

### Changed
- **Table column restructure**:
  - Renamed "Action Map" column to "Action Category"
  - Consolidated input display: removed separate "Input Code" and "Input Label" columns
  - New single "Input" column shows human-readable text with raw code in tooltip
  - Default view now includes: Action Category, Label, Input, Device, Edit (5 columns)
  - Detailed view adds original "Action" column (6 columns)
- **RemapDialog improvements**:
  - Now accepts input_code string parameter instead of binding object
  - Uses bindings_changed signal (plural) for consistency with multi-action support
  - Context menu updated to use new RemapDialog API
- **Main window toolbar**:
  - "New Profile" button added between "Import Profile XML" and export buttons

### Fixed
- **Context menu remapping** - Updated to use bindings_changed signal from RemapDialog

### Technical
- All input code dropdown items generated dynamically from available devices
- Input codes include: keyboard (99 keys), mouse (7 buttons), joystick buttons/axes/hats
- Device auto-update works automatically when UI refreshes after input change

---

## [0.5.1] - 2025-11-18

### Added
- **Multi-action button tooltips** - Buttons with multiple actions now display a tooltip showing all assigned actions
- **Enhanced action list in BLANK profile** - Added 564 missing actions from other profiles:
  - Profile now includes all 621 actions across 39 action maps
  - Enables full action discovery when mapping buttons in any profile
- **Action label truncation** - Long action labels in table view are now truncated with ellipsis when they exceed cell width
  - Allows viewing full label by hovering over truncated text

### Fixed
- **Fixed rebind warning for unbound actions** - Unbound actions (with input ending in underscore like "js1_ ") no longer trigger rebind confirmation dialog:
  - Only shows warning when action is actually bound to a different input
  - Uses `rstrip()` to properly detect unbound actions with trailing whitespace
- **Improved stability** - Added comprehensive debug logging throughout RemapDialog for better crash diagnostics

### Changed
- **BLANK profile renamed** - Changed from `layout_BLANK_exported.xml` to `blank.xml` for consistency
- **Tooltip behavior tuning** - Improved multi-action button tooltip display and duplicate mapping handling

---

## [0.5.0] - 2025-11-14

### Added
- **Input detection feature** - Users can now detect inputs with a "Detect Input" button in the remap dialog:
  - Automatically detects joystick button presses and axis movements
  - Detects keyboard key presses
  - Detects mouse button clicks
  - Supports 10-second detection timeout with cancel option
  - Uses lightweight python-dinput (joystick) and pynput (keyboard/mouse) libraries

### Changed
- **Dependency updates** - Replaced pygame with lighter alternatives:
  - Removed: pygame (20-30 MB)
  - Added: python-dinput (~2 MB) for Windows joystick detection
  - Added: pynput (~3 MB) for keyboard and mouse detection
- **Removed WebEngine modules** - Dropped unused Chromium-based PDF viewer:
  - Removed QtWebEngine and QtWebChannel from build (saves ~150 MB)
  - Application now uses QtPdf exclusively for PDF viewing
  - Reduced installer size from 256 MB to ~110 MB (57% reduction!)
- **Build optimization** - Excluded 25+ unused Qt6 modules:
  - Removed: QtTest, QtSql, QtBluetooth, QtNfc, Qt3D*, QtCharts, QtDataVisualization, QtMultimedia, QtPositioning, QtSensors, QtSerialPort, QtSvg, QtQuick, QtQml, QtHelp, QtDesigner, QtDBus, QtRemoteObjects, QtWebSockets, QtLocation, QtOpenGL

### Removed
- **Deleted webengine_pdf_widget.py** - No longer needed after WebEngine removal
- **Removed pygame dependency** - Was not actually used by the application

---

## [0.4.0] - 2025-11-12

### Added
- **About tab** - New tab with project information, Osiris DevWorks placeholder, and acknowledgements:
  - GurningBoose, Hawkwar, Nazgul-Five 'Maverick', Tichro 'BreakPoint', UntoldForce
- **Expanded VKB PDF template library** - Added 19 new VKB device PDF templates:
  - VKB Gladiator SCG (LH/RH, OTA-LH/OTA-RH variants)
  - VKB Gunfighter SCG (LH/RH, OTA-LH/OTA-RH variants)
  - VKB SEM-V variant
  - VKB STECS throttle system (base unit, STEM, ATEM, SpaceThrottleGrip LH/RH)
  - VKB THQ-V, THQ-WW2, THQ-V-WW2 variants

### Changed
- **UI Simplification** - Consolidated device graphics interface:
  - Renamed "Device Graphics (Interactive)" to "Device View"
  - Removed redundant "Device Graphics (SVG)" and "Device Graphics (PDF)" tabs
  - Now uses single interactive PDF viewer for all device graphics
- **Updated tab structure** - Three tabs total: Controls Table, Device View, About
- **Save Profile button** - Now always visible but disabled when no changes made (previously hidden)
- **Documentation restructure** - Reorganized documentation files:
  - README.md now serves as user guide (previously USER_GUIDE.md)
  - Developer documentation moved to docs/DEVELOPMENT.md
  - All .md files except README.md moved to docs/ directory

### Deprecated
- **SVG/PNG template system** - Replaced with PDF-only system
  - Moved deprecated files to `deprecated/` directory:
    - `device_graphics.py` (SVG widget)
    - `pdf_device_graphics_widget.py` (static PDF widget)
    - `ocr_annotator.py` (OCR utilities)
    - `svg_generator.py` (SVG generation)
    - `detect_button_coordinates.py` (OCR-based coordinate detection)
    - All `.png` and `_overlay.svg` template files
- **OCR build configuration** - Removed build_exe_with_ocr.py (no longer needed)
- **Cleaned template_registry.json** - Removed `image` and `overlay` keys (SVG/PNG references)

### Technical
- Updated all documentation (README.md, CLAUDE.md) to reflect PDF-only system
- Simplified build process to single standard build script

## [0.3.0] - 2025-01-08

### Added
- **Expanded device template support** - Added templates for additional VKB devices:
  - VKB F16 MFD (Multi-Function Display)
  - VKB Throttle Quadrant (THQ)
  - VKB Gunfighter MCG Ultimate (MCGU) joystick
- Added example profile (`example-profiles/layout_19APR2025_exported.xml`) for testing

### Changed
- Cleaned up visual-scratch directory (removed temporary development images)
- Updated .gitignore to exclude visual-scratch directory

## [0.2.1] - 2025-10-28

### Fixed
- Fixed label edit loss when toggling "Show Detailed" checkbox during active edit
  - Edits are now properly committed before view mode changes
  - Prevents confusion when reverting to default labels
- Fixed issue with device and action map filters not being preserved when toggling "Show Detailed" checkbox
- Fixed issue with label editing window text bleed-through
- Fixed issue restoring default text in label
- Support for buttons with multiple mappings

### Changed
- Updated CHANGELOG documentation to clarify device template support status (VPC MongoosT-50CM3 Left and Thrustmaster TWCS Throttle are stubs)

## [0.2.0] - 2025-10-26

### Added
- **Expanded device template support** - Added templates for additional HOTAS devices:
  - VKB Gladiator EVO Left (standalone and with Space Sim Module)
  - VKB Space Sim Module (SEM) as separate device
  - Virpil MongoosT-50CM3 Left stick stubs
  - Thrustmaster TWCS Throttle stubs
- Device splitter utility (`device_splitter.py`) for handling composite devices like VKB sticks with SEM modules
- Comprehensive device template creation documentation:
  - `CREATING_DEVICE_TEMPLATES.md` - Step-by-step guide for creating new device templates
  - `OVERLAY_CONVERSION.md` - Guide for converting Inkscape SVG overlays
- Utility scripts for template development:
  - `convert_inkscape_overlay.py` - Convert Inkscape SVG to template format
  - `embed_image_in_svg.py` - Embed device images in SVG overlays
  - `rescale_overlay.py` - Rescale overlay coordinates
- DEVICE_STATUS.md to track template development progress across devices

### Changed
- Updated .gitignore to exclude scratch/working directories and binary artifacts

## [0.1.1] - 2025-10-24

### Added
- Version management system with automatic version incrementing in build scripts
- Version display in window title, main header, and Help dialog
- CHANGELOG.md to track version history

### Changed
- Unified UI: Moved "Export Graphic" button to main header alongside other export buttons
- Export Graphic button now intelligently enables/disables based on graphic availability

### Fixed
- Fixed label edit loss when toggling "Show Detailed" checkbox during active edit
  - Edits are now properly committed before view mode changes
  - Prevents confusion when reverting to default labels
- Fixed label revert not working (deleting label text now properly reverts to global/auto-generated)
  - Removed incorrect text clearing on double-click that was interfering with revert
  - Labels now correctly fall back to global defaults or auto-generated names

### Removed
- Export Graphic button from Device Graphics tab (now in main header)
- Unused PyInstaller .spec files (now using Python build scripts exclusively)

## [0.1.0] - 2025-10-23

### Added
- Initial release of SC Profile Editor
- Import and parse Star Citizen control profile XML files
- Display control bindings in sortable, filterable table
- Edit action labels with custom overrides
- Export profiles to CSV, PDF, and Word formats
- Device graphics visualization with SVG overlay annotations
- Support for VKB Gladiator EVO joystick templates
- Automatic template-based graphic generation
- Filter controls by:
  - Search text (action, input, device)
  - Device type
  - Action map
  - Hide unmapped keys
- Toggle between default and detailed view modes
- Persistent settings (window geometry, last opened profile)
- Auto-load last opened profile on startup
- User guide with comprehensive documentation
- PayPal donation and Discord community links

### Technical Features
- PyQt6-based GUI
- ReportLab PDF generation
- python-docx Word document export
- SVG rendering and template system
- Custom label override system with JSON storage
- Label generator for human-readable action names
- Device template manager
- Settings persistence via QSettings

---

## Version Format

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR** version for incompatible API changes or major feature overhauls
- **MINOR** version for new functionality in a backward-compatible manner
- **PATCH** version for backward-compatible bug fixes

## How to Update This File

When making changes:

1. Add new entries under `[Unreleased]` in the appropriate category:
   - **Added** for new features
   - **Changed** for changes in existing functionality
   - **Deprecated** for soon-to-be removed features
   - **Removed** for now removed features
   - **Fixed** for any bug fixes
   - **Security** for vulnerability fixes

2. When releasing a new version:
   - Change `[Unreleased]` to `[X.Y.Z] - YYYY-MM-DD`
   - Add a new `[Unreleased]` section at the top
   - Update VERSION.TXT file
   - Create a git tag for the release

## Build Script Version Increment

Use the build scripts with the `--increment` flag to automatically update the version:

```bash
# Increment patch version (0.1.0 -> 0.1.1) for bug fixes
python scripts/build/build_exe.py --increment patch

# Increment minor version (0.1.0 -> 0.2.0) for new features
python scripts/build/build_exe.py --increment minor

# Increment major version (0.1.0 -> 1.0.0) for breaking changes
python scripts/build/build_exe.py --increment major
```
