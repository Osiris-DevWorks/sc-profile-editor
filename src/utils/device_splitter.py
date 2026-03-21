"""
Device splitter utility for handling composite devices like VKB Gladiator + SEM
"""

import re
import json
import os
import sys
import logging
from typing import Optional, Tuple, Dict

logger = logging.getLogger(__name__)

# Cache for template registry
_template_registry_cache: Optional[Dict] = None
_templates_dir_cache: Optional[str] = None


def _get_templates_dir() -> Optional[str]:
    """Get the visual-templates directory path"""
    global _templates_dir_cache

    if _templates_dir_cache:
        return _templates_dir_cache

    try:
        # Try to determine if running as PyInstaller bundle
        if getattr(sys, 'frozen', False):
            base_path = sys._MEIPASS
        else:
            # Running from source - go up to project root
            current_file = os.path.abspath(__file__)
            src_dir = os.path.dirname(os.path.dirname(current_file))
            base_path = os.path.dirname(src_dir)

        templates_dir = os.path.join(base_path, 'visual-templates')
        if os.path.exists(templates_dir):
            _templates_dir_cache = templates_dir
            return templates_dir
    except Exception as e:
        logger.debug(f"Could not locate templates directory: {e}")

    return None


def _load_template_registry() -> Optional[Dict]:
    """Load and cache the template registry"""
    global _template_registry_cache

    if _template_registry_cache is not None:
        return _template_registry_cache

    templates_dir = _get_templates_dir()
    if not templates_dir:
        return None

    registry_path = os.path.join(templates_dir, 'template_registry.json')

    if not os.path.exists(registry_path):
        logger.debug(f"Template registry not found at {registry_path}")
        return None

    try:
        with open(registry_path, 'r', encoding='utf-8') as f:
            _template_registry_cache = json.load(f)
            logger.debug(f"Loaded template registry with {len(_template_registry_cache.get('templates', []))} templates")
            return _template_registry_cache
    except Exception as e:
        logger.warning(f"Error loading template registry: {e}")
        return None


def get_friendly_device_name(device_name: str) -> str:
    """
    Get friendly display name for a device based on template registry

    Args:
        device_name: Raw device name from SC profile (e.g., "F16 MFD 2")

    Returns:
        Friendly name from template registry or original name if no match
    """
    if not device_name:
        return device_name

    registry = _load_template_registry()
    if not registry:
        return device_name

    device_name_lower = device_name.lower()

    # Try to match against template patterns
    for template in registry.get('templates', []):
        # Skip deprecated templates
        if template.get('deprecated', False):
            continue

        # Check device match patterns
        for pattern in template.get('device_match_patterns', []):
            if pattern.lower() in device_name_lower:
                # Found a match - return the template's friendly name
                friendly_name = template.get('name', device_name)

                # Remove instance numbers from the device name (e.g., "F16 MFD 2" -> "F16 MFD")
                # and check if we need to preserve the instance
                instance_match = re.search(r'\s+(\d+)\s*$', device_name)
                if instance_match:
                    # Device has instance number - append it to friendly name
                    instance = instance_match.group(1)
                    return f"{friendly_name} {instance}"
                else:
                    return friendly_name

    # No match found - return original
    return device_name


def is_vkb_with_sem(device_name: str) -> bool:
    """
    Check if device is a VKB device with SEM module attached

    Args:
        device_name: Device product name (e.g., "VKBsim Gladiator EVO R SEM")

    Returns:
        True if device has SEM module attached
    """
    if not device_name:
        return False

    device_name_upper = device_name.upper()
    return 'VKB' in device_name_upper and 'SEM' in device_name_upper


def get_base_stick_name(device_name: str) -> str:
    """
    Extract base stick name from a VKB device with SEM

    Args:
        device_name: Full device name (e.g., "VKBsim Gladiator EVO R SEM")

    Returns:
        Base stick name without SEM (e.g., "VKBsim Gladiator EVO R")
    """
    if not device_name:
        return device_name

    # Remove "SEM" and extra whitespace
    base_name = re.sub(r'\s*SEM\s*', '', device_name, flags=re.IGNORECASE)
    return base_name.strip()


def _get_sem_button_range(device_name: str) -> tuple:
    """
    Determine the button range for SEM module based on device type

    For Gladiator-based devices (EVO, SCG, etc.): SEM uses buttons 41-78
    For NXT-based or standalone SEM: SEM uses buttons 9-40

    Args:
        device_name: Full device name from SC profile

    Returns:
        Tuple of (start_button, end_button) for SEM range
    """
    device_upper = device_name.upper() if device_name else ""

    # If device contains "Gladiator" (EVO, SCG, MCGU, etc.), use 41-78 range
    if 'GLADIATOR' in device_upper or 'GUNFIGHTER' in device_upper:
        return (41, 78)

    # For NXT or standalone SEM, use 9-40 range
    return (9, 40)


def split_device_by_button(device_name: str, button_number: int) -> str:
    """
    Split a composite device into its component parts based on button number

    For VKB devices with SEM:
    - Always maps to "VKB SEM" for display/filtering
    - The actual button range varies by device type

    Args:
        device_name: Full device name from SC profile
        button_number: Button number from input code

    Returns:
        Appropriate device name for the button
    """
    if not is_vkb_with_sem(device_name):
        return device_name

    # For composite VKB+SEM devices, always show as "VKB SEM" in device filter/display
    # This prevents base stick names like "VKBsim NXT" from appearing in the filter
    # All buttons (base and SEM) are grouped under the VKB SEM device for filtering
    return "VKB SEM"


def extract_button_number(input_code: str) -> Optional[int]:
    """
    Extract button number from joystick input code

    Args:
        input_code: Input code like "js1_button42"

    Returns:
        Button number or None if not a button input
    """
    match = re.match(r'js\d+_button(\d+)', input_code)
    if match:
        return int(match.group(1))
    return None


def get_device_for_input(device_name: str, input_code: str) -> str:
    """
    Get the appropriate device name for a given input code

    Args:
        device_name: Full device name from SC profile
        input_code: Input code (e.g., "js1_button42")

    Returns:
        Appropriate device name (may be split into component, with friendly name applied)
    """
    # First, handle composite devices (e.g., VKB with SEM)
    button_num = extract_button_number(input_code)

    if button_num is not None:
        split_name = split_device_by_button(device_name, button_num)
    elif is_vkb_with_sem(device_name):
        # For non-button inputs (axes, hats, etc.), use base device
        split_name = get_base_stick_name(device_name)
    else:
        split_name = device_name

    # Apply friendly name from template registry
    return get_friendly_device_name(split_name)
