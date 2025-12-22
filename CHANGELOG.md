# Changelog

All notable changes to the Star Citizen Profile Editor project are documented in this file.

## [0.7.0] - 2025-12-22

### Added

#### Merge Default Bindings (Issue #6)
- **Auto-populate unmapped actions** - When loading profiles, automatically fill unmapped actions with Star Citizen's default bindings
- **User overrides defaults** - Custom user bindings always take priority over defaults; unmapped bindings (ending with `_`) are replaced with defaults
- **Configurable merge** - New "Default Bindings" toggle in Config tab to enable/disable merge behavior (enabled by default)
- **Bundled defaults** - Default bindings extracted from Star Citizen and bundled with the application for offline use
- **Maintenance script** - New `scripts/extract_sc_defaults.py` script to refresh defaults when Star Citizen updates

#### Load Preset Profiles (Issue #6 - Bonus Feature)
- **Preset profile loading** - New "Load Preset Profile" button to select and load pre-configured HOTAS profiles
- **Hardware-specific presets** - Includes profiles for:
  - **Thrustmaster**: Warthog, X52, X55, X56, G940, T.16000M (single, dual, with TWCS)
  - **VKB**: Gladiator (right/left/OTA), Gunfighter, STECS systems
  - **Generic HOTAS** layouts
- **Customizable starting point** - Load a preset and customize it as your new profile
- **Auto-mark as modified** - Loaded presets are automatically marked as modified to encourage customization

#### Infrastructure
- **Extended ProfileParser** - New merge logic with `_merge_default_bindings()` and `_find_or_create_actionmap()` methods
- **Extended ControlProfile model** - New `merged_defaults: bool` field to track if defaults were merged
- **AppSettings expansion** - New `get_merge_defaults_enabled()` and `set_merge_defaults_enabled()` methods
- **Build script updates** - Added `default-bindings/` folder to PyInstaller build configuration
- **Installer updates** - Added `default-bindings/` folder to Inno Setup installer configuration

### Changed
- **Version** - Updated from 0.6.1 to 0.7.0
- **Config Tab** - Added "Default Bindings" section with merge toggle checkbox
- **Main Window** - Updated profile loading to use merge setting and display merge status in status bar
- **README** - Updated to document new features and expanded feature list

### Technical Details

#### Default Bindings Workflow
1. User imports a profile or creates new profile
2. ProfileParser checks `use_bundled_defaults` setting (default: True)
3. Parser merges default actionmaps.xml with user profile
4. Unmapped user actions (ending with `_`) are replaced with defaults
5. User's custom bindings (non-underscore) always take priority

#### Preset Profile Discovery
1. App locates `default-bindings/presets/` directory
2. Lists all `.xml` files in directory
3. Converts filenames to friendly names for display (e.g., `layout_t16000m_dual.xml` → "T16000m Dual")
4. Allows user selection and loading
5. Loaded profile marked as modified for customization

#### PyInstaller Compatibility
- Handles both frozen and development execution contexts
- Default bindings path determined based on execution environment
- Supports both `sys._MEIPASS` (PyInstaller) and development directory structures

### Files Modified
- `src/parser/xml_parser.py` - Added merge logic and helper methods
- `src/models/profile_model.py` - Added `merged_defaults` field
- `src/utils/settings.py` - Added merge defaults settings methods
- `src/gui/config_tab.py` - Added default bindings merge toggle UI
- `src/gui/main_window.py` - Updated profile loading, added preset profile dialog
- `scripts/build/build_exe.py` - Added default-bindings to PyInstaller args
- `installer.iss` - Added default-bindings to Inno Setup file list
- `README.md` - Updated documentation and features list

### Files Added
- `scripts/extract_sc_defaults.py` - Utility to extract defaults from Star Citizen Data.p4k
- `default-bindings/actionmaps.xml` - Extracted default bindings
- `default-bindings/presets/*.xml` - Pre-configured HOTAS profiles (multiple files)

### Testing Notes
- Default bindings merge tested with user profiles containing unmapped actions
- Preset profile loading tested with all available presets
- Config tab toggle verified to persist across sessions
- Build scripts verified to include default-bindings folder in distribution

---

## [0.6.1] - Previous Release

(Earlier changelog entries for versions < 0.7.0 can be added here)
