# Star Citizen Profile Editor - Development Guide

**Version:** 0.6.1
**Date:** 2025-12-04
**For:** Developers - Setup, architecture, and development workflow

A desktop application for editing and converting Star Citizen control profile XML files into human-readable formats (PDF, Word, CSV) with annotated device graphics.

> **Note:** This guide is for developers. For end-user documentation, see [README.md](../README.md).

## Features

- Import Star Citizen XML control profiles
- Generate human-readable control mapping tables
- Create annotated device graphics (VKB Gladiator EVO, and more)
- Export to multiple formats: PDF, Word, CSV, PNG
- Edit control labels with persistent custom overrides
- Support for keyboard, mouse, and HOTAS devices
- Interactive PDF-based template system for device graphics
- Filter and search control bindings
- Auto-save last opened profile

## Project Structure

```
sc-profile-viewer/
├── src/                        # Source code
│   ├── main.py                # Application entry point
│   ├── gui/                   # GUI components (PyQt6)
│   │   ├── main_window.py    # Main application window
│   │   └── webengine_pdf_widget.py # Interactive PDF device viewer
│   ├── parser/                # XML parsing and label generation
│   │   ├── xml_parser.py     # SC profile XML parser
│   │   └── label_generator.py # Human-readable label generator
│   ├── exporters/             # Export modules
│   │   ├── csv_exporter.py   # CSV export
│   │   ├── pdf_exporter.py   # PDF export
│   │   ├── word_exporter.py  # Word document export
│   │   └── graphic_exporter.py # Graphics export
│   ├── graphics/              # Graphics and template management
│   │   └── pdf_template_manager.py # PDF template loader
│   ├── models/                # Data models
│   │   └── profile_model.py  # Control profile data structures
│   └── utils/                 # Utilities
│       ├── settings.py       # Application settings persistence
│       ├── label_overrides.py # Custom label override manager
│       └── version.py        # Version management utilities
├── scripts/                    # Build and utility scripts
│   └── build/                 # Build scripts
│       └── build_exe.py      # Standard build
├── visual-templates/          # Device graphics templates
├── example-profiles/          # Sample SC profile XML files
├── assets/                    # Application assets (icons, images)
├── tests/                     # Unit tests
├── label_overrides.json       # Global label overrides
├── VERSION.TXT                # Current version number
├── README.md                  # End-user documentation and user guide
└── docs/                      # Developer documentation
    ├── CHANGELOG.md           # Version history and changes
    ├── DEVELOPMENT.md         # This file
    ├── CLAUDE.md              # Project context for AI assistants
    ├── RELEASE_PROCESS.md     # Release workflow
    └── FILE_LOCATIONS.md      # File storage documentation
```

## Setup for Development

### Prerequisites
- Python 3.12 or higher
- Git (for version control)

### Installation Steps

1. **Clone the repository:**
   ```bash
   git clone <repository-url>
   cd sc-profile-viewer
   ```

2. **Create virtual environment:**
   ```bash
   python -m venv .venv
   ```

3. **Activate virtual environment:**
   ```bash
   # Windows
   .venv\Scripts\activate

   # Linux/Mac
   source .venv/bin/activate
   ```

4. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

## Running the Application

### Development Mode
```bash
python -m src.main
```

Or directly:
```bash
python src/main.py
```

## Version Management

The project uses [Semantic Versioning](https://semver.org/) (MAJOR.MINOR.PATCH).

### Current Version
The current version is stored in `VERSION.TXT` and is displayed in:
- Window title
- Main application header
- Help dialog

### Version Utilities
Located in `src/utils/version.py`:
- `get_version()` - Get current version
- `increment_version(version, type)` - Increment major/minor/patch
- `set_version(version)` - Update VERSION.TXT

### Updating the Version
You can update the version manually by editing `VERSION.TXT`, or use the build scripts with the `--increment` flag (see Building section below).

## Building Executables

### Standard Build

```bash
# Build without version increment
python scripts/build/build_exe.py

# Build and increment patch version (0.1.0 -> 0.1.1)
python scripts/build/build_exe.py --increment patch

# Build and increment minor version (0.1.0 -> 0.2.0)
python scripts/build/build_exe.py --increment minor

# Build and increment major version (0.1.0 -> 1.0.0)
python scripts/build/build_exe.py --increment major
```

**Output:** `dist/SCProfileViewer.exe`

### Version Increment Guidelines

- **Patch** (`--increment patch`): Bug fixes, minor tweaks ui tweaks, no new features
- **Minor** (`--increment minor`): New features, additional device support backward-compatible changes
- **Major** (`--increment major`): Breaking changes, major rewrites

### Build Process Details

The build scripts:
1. Display current version or increment if requested
2. Clean previous build artifacts
3. Bundle all required files (templates, assets, etc.)
4. Create standalone executable using PyInstaller
5. Place output in `dist/` directory

**Important Files Bundled:**
- `VERSION.TXT` - Version number
- `label_overrides.json` - Global label mappings
- `README.md` - User documentation and guide
- `assets/` - Icons and images
- `visual-templates/` - Device templates
- `example-profiles/` - Sample profiles

## Creating Installer Packages

> **TODO:** Document installer creation process when implemented

For distribution, you may want to create installer packages:
- Windows: Use NSIS, Inno Setup, or WiX
- macOS: Create .dmg or .pkg
- Linux: Create .deb, .rpm, or AppImage

## Testing

Run unit tests:
```bash
pytest tests/
```

Run tests with coverage:
```bash
pytest --cov=src tests/
```

## Release Process

See [RELEASE_PROCESS.md](RELEASE_PROCESS.md) for the complete release workflow.

## Development Workflow

### Adding New Features
1. Create feature branch: `git checkout -b feature/your-feature`
2. Implement changes
3. Update tests
4. Add entry to docs/CHANGELOG.md under `[Unreleased]`
5. Update README.md if user-facing changes
6. Submit pull request

### Bug Fixes
1. Create bugfix branch: `git checkout -b bugfix/issue-name`
2. Fix the issue
3. Add tests to prevent regression
4. Update docs/CHANGELOG.md
5. Submit pull request

## Technology Stack

- **Python 3.12+** - Programming language
- **PyQt6** - GUI framework
- **python-docx** - Word document generation
- **reportlab** - PDF generation
- **Pillow** - Image processing
- **PyInstaller** - Executable packaging
- **pytest** - Testing framework

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests
5. Update documentation
6. Submit pull request

## Troubleshooting

### Build Issues
- **Permission Error:** Close any running instances of the application
- **Import Error:** Ensure virtual environment is activated and dependencies are installed
- **Missing Files:** Check that all required assets are in the correct directories

### Development Issues
- **PyQt6 Import Error:** Reinstall PyQt6: `pip install --upgrade PyQt6`
- **Version Not Displaying:** Ensure VERSION.TXT exists in project root

## Documentation

- **README.md** - End-user documentation and guide (in-app Help)
- **docs/CHANGELOG.md** - Version history and changes
- **docs/ROADMAP.md** - Planned releases and device support roadmap
- **docs/CLAUDE.md** - Project context and AI assistant instructions
- **docs/DEVELOPMENT.md** - This file (developer guide)
- **docs/RELEASE_PROCESS.md** - Release workflow and checklist
- **docs/FILE_LOCATIONS.md** - File storage documentation

## License

TBD
