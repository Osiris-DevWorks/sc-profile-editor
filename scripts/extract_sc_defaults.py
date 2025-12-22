#!/usr/bin/env python3
"""
Extract default control bindings and preset profiles from Star Citizen's Data.p4k

This script extracts:
- Default actionmaps.xml from Data/Libs/Config/Profiles/default/
- Preset profiles from Data/Libs/Config/Mappings/

Run this script when Star Citizen updates to refresh default bindings and presets.

Usage:
    python scripts/extract_sc_defaults.py
"""

import os
import sys
import struct
import shutil
from pathlib import Path
from typing import List, Dict, Tuple


def find_p4k_file() -> str:
    """Find Star Citizen Data.p4k file"""
    default_paths = [
        r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\Data.p4k",
        r"C:\Program Files (x86)\Roberts Space Industries\StarCitizen\LIVE\Data.p4k",
    ]

    for path in default_paths:
        if os.path.exists(path):
            return path

    raise FileNotFoundError(
        "Could not find Star Citizen Data.p4k file. "
        "Please install Star Citizen or provide the path as an argument."
    )


def extract_file_from_p4k(
    p4k_path: str, file_path_in_archive: str, output_path: str
) -> bool:
    """
    Extract a single file from P4K archive using a ZIP-compatible library.

    Args:
        p4k_path: Path to Data.p4k file
        file_path_in_archive: Path within archive (e.g., "Data/Libs/Config/Profiles/default/actionmaps.xml")
        output_path: Where to save the extracted file

    Returns:
        True if successful, False otherwise
    """
    try:
        # Try py7zr which handles ZIP64 better
        try:
            import py7zr

            with py7zr.SevenZipFile(p4k_path, 'r') as archive:
                # Normalize path separators
                archive_path = file_path_in_archive.replace("\\", "/")

                # Extract to temporary location and read
                import tempfile
                with tempfile.TemporaryDirectory() as tmpdir:
                    archive.extract(path=tmpdir)

                    # Find the extracted file (case-insensitive)
                    for root, dirs, files in os.walk(tmpdir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            rel_path = os.path.relpath(file_path, tmpdir).replace("\\", "/")

                            if rel_path.lower() == archive_path.lower():
                                # Create output directory if needed
                                os.makedirs(os.path.dirname(output_path), exist_ok=True)

                                # Copy extracted file
                                shutil.copy2(file_path, output_path)
                                return True
        except ImportError:
            pass
        except Exception as e:
            pass

        # Fallback: try zipfile with error handling
        import zipfile

        try:
            with zipfile.ZipFile(p4k_path, "r", allowZip64=True) as zf:
                # Normalize path separators
                archive_path = file_path_in_archive.replace("\\", "/")

                # Find matching file in archive (case-insensitive)
                matching_file = None
                for name in zf.namelist():
                    if name.lower() == archive_path.lower():
                        matching_file = name
                        break

                if matching_file:
                    # Extract file
                    content = zf.read(matching_file)

                    # Create output directory if needed
                    os.makedirs(os.path.dirname(output_path), exist_ok=True)

                    # Write file
                    with open(output_path, "wb") as f:
                        f.write(content)

                    return True
        except zipfile.BadZipFile:
            # P4K uses custom ZIP format that standard zipfile can't read
            pass

    except Exception as e:
        print(f"Error extracting {file_path_in_archive}: {e}")

    return False


def list_files_in_p4k(p4k_path: str, prefix: str) -> List[str]:
    """
    List all files in P4K archive matching a prefix.

    Args:
        p4k_path: Path to Data.p4k file
        prefix: File prefix to match (e.g., "Data/Libs/Config/Mappings/")

    Returns:
        List of matching file paths
    """
    try:
        import zipfile

        matching_files = []

        with zipfile.ZipFile(p4k_path, "r") as zf:
            for name in zf.namelist():
                if name.lower().startswith(prefix.lower()) and name.endswith(".xml"):
                    matching_files.append(name)

        return sorted(matching_files)

    except Exception as e:
        print(f"Error listing files in P4K: {e}")
        return []


def extract_defaults_and_presets(p4k_path: str, output_dir: str) -> bool:
    """
    Extract default bindings and preset profiles from Data.p4k.

    Args:
        p4k_path: Path to Data.p4k file
        output_dir: Output directory for extracted files

    Returns:
        True if successful
    """
    print(f"Extracting from: {p4k_path}")
    print(f"Output directory: {output_dir}")
    print()

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    success = True

    # 1. Extract actionmaps.xml (default bindings)
    print("Extracting default actionmaps.xml...")
    actionmaps_src = "Data/Libs/Config/Profiles/default/actionmaps.xml"
    actionmaps_dst = os.path.join(output_dir, "actionmaps.xml")

    if extract_file_from_p4k(p4k_path, actionmaps_src, actionmaps_dst):
        print(f"  [OK] Saved to: {actionmaps_dst}")
    else:
        print(f"  [FAIL] Failed to extract: {actionmaps_src}")
        success = False

    # 2. Extract defaultProfile.xml
    print("Extracting defaultProfile.xml...")
    default_profile_src = "Data/Libs/Config/defaultProfile.xml"
    default_profile_dst = os.path.join(output_dir, "defaultProfile.xml")

    if extract_file_from_p4k(p4k_path, default_profile_src, default_profile_dst):
        print(f"  [OK] Saved to: {default_profile_dst}")
    else:
        print(f"  [FAIL] Failed to extract: {default_profile_src}")
        # This is optional, so don't fail completely

    # 3. Extract preset profiles from Mappings folder
    print("\nExtracting preset profiles...")
    presets_output_dir = os.path.join(output_dir, "presets")
    os.makedirs(presets_output_dir, exist_ok=True)

    # List files in Mappings folder
    mappings_prefix = "Data/Libs/Config/Mappings/"
    preset_files = list_files_in_p4k(p4k_path, mappings_prefix)

    if preset_files:
        print(f"  Found {len(preset_files)} preset profiles")

        for preset_file in preset_files:
            filename = os.path.basename(preset_file)
            output_path = os.path.join(presets_output_dir, filename)

            if extract_file_from_p4k(p4k_path, preset_file, output_path):
                print(f"  [OK] {filename}")
            else:
                print(f"  [FAIL] Failed: {filename}")
                success = False
    else:
        print("  [FAIL] No preset profiles found in Data.p4k")
        success = False

    print()
    if success:
        print("[OK] Extraction complete!")
        return True
    else:
        print("[FAIL] Extraction completed with errors")
        return success


def main():
    """Main entry point"""
    try:
        # Find P4K file
        p4k_path = find_p4k_file()
        print(f"Found Data.p4k: {p4k_path}\n")

        # Determine output directory (next to this script)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_dir = os.path.join(project_root, "default-bindings")

        # Extract files
        success = extract_defaults_and_presets(p4k_path, output_dir)

        sys.exit(0 if success else 1)

    except FileNotFoundError as e:
        print(f"Error: {e}")
        print()
        print("Please ensure Star Citizen is installed at:")
        print("  C:\\Program Files\\Roberts Space Industries\\StarCitizen\\LIVE\\")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
