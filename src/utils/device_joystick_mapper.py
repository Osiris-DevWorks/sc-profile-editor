"""
Device to Joystick Index Mapper

Maps device names from Star Citizen XML profiles to joystick indices (js1, js2, js3, etc.)
Handles device name variations, partial matching, and split devices.

Author: Phase 1.2 - Device-to-Joystick Mapping System
"""

from typing import Dict, List, Optional, Tuple
import json
from pathlib import Path
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.profile_model import ControlProfile, Device


class DeviceJoystickMapper:
    """
    Maps devices from SC profiles to joystick indices (js1, js2, etc.)

    The mapper creates a bidirectional mapping between:
    - Device names (e.g., "VKBSim Gunfighter MCG Ultimate")
    - Joystick indices (e.g., "js1", "js2")

    This is essential for PDF templates because form field names use
    the jsN_button format (e.g., "js1_button1", "js2_button5").
    """

    def __init__(self, profile: ControlProfile, template_registry_path: Optional[str] = None):
        """
        Initialize mapper with a control profile

        Args:
            profile: Parsed Star Citizen profile with device information
            template_registry_path: Optional path to template registry for device matching
        """
        self.profile = profile
        self.template_registry = None
        if template_registry_path:
            self.load_template_registry(template_registry_path)

        # Create mappings
        self.device_to_js: Dict[str, str] = {}  # device name -> js index
        self.js_to_device: Dict[str, Device] = {}  # js index -> Device object
        # Authoritative VID/PID -> js index map. Populated from devices that
        # had a parseable DirectInput product GUID in their profile XML.
        # Checked before name-based matching because it's an exact identity
        # comparison rather than fuzzy substring matching.
        self.vid_pid_to_js: Dict[Tuple[int, int], str] = {}
        self._build_mappings()

    def load_template_registry(self, registry_path: str):
        """Load template registry for device pattern matching"""
        try:
            with open(registry_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.template_registry = data.get('templates', [])
        except (FileNotFoundError, json.JSONDecodeError) as e:
            print(f"Warning: Could not load template registry: {e}")
            self.template_registry = None

    def _build_mappings(self):
        """Build bidirectional mappings between devices and joystick indices"""
        # Filter to only joystick devices
        joysticks = [d for d in self.profile.devices if d.device_type == 'joystick']

        # Sort by instance number to ensure consistent mapping
        joysticks.sort(key=lambda d: d.instance)

        for device in joysticks:
            # Map device to its JS instance
            js_index = f"js{device.instance}"

            if device.product_name:
                # Use product name as key (clean version)
                device_name = device.product_name.strip()
                self.device_to_js[device_name] = js_index
                self.js_to_device[js_index] = device

                # Also add lowercase version for case-insensitive matching
                self.device_to_js[device_name.lower()] = js_index

            # Index by VID/PID if the profile carried a DI product GUID. This
            # is the authoritative match key — every physical device of a
            # given model shares the same VID/PID, regardless of name spelling.
            if device.vid_pid is not None:
                self.vid_pid_to_js[device.vid_pid] = js_index
                # Always populate js_to_device even when product_name is empty
                # so vid/pid-only matches still resolve to a Device object.
                if js_index not in self.js_to_device:
                    self.js_to_device[js_index] = device

    def get_js_index_for_vid_pid(self, vid_pid: Tuple[int, int]) -> Optional[str]:
        """
        Look up the joystick index by (VID, PID).

        This is the authoritative match path — VID/PID is a hardware identity
        that survives renames, locale changes, and SDL/DirectInput naming
        differences. Returns None if no profile device carried a parseable
        DI product GUID, in which case the caller should fall back to name
        matching via get_js_index_for_device().
        """
        if vid_pid is None:
            return None
        return self.vid_pid_to_js.get(vid_pid)

    def get_js_index_for_device(self, device_name: str,
                                 vid_pid: Optional[Tuple[int, int]] = None) -> Optional[str]:
        """
        Get joystick index (e.g., "js1") for a device.

        Args:
            device_name: Device name (e.g., "VKBSim Gunfighter MCG Ultimate")
            vid_pid: Optional (VID, PID) tuple. When provided, matched first
                via the authoritative DirectInput product GUID; falls back to
                name-based matching if VID/PID isn't in the profile or doesn't
                resolve.

        Returns:
            Joystick index (e.g., "js1") or None if not found
        """
        # VID/PID first — exact, identity-based match.
        if vid_pid is not None:
            js_index = self.vid_pid_to_js.get(vid_pid)
            if js_index:
                return js_index

        # Try exact match first
        if device_name in self.device_to_js:
            return self.device_to_js[device_name]

        # Try case-insensitive match
        device_name_lower = device_name.lower()
        if device_name_lower in self.device_to_js:
            return self.device_to_js[device_name_lower]

        # Try partial match using template registry patterns
        if self.template_registry:
            js_index = self._match_using_templates(device_name)
            if js_index:
                return js_index

        # Try fuzzy match (last resort)
        return self._fuzzy_match_device(device_name)

    def get_device_for_js_index(self, js_index: str) -> Optional[Device]:
        """
        Get device object for a joystick index

        Args:
            js_index: Joystick index (e.g., "js1", "js2")

        Returns:
            Device object or None if not found
        """
        return self.js_to_device.get(js_index)

    def _match_using_templates(self, device_name: str) -> Optional[str]:
        """
        Match device name using template registry patterns

        Args:
            device_name: Device name to match

        Returns:
            Joystick index or None
        """
        if not self.template_registry:
            return None

        device_name_lower = device_name.lower()

        for template in self.template_registry:
            patterns = template.get('device_match_patterns', [])
            for pattern in patterns:
                if pattern.lower() in device_name_lower:
                    # Found a match! Now find which JS index has this device
                    for js_idx, device in self.js_to_device.items():
                        if device.product_name and pattern.lower() in device.product_name.lower():
                            return js_idx

        return None

    def _fuzzy_match_device(self, device_name: str) -> Optional[str]:
        """
        Fuzzy match device name (case-insensitive substring matching)

        Args:
            device_name: Device name to match

        Returns:
            Joystick index or None
        """
        device_name_lower = device_name.lower()

        # Check if device_name is substring of any known device
        for known_device, js_index in self.device_to_js.items():
            if device_name_lower in known_device.lower() or known_device.lower() in device_name_lower:
                return js_index

        return None

    def get_all_mappings(self) -> Dict[str, str]:
        """
        Get all device-to-JS mappings

        Returns:
            Dictionary mapping device names to JS indices
        """
        # Return only non-lowercase keys (clean version)
        return {k: v for k, v in self.device_to_js.items() if not k.islower() or k not in self.device_to_js.values()}

    def get_joystick_devices(self) -> List[Device]:
        """
        Get all joystick devices in the profile

        Returns:
            List of Device objects (joysticks only)
        """
        return list(self.js_to_device.values())

    def print_mappings(self):
        """Print all mappings (for debugging)"""
        print("Device-to-Joystick Mappings:")
        print("=" * 60)
        for js_index in sorted(self.js_to_device.keys()):
            device = self.js_to_device[js_index]
            print(f"{js_index} -> {device.product_name}")
        print("=" * 60)


def create_mapper_from_xml(xml_path: str, template_registry_path: Optional[str] = None) -> DeviceJoystickMapper:
    """
    Convenience function to create mapper from XML file

    Args:
        xml_path: Path to Star Citizen profile XML
        template_registry_path: Optional path to template registry

    Returns:
        DeviceJoystickMapper instance
    """
    from parser.xml_parser import ProfileParser

    parser = ProfileParser(xml_path)
    profile = parser.parse()
    return DeviceJoystickMapper(profile, template_registry_path)


# Example usage and testing
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python device_joystick_mapper.py <profile.xml> [template_registry.json]")
        sys.exit(1)

    xml_path = sys.argv[1]
    registry_path = sys.argv[2] if len(sys.argv) > 2 else None

    print(f"Loading profile: {xml_path}")
    if registry_path:
        print(f"Using template registry: {registry_path}")

    try:
        mapper = create_mapper_from_xml(xml_path, registry_path)
        mapper.print_mappings()

        # Test some lookups
        print("\nTest Lookups:")
        print("-" * 60)
        devices = mapper.get_joystick_devices()
        if devices:
            test_device = devices[0]
            print(f"Device: {test_device.product_name}")
            js_idx = mapper.get_js_index_for_device(test_device.product_name)
            print(f"JS Index: {js_idx}")

            print(f"\nReverse lookup ({js_idx}):")
            device_obj = mapper.get_device_for_js_index(js_idx)
            print(f"Device: {device_obj.product_name if device_obj else 'None'}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
