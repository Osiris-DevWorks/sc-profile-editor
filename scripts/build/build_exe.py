"""
Build script for creating the SC Profile Editor executable

Usage:
    python scripts/build/build_exe.py          # build dist/SCProfileEditor/ (onedir)

Mirrors smart-citizen's scripts/build/build_exe.py: one PyInstaller --onedir
build with a STABLE exe name (SCProfileEditor.exe) so installed shortcuts
survive version updates. The version lives in VERSION.TXT only; the exe reads
it at runtime via src/utils/version.py and installer.iss reads it at compile
time via ISPP.
"""

import os
import shutil
import sys

import PyInstaller.__main__

# scripts/build/ -> repo root
project_dir = os.path.dirname(os.path.abspath(__file__))
root_dir = os.path.dirname(os.path.dirname(project_dir))

version_file = os.path.join(root_dir, 'VERSION.TXT')
with open(version_file, 'r', encoding='utf-8') as f:
    current_version = f.read().strip()

print(f"\n{'=' * 60}")
print(f"Building SC Profile Editor version: {current_version}")
print(f"{'=' * 60}\n")

# Clean previous builds
print("Cleaning old builds...")
for folder in ['build', 'dist']:
    path = os.path.join(root_dir, folder)
    if os.path.exists(path):
        shutil.rmtree(path)
        print(f"  - Removed {folder}/")
print()

exe_name = "SCProfileEditor"

# PyInstaller's generated .spec goes into build/ (wiped each run) so it never
# litters the repo root.
spec_path = os.path.join(root_dir, 'build')
os.makedirs(spec_path, exist_ok=True)


def data(src_rel: str, dest: str) -> str:
    return f"{os.path.join(root_dir, src_rel)}{os.pathsep}{dest}"


args = [
    os.path.join(root_dir, 'src', 'main.py'),
    '--name', exe_name,
    '--onedir',
    '--windowed',
    '--icon', os.path.join(root_dir, 'assets', 'icon.ico'),
    # main_window.py uses bare imports (`from parser.xml_parser import …`).
    # PyInstaller's frozen import table is pre-baked, so `src/` must be a
    # source root at analysis time or the exe dies on launch with
    # ModuleNotFoundError: No module named 'parser' (see docs/DEVELOPMENT.md).
    '--paths', os.path.join(root_dir, 'src'),
    # Every bundled resource below is resolved at runtime through the
    # _MEIPASS-aware get_resource_path() helper. Keep this list in sync
    # with docs/DEVELOPMENT.md.
    '--add-data', data('VERSION.TXT', '.'),
    '--add-data', data('label_overrides.json', '.'),
    '--add-data', data('README.md', '.'),
    '--add-data', data('ABOUT.md', '.'),
    '--add-data', data('UNBIND_ALL.xml', '.'),
    '--add-data', data('assets', 'assets'),
    '--add-data', data('visual-templates', 'visual-templates'),
    '--add-data', data('example-profiles', 'example-profiles'),
    '--add-data', data('default-bindings', 'default-bindings'),
    '--workpath', os.path.join(root_dir, 'build'),
    '--specpath', spec_path,
    '--distpath', os.path.join(root_dir, 'dist'),
    '--hidden-import=PyQt6',
    '--hidden-import=PyQt6.QtPdf',
    '--hidden-import=PyQt6.QtPdfWidgets',
    '--noconfirm',
]

print("Building --onedir version (for installer)...")
print(f"  Output: dist/{exe_name}/")
print()

try:
    PyInstaller.__main__.run(args)
except Exception as e:  # noqa: BLE001 - surface any PyInstaller failure
    print(f"\nError building --onedir executable: {e}")
    sys.exit(1)

exe_path = os.path.join(root_dir, 'dist', exe_name, f'{exe_name}.exe')
if not os.path.exists(exe_path):
    print(f"\nBuild finished but {exe_path} is missing")
    sys.exit(1)

print(f"\n{'=' * 60}")
print("Build successful!")
print(f"{'=' * 60}")
print(f"Onedir: dist/{exe_name}/")
print(f"Exe:    dist/{exe_name}/{exe_name}.exe")
print()
