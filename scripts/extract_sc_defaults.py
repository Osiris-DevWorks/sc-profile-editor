#!/usr/bin/env python3
"""
Extract preset profiles from Star Citizen's Data.p4k

This script extracts official preset profiles from:
  Data/Libs/Config/Mappings/

REQUIREMENTS:
1. Download unp4k.exe from: https://github.com/dolkensp/unp4k/releases
   Place it in the scripts/ folder or project root, or add to PATH

2. Download StarBreaker.Cli from: https://nightly.link/diogotr7/StarBreaker/workflows/build/master
   Extract to scripts/StarBreaker.Cli/ directory

unp4k handles P4K extraction, StarBreaker.Cli converts CryXML to plain XML.

Usage:
    python scripts/extract_sc_defaults.py
"""

import os
import sys
import glob
import logging
import subprocess
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(message)s'
)
logger = logging.getLogger(__name__)


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
        "Please ensure Star Citizen is installed at:\n"
        "  C:\\Program Files\\Roberts Space Industries\\StarCitizen\\LIVE\\"
    )


def find_unp4k() -> str:
    """Find unp4k.exe executable"""
    search_paths = [
        # Current directory
        "unp4k.exe",
        # scripts directory
        os.path.join(os.path.dirname(__file__), "unp4k.exe"),
        # unp4k subdirectory in scripts (e.g., unp4k-v3.13.66)
        os.path.join(os.path.dirname(__file__), "unp4k*", "unp4k.exe"),
        # Project root
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "unp4k.exe"),
    ]

    # Check direct paths first
    for path in search_paths:
        if "*" not in path:
            if shutil.which(path) or os.path.exists(path):
                return path

    # Check glob paths (unp4k-* subdirectories)
    scripts_dir = os.path.dirname(__file__)
    glob_pattern = os.path.join(scripts_dir, "unp4k*", "unp4k.exe")
    glob_results = glob.glob(glob_pattern)
    if glob_results:
        return glob_results[0]

    # Try PATH
    unp4k_path = shutil.which("unp4k.exe")
    if unp4k_path:
        return unp4k_path

    raise FileNotFoundError(
        "Could not find unp4k.exe. "
        "Please download it from: https://github.com/dolkensp/unp4k/releases "
        "and place it in:\n"
        "  - scripts/ folder\n"
        "  - scripts/unp4k-vX.X.X/ folder\n"
        "  - project root\n"
        "  - or add to PATH"
    )


def find_starbreaker_cli() -> str:
    """Find StarBreaker.Cli.exe executable"""
    search_paths = [
        # StarBreaker.Cli subdirectory in scripts
        os.path.join(os.path.dirname(__file__), "StarBreaker.Cli", "StarBreaker.Cli.exe"),
        # Current directory
        "StarBreaker.Cli.exe",
        # scripts directory
        os.path.join(os.path.dirname(__file__), "StarBreaker.Cli.exe"),
    ]

    for path in search_paths:
        if os.path.exists(path):
            return path

    # Try PATH
    sb_path = shutil.which("StarBreaker.Cli.exe")
    if sb_path:
        return sb_path

    raise FileNotFoundError(
        "Could not find StarBreaker.Cli.exe. "
        "Please download it from: https://nightly.link/diogotr7/StarBreaker/workflows/build/master/StarBreaker.Cli.zip "
        "and extract to:\n"
        "  - scripts/StarBreaker.Cli/ folder"
    )


def inspect_file_format(file_path: str) -> str:
    """
    Inspect file format by examining magic bytes and first bytes.

    Args:
        file_path: Path to file to inspect

    Returns:
        String description of detected format
    """
    try:
        with open(file_path, 'rb') as f:
            header = f.read(16)

        if not header:
            return "Empty file"

        # Check for common formats
        hex_header = header.hex().upper()
        ascii_preview = ''.join(chr(b) if 32 <= b < 127 else f'\\x{b:02x}' for b in header)

        # CryXML typically starts with a header indicating compression/encryption
        if header.startswith(b'\x00\x00\x00\x00'):
            return f"Binary format (starts with nulls) - {hex_header[:32]}... (ASCII: {ascii_preview})"
        elif header.startswith(b'<?xml'):
            return "Plain XML (valid start)"
        elif header[:2] == b'PK':
            return "ZIP/P4K format"
        elif header[:2] == b'\x78\x9c' or header[:2] == b'\x78\xda':
            return "DEFLATE compressed (zlib)"
        else:
            return f"Unknown - hex: {hex_header[:32]}... (ASCII: {ascii_preview})"

    except Exception as e:
        return f"Inspection error: {e}"


