"""
XML parser for Star Citizen control profiles
"""

import xml.etree.ElementTree as ET
from typing import Dict, List, Optional
import sys
import os
import logging

# Add parent directory to path to import models
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.profile_model import ControlProfile, Device, ActionMap, ActionBinding

logger = logging.getLogger(__name__)


class ProfileParser:
    """Parser for Star Citizen XML profile files"""

    def __init__(self, xml_path: str, use_bundled_defaults: bool = True):
        self.xml_path = xml_path
        self.use_bundled_defaults = use_bundled_defaults
        self.tree = None
        self.root = None

        # Path to bundled default bindings
        if use_bundled_defaults:
            # Get bundled defaults from app resources
            if getattr(sys, 'frozen', False):
                # Running as PyInstaller executable
                base_path = sys._MEIPASS
            else:
                # Running as script
                base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                base_path = os.path.dirname(base_path)  # Go up to project root
            self.default_actionmaps_path = os.path.join(base_path, 'default-bindings', 'actionmaps.xml')
        else:
            self.default_actionmaps_path = None

    def parse(self) -> ControlProfile:
        """Parse the XML file and return ControlProfile object"""
        try:
            self.tree = ET.parse(self.xml_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"XML file not found: {self.xml_path}")

        profile_name = self.get_profile_name()
        devices = self.get_devices()
        categories = self.get_categories()
        action_maps = self.get_action_maps()

        profile = ControlProfile(
            profile_name=profile_name,
            devices=devices,
            action_maps=action_maps,
            categories=categories,
            is_modified=False,
            source_xml_path=self.xml_path,
            merged_defaults=False
        )

        # Merge default bindings if configured and file exists
        if self.default_actionmaps_path and os.path.exists(self.default_actionmaps_path):
            self._merge_default_bindings(profile)
            profile.merged_defaults = True

        return profile

    def get_profile_name(self) -> str:
        """Extract profile name from XML"""
        if self.root is None:
            return "Unknown"

        # Try to get from ActionProfiles attribute
        action_profiles = self.root.find('ActionProfiles')
        if action_profiles is not None:
            profile_name = action_profiles.get('profileName')
            if profile_name:
                return profile_name

        # Try to get from root attribute
        profile_name = self.root.get('profileName')
        if profile_name:
            return profile_name

        # Fallback to CustomisationUIHeader label
        header = self.root.find('CustomisationUIHeader')
        if header is not None:
            label = header.get('label')
            if label:
                return label

        return "Unknown"

    def get_categories(self) -> List[str]:
        """Extract category labels from XML"""
        if self.root is None:
            return []

        categories = []
        header = self.root.find('CustomisationUIHeader')
        if header is not None:
            categories_elem = header.find('categories')
            if categories_elem is not None:
                for category in categories_elem.findall('category'):
                    label = category.get('label', '')
                    if label:
                        categories.append(label)

        return categories

    def get_devices(self) -> List[Device]:
        """Extract device information from XML"""
        if self.root is None:
            return []

        devices = []

        # Get device declarations from CustomisationUIHeader
        header = self.root.find('CustomisationUIHeader')
        if header is not None:
            devices_elem = header.find('devices')
            if devices_elem is not None:
                for device_elem in devices_elem:
                    device_type = device_elem.tag  # keyboard, mouse, joystick
                    instance = int(device_elem.get('instance', 1))

                    # Try to find product info from options elements
                    product_id = None
                    product_name = None

                    for options in self.root.findall('options'):
                        if (options.get('type') == device_type and
                            int(options.get('instance', 1)) == instance):
                            product = options.get('Product', '')
                            if product:
                                product_id = product
                                # Extract readable name from product string
                                # Format: " VKBsim Gladiator EVO R    {GUID}"
                                if '{' in product:
                                    product_name = product.split('{')[0].strip()
                                else:
                                    product_name = product.strip()
                            break

                    devices.append(Device(
                        device_type=device_type,
                        instance=instance,
                        product_id=product_id,
                        product_name=product_name
                    ))
        # Fallback: If no devices found and no CustomisationUIHeader, extract from options elements
        # This handles preset profiles that don't have CustomisationUIHeader
        if not devices:
            # Look for options inside ActionProfiles (preset format)
            action_profiles = self.root.find('ActionProfiles')
            if action_profiles is not None:
                all_options = action_profiles.findall('options')

                for options in all_options:
                    device_type = options.get('type')
                    if not device_type:
                        continue

                    instance = int(options.get('instance', 1))
                    product = options.get('Product', '')

                    product_id = None
                    product_name = None

                    if product:
                        product_id = product
                        # Extract readable name from product string
                        # Format: " T.16000M" or "Thrustmaster TWCS Throttle {GUID}"
                        if '{' in product:
                            product_name = product.split('{')[0].strip()
                        else:
                            product_name = product.strip()

                    devices.append(Device(
                        device_type=device_type,
                        instance=instance,
                        product_id=product_id,
                        product_name=product_name
                    ))

        return devices

    def get_action_maps(self) -> List[ActionMap]:
        """Extract all action maps and their bindings"""
        if self.root is None:
            return []

        action_maps = []

        # Find ActionProfiles element (actionmaps are nested inside it)
        action_profiles = self.root.find('ActionProfiles')
        if action_profiles is None:
            action_profiles = self.root

        for actionmap_elem in action_profiles.findall('actionmap'):
            map_name = actionmap_elem.get('name', 'unknown')
            actions = []

            for action_elem in actionmap_elem.findall('action'):
                action_name = action_elem.get('name', 'unknown')

                # Find all rebind elements (actions can have multiple bindings)
                for rebind_elem in action_elem.findall('rebind'):
                    input_code = rebind_elem.get('input', '')
                    activation_mode = rebind_elem.get('activationMode')

                    # Only add if there's an actual input binding (not empty)
                    if input_code and input_code.strip():
                        actions.append(ActionBinding(
                            action_name=action_name,
                            input_code=input_code,
                            activation_mode=activation_mode
                        ))

            # Only add action map if it has bindings
            if actions:
                action_maps.append(ActionMap(
                    name=map_name,
                    actions=actions
                ))

        return action_maps

    def _merge_default_bindings(self, user_profile: ControlProfile):
        """
        Merge default bindings from actionmaps.xml where user bindings are unmapped.
        User bindings override defaults.
        """
        try:
            # Parse default actionmaps.xml
            default_tree = ET.parse(self.default_actionmaps_path)
            default_root = default_tree.getroot()
        except (ET.ParseError, FileNotFoundError) as e:
            logger.warning(f"Could not parse default actionmaps: {e}")
            return

        # Build lookup: (actionmap_name, action_name) -> List[ActionBinding]
        user_bindings_map = {}
        for action_map in user_profile.action_maps:
            for binding in action_map.actions:
                key = (action_map.name, binding.action_name)
                if key not in user_bindings_map:
                    user_bindings_map[key] = []
                user_bindings_map[key].append(binding)

        # Find ActionProfiles element in default bindings
        default_action_profiles = default_root.find('ActionProfiles')
        if default_action_profiles is None:
            default_action_profiles = default_root

        # Parse default bindings and merge
        for actionmap_elem in default_action_profiles.findall('actionmap'):
            map_name = actionmap_elem.get('name', '')

            # Find or create corresponding ActionMap in user profile
            user_action_map = self._find_or_create_actionmap(user_profile, map_name)

            for action_elem in actionmap_elem.findall('action'):
                action_name = action_elem.get('name', '')
                key = (map_name, action_name)

                # Check if user has this binding
                user_bindings = user_bindings_map.get(key, [])

                # Determine if we should use default bindings
                # Use defaults only if ALL user bindings are unmapped (end with '_')
                should_use_default = True
                if user_bindings:
                    for ub in user_bindings:
                        if not ub.input_code.rstrip().endswith('_'):
                            should_use_default = False
                            break

                if should_use_default:
                    # Get default bindings for this action
                    default_bindings = []
                    for rebind_elem in action_elem.findall('rebind'):
                        input_code = rebind_elem.get('input', '')
                        activation_mode = rebind_elem.get('activationMode')
                        if input_code and input_code.strip() and not input_code.rstrip().endswith('_'):
                            default_bindings.append(ActionBinding(
                                action_name=action_name,
                                input_code=input_code,
                                activation_mode=activation_mode
                            ))

                    # Replace unmapped user bindings with defaults
                    if default_bindings:
                        if user_bindings:
                            # Remove unmapped user bindings
                            for ub in user_bindings:
                                user_action_map.actions.remove(ub)

                        # Add default bindings
                        user_action_map.actions.extend(default_bindings)

    def _find_or_create_actionmap(self, profile: ControlProfile, map_name: str) -> ActionMap:
        """Find existing action map or create new one"""
        for action_map in profile.action_maps:
            if action_map.name == map_name:
                return action_map

        # Create new action map
        new_map = ActionMap(name=map_name, actions=[])
        profile.action_maps.append(new_map)
        return new_map
