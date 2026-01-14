"""
Build script for SC Profile Editor
Creates a standalone executable using PyInstaller
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def clean_build_artifacts():
    """Remove previous build artifacts"""
    print("Cleaning previous build artifacts...")

    artifacts = [
        PROJECT_ROOT / "build",
        PROJECT_ROOT / "dist",
        PROJECT_ROOT / "SCProfileEditor.spec"
    ]

    for artifact in artifacts:
        if artifact.exists():
            if artifact.is_dir():
                shutil.rmtree(artifact)
                print(f"  Removed: {artifact}")
            else:
                artifact.unlink()
                print(f"  Removed: {artifact}")

def get_version():
    """Read version from VERSION.TXT"""
    version_file = PROJECT_ROOT / "VERSION.TXT"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0"

def build_executable():
    """Build the executable using PyInstaller"""
    print("\n" + "="*60)
    print("Building SC Profile Editor")
    print("="*60)

    version = get_version()
    print(f"Version: {version}\n")

    # Clean previous builds
    clean_build_artifacts()

    # Determine the correct path separator for --add-data based on OS
    # Windows uses ';', Linux/Mac use ':'
    sep = ';' if sys.platform == 'win32' else ':'

    # Define PyInstaller command
    cmd = [
        "pyinstaller",
        "--name=SCProfileEditor",
        "--onefile",
        "--windowed",
        "--icon=assets/icon.ico",

        # Add data files
        f"--add-data=VERSION.TXT{sep}.",
        f"--add-data=label_overrides.json{sep}.",
        f"--add-data=README.md{sep}.",
        f"--add-data=assets{sep}assets",
        f"--add-data=visual-templates{sep}visual-templates",
        f"--add-data=example-profiles{sep}example-profiles",

        # Hidden imports for PyQt6 modules
        "--hidden-import=PyQt6.QtPdf",
        "--hidden-import=PyQt6.QtPdfWidgets",
        "--hidden-import=pygame",
        "--hidden-import=pynput",

        # Collect all src submodules (fixes ModuleNotFoundError)
        "--collect-submodules=src",

        # Explicitly include src packages to ensure they're found
        "--hidden-import=src.parser",
        "--hidden-import=src.parser.xml_parser",
        "--hidden-import=src.parser.label_generator",
        "--hidden-import=src.models",
        "--hidden-import=src.models.profile_model",
        "--hidden-import=src.utils",
        "--hidden-import=src.utils.settings",
        "--hidden-import=src.utils.version",
        "--hidden-import=src.utils.device_splitter",
        "--hidden-import=src.utils.device_joystick_mapper",
        "--hidden-import=src.utils.label_overrides",
        "--hidden-import=src.utils.input_detector",
        "--hidden-import=src.utils.input_validator",
        "--hidden-import=src.utils.single_instance",
        "--hidden-import=src.gui",
        "--hidden-import=src.gui.main_window",
        "--hidden-import=src.gui.qtpdf_device_widget",
        "--hidden-import=src.gui.config_tab",
        "--hidden-import=src.gui.control_editor",
        "--hidden-import=src.gui.preview_widget",
        "--hidden-import=src.gui.remap_dialog",
        "--hidden-import=src.exporters",
        "--hidden-import=src.exporters.csv_exporter",
        "--hidden-import=src.exporters.pdf_exporter",
        "--hidden-import=src.exporters.word_exporter",
        "--hidden-import=src.exporters.graphic_exporter",
        "--hidden-import=src.graphics",
        "--hidden-import=src.graphics.pdf_template_manager",
        "--hidden-import=src.graphics.template_manager",

        # Entry point
        "src/main.py"
    ]

    # Add preset-profiles if it exists
    preset_profiles = PROJECT_ROOT / "preset-profiles"
    if preset_profiles.exists():
        cmd.insert(-1, f"--add-data=preset-profiles{sep}preset-profiles")

    print("Running PyInstaller...\n")
    print(" ".join(cmd))
    print()

    # Run PyInstaller
    result = subprocess.run(cmd, cwd=PROJECT_ROOT)

    if result.returncode == 0:
        print("\n" + "="*60)
        print("Build completed successfully!")
        print("="*60)
        print(f"\nExecutable location: {PROJECT_ROOT / 'dist' / 'SCProfileEditor.exe'}")
        print(f"Version: {version}")
    else:
        print("\n" + "="*60)
        print("Build FAILED!")
        print("="*60)
        sys.exit(1)

def main():
    """Main entry point"""
    try:
        build_executable()
    except KeyboardInterrupt:
        print("\n\nBuild cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nBuild error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