def convert_cryxml_files(starbreaker_exe: str, input_dir: str, output_dir: str) -> bool:
    """
    Convert CryXML files to plain XML using StarBreaker.Cli.

    Args:
        starbreaker_exe: Path to StarBreaker.Cli.exe executable
        input_dir: Directory containing CryXML files
        output_dir: Output directory for converted XML files

    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info("Running StarBreaker.Cli to convert CryXML to plain XML...")
        cmd = [starbreaker_exe, "cryxml-convert-all", "--input", input_dir, "--output", output_dir]

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            logger.error("StarBreaker CryXML conversion failed")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False

        logger.info(f"CryXML conversion completed: {result.stdout.strip()}")
        return True

    except subprocess.TimeoutExpired:
        logger.error("StarBreaker CryXML conversion timed out")
        return False
    except Exception as e:
        logger.error(f"Error during CryXML conversion: {e}")
        return False


def extract_presets_with_unp4k(p4k_path: str, unp4k_exe: str, starbreaker_exe: str, output_dir: str) -> bool:
    """
    Extract preset profiles from Data.p4k using unp4k and convert CryXML to XML.

    Args:
        p4k_path: Path to Data.p4k file
        unp4k_exe: Path to unp4k.exe executable
        starbreaker_exe: Path to StarBreaker.Cli.exe executable
        output_dir: Output directory for extracted files

    Returns:
        True if successful, False otherwise
    """
    try:
        # Create temporary extraction directory
        temp_dir = os.path.join(output_dir, "_temp_extract")
        os.makedirs(temp_dir, exist_ok=True)

        logger.info(f"Using unp4k: {unp4k_exe}")
        logger.info(f"Using StarBreaker.Cli: {starbreaker_exe}")
        logger.info(f"Extracting from: {p4k_path}")
        logger.info(f"Temporary extraction directory: {temp_dir}")

        # Run unp4k to extract Mappings folder
        logger.info("Running unp4k to extract Mappings folder...")
        cmd = [unp4k_exe, p4k_path, "Data/Libs/Config/Mappings"]

        result = subprocess.run(
            cmd,
            cwd=temp_dir,
            capture_output=True,
            text=True,
            timeout=120
        )

        if result.returncode != 0:
            logger.error("unp4k extraction failed")
            logger.error(f"STDOUT: {result.stdout}")
            logger.error(f"STDERR: {result.stderr}")
            return False

        logger.info("unp4k extraction completed")

        # Convert CryXML files to plain XML
        temp_converted_dir = os.path.join(output_dir, "_temp_converted")
        os.makedirs(temp_converted_dir, exist_ok=True)

        if not convert_cryxml_files(starbreaker_exe, temp_dir, temp_converted_dir):
            logger.error("Failed to convert CryXML files")
            return False

        # Find the extracted XML files (they're in Data/Libs/Config/Mappings subdirectory)
        mappings_dir = os.path.join(temp_converted_dir, "Data", "Libs", "Config", "Mappings")
        if not os.path.exists(mappings_dir):
            logger.error(f"Converted files not found in expected location: {mappings_dir}")
            return False

        # Use converted files instead of the original extracted ones
        temp_dir_with_converted = mappings_dir

        # Find extracted preset files
        presets_output_dir = os.path.join(output_dir, "presets")
        os.makedirs(presets_output_dir, exist_ok=True)

        # Get the converted XML files
        preset_files = []
        for file in os.listdir(temp_dir_with_converted):
            if file.endswith('.xml'):
                preset_files.append(os.path.join(temp_dir_with_converted, file))

        if not preset_files:
            logger.error("No converted preset files found")
            return False

        logger.info(f"Found {len(preset_files)} converted preset profiles\n")

        success = True

        # Copy and validate each preset
        for preset_path in preset_files:
            try:
                filename = os.path.basename(preset_path)
                output_path = os.path.join(presets_output_dir, filename)

                logger.info(f"Processing: {filename}")

                # Read and validate XML
                with open(preset_path, 'rb') as f:
                    file_content = f.read()

                # Parse to verify it's valid XML and get info
                try:
                    tree = ET.fromstring(file_content)
                    action_profiles = tree.find('ActionProfiles')
                    profile_name = action_profiles.get('profileName') if action_profiles is not None else 'Unknown'
                    rebinds = tree.findall('.//rebind')

                    # Copy to output directory
                    with open(output_path, 'wb') as f:
                        f.write(file_content)

                    logger.info(f"  [OK] {filename}")
                    logger.info(f"       Profile: {profile_name}")
                    logger.info(f"       Bindings: {len(rebinds)}")

                except ET.ParseError as e:
                    logger.error(f"  [FAIL] Invalid XML: {e}")
                    success = False

            except Exception as e:
                logger.error(f"  [FAIL] {filename}: {e}")
                success = False

        logger.info("")

        # Clean up temporary directories
        logger.info(f"Cleaning up temporary directories...")
        shutil.rmtree(temp_dir, ignore_errors=True)
        shutil.rmtree(temp_converted_dir, ignore_errors=True)

        if success:
            logger.info("[OK] Extraction and conversion complete!")
            logger.info(f"Presets saved to: {presets_output_dir}")
            return True
        else:
            logger.error("[PARTIAL] Extraction completed with errors")
            return success

    except subprocess.TimeoutExpired:
        logger.error("unp4k extraction timed out")
        return False
    except Exception as e:
        logger.error(f"Error during extraction: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point"""
    try:
        logger.info("")

        # Find P4K file
        p4k_path = find_p4k_file()
        logger.info(f"Found Data.p4k: {p4k_path}")

        # Find unp4k executable
        unp4k_exe = find_unp4k()

        # Find StarBreaker.Cli executable
        starbreaker_exe = find_starbreaker_cli()

        # Determine output directory
        script_dir = os.path.dirname(os.path.abspath(__file__))
        project_root = os.path.dirname(script_dir)
        output_dir = os.path.join(project_root, "default-bindings")

        # Extract presets
        success = extract_presets_with_unp4k(p4k_path, unp4k_exe, starbreaker_exe, output_dir)

        sys.exit(0 if success else 1)

    except FileNotFoundError as e:
        logger.error(f"Error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
