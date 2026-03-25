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
from registry.action_registry import get_action_registry

logger = logging.getLogger(__name__)


class ProfileParser:
    """Parser for Star Citizen XML profile files"""

    def __init__(self, xml_path: str, use_bundled_defaults: bool = True):
        self.xml_path = xml_path
        self.use_bundled_defaults = use_bundled_defaults
        self.tree = None
        self.root = None

        # Get registry for master template (contains 1,085 actions)
        self.registry = get_action_registry()

        # Get base path for bundled resources (kept for backwards compatibility)
        if getattr(sys, 'frozen', False):
            # Running as PyInstaller executable
            base_path = sys._MEIPASS
        else:
            # Running as script
            base_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            base_path = os.path.dirname(base_path)  # Go up to project root

        # Path to bundled default bindings (kept for backwards compatibility)
        if use_bundled_defaults:
            self.default_actionmaps_path = os.path.join(base_path, 'default-bindings', 'actionmaps.xml')
        else:
            self.default_actionmaps_path = None

    def parse(self) -> ControlProfile:
        """
        Parse the XML file and return ControlProfile object with complete action structure.
        Uses ActionRegistry master template (UNBIND_ALL.xml) with source profile overlay.
        """
        try:
            self.tree = ET.parse(self.xml_path)
            self.root = self.tree.getroot()
        except ET.ParseError as e:
            raise ValueError(f"Failed to parse XML file: {e}")
        except FileNotFoundError:
            raise FileNotFoundError(f"XML file not found: {self.xml_path}")

        # Get master template from action registry
        try:
            template_tree = self.registry.get_master_template_tree()
            template_root = template_tree.getroot()
            logger.info(f"Loaded master template from ActionRegistry: {self.registry.get_action_count()} actions")
        except Exception as e:
            logger.error(f"Failed to get master template from registry: {e}, falling back to source-only parsing")
            return self._parse_source_only()

        # Overlay source customizations onto template
        profile = self._overlay_source_onto_template(template_root, self.root)

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

    def _parse_source_only(self) -> ControlProfile:
        """
        Fallback method: Parse source profile without template overlay.
        This maintains old behavior when blank.xml is unavailable.
        """
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

        # Legacy merge if needed (only when overlay system unavailable)
        if self.default_actionmaps_path and os.path.exists(self.default_actionmaps_path):
            logger.info("Using legacy merge system (overlay system unavailable)")
            self._merge_default_bindings(profile)
            profile.merged_defaults = True

        return profile

    def _overlay_source_onto_template(self, template_root: ET.Element, source_root: ET.Element) -> ControlProfile:
        """
        Overlay source profile customizations onto blank.xml template.

        Template provides:
        - Complete action structure (621 actions)
        - Default categories
        - Unmapped bindings

        Source overlays:
        - Profile name
        - Devices
        - Device options
        - Options elements (axis configs)
        - Actual bindings
        - Modifiers

        Args:
            template_root: Root element from blank.xml
            source_root: Root element from source profile

        Returns:
            ControlProfile with complete structure + source customizations
        """
        # STEP 1: Extract profile name from source (with fallback to template)
        profile_name = self._extract_profile_name(source_root)
        if not profile_name or profile_name == "BLANK":
            profile_name = self._extract_profile_name(template_root)
        logger.info(f"Profile name: {profile_name}")

        # STEP 2: Extract devices from source (critical for user's hardware)
        devices = self._extract_devices(source_root)
        if not devices:
            logger.warning("Source profile has no devices, using template defaults")
            devices = self._extract_devices(template_root)
        logger.info(f"Devices: {len(devices)} device(s)")

        # STEP 3: Extract categories from source, fallback to template
        categories = self._extract_categories(source_root)
        if not categories:
            categories = self._extract_categories(template_root)
        logger.info(f"Categories: {len(categories)} category(ies)")

        # STEP 4: Parse complete action structure from template
        template_action_maps = self._extract_action_maps(template_root, keep_unmapped=True)
        logger.info(f"Loaded {len(template_action_maps)} actionmaps from template with {sum(len(am.actions) for am in template_action_maps)} total actions")

        # STEP 5: Parse user's bindings from source
        source_action_maps = self._extract_action_maps(source_root, keep_unmapped=False)
        logger.info(f"Loaded {len(source_action_maps)} actionmaps from source with {sum(len(am.actions) for am in source_action_maps)} mapped actions")

        # STEP 6: Build lookup map for source bindings
        source_bindings_map = self._build_bindings_lookup(source_action_maps)

        # STEP 7: Overlay source bindings onto template structure
        overlaid_action_maps = self._overlay_bindings(template_action_maps, source_bindings_map)

        # STEP 8: Create profile with complete structure
        profile = ControlProfile(
            profile_name=profile_name,
            devices=devices,
            action_maps=overlaid_action_maps,
            categories=categories,
            is_modified=False,
            source_xml_path=self.xml_path,
            merged_defaults=False  # Not using old merge system
        )

        logger.info(f"Created profile with {len(profile.action_maps)} actionmaps and {len(profile.get_all_bindings())} total bindings")

        return profile

    def _extract_profile_name(self, root: ET.Element) -> str:
        """Extract profile name from XML root (works for both template and source)"""
        if root is None:
            return "Unknown"

        # Try ActionProfiles attribute
        action_profiles = root.find('ActionProfiles')
        if action_profiles is not None:
            profile_name = action_profiles.get('profileName')
            if profile_name:
                return profile_name

        # Try root attribute
        profile_name = root.get('profileName')
        if profile_name:
            return profile_name

        # Try CustomisationUIHeader label
        header = root.find('CustomisationUIHeader')
        if header is not None:
            label = header.get('label')
            if label:
                return label

        return "Unknown"

    def _extract_devices(self, root: ET.Element) -> List[Device]:
        """Extract devices from XML root"""
        if root is None:
            return []

        devices = []

        # Get device declarations from CustomisationUIHeader
        header = root.find('CustomisationUIHeader')
        if header is not None:
            devices_elem = header.find('devices')
            if devices_elem is not None:
                for device_elem in devices_elem:
                    device_type = device_elem.tag
                    instance = int(device_elem.get('instance', 1))

                    product_id = None
                    product_name = None

                    for options in root.findall('options'):
                        if (options.get('type') == device_type and
                            int(options.get('instance', 1)) == instance):
                            product = options.get('Product', '')
                            if product:
                                product_id = product
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

        # Fallback: extract from options elements in ActionProfiles
        if not devices:
            action_profiles = root.find('ActionProfiles')
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

    def _extract_categories(self, root: ET.Element) -> List[str]:
        """Extract categories from XML root"""
        if root is None:
            return []

        categories = []
        header = root.find('CustomisationUIHeader')
        if header is not None:
            categories_elem = header.find('categories')
            if categories_elem is not None:
                for category in categories_elem.findall('category'):
                    label = category.get('label', '')
                    if label:
                        categories.append(label)

        return categories

    def _extract_action_maps(self, root: ET.Element, keep_unmapped: bool = False) -> List[ActionMap]:
        """
        Extract action maps from XML root.

        Args:
            root: Root element to extract from
            keep_unmapped: If True, keep unmapped bindings (js1_ ). If False, skip them.

        Returns:
            List of ActionMap objects
        """
        if root is None:
            return []

        action_maps = []

        # Find ActionProfiles element
        action_profiles = root.find('ActionProfiles')
        if action_profiles is None:
            action_profiles = root

        for actionmap_elem in action_profiles.findall('actionmap'):
            map_name = actionmap_elem.get('name', 'unknown')
            actions = []

            for action_elem in actionmap_elem.findall('action'):
                action_name = action_elem.get('name', 'unknown')

                for rebind_elem in action_elem.findall('rebind'):
                    input_code = rebind_elem.get('input', '')
                    activation_mode = rebind_elem.get('activationMode')

                    # Check if binding is empty or unmapped
                    if not input_code or not input_code.strip():
                        continue

                    is_unmapped = input_code.rstrip().endswith('_')
                    if is_unmapped and not keep_unmapped:
                        continue

                    actions.append(ActionBinding(
                        action_name=action_name,
                        input_code=input_code,
                        activation_mode=activation_mode
                    ))

            # Add actionmap even if empty when keeping unmapped (for template)
            if actions or keep_unmapped:
                action_maps.append(ActionMap(
                    name=map_name,
                    actions=actions
                ))

        return action_maps

    def _build_bindings_lookup(self, action_maps: List[ActionMap]) -> Dict[tuple, List[ActionBinding]]:
        """
        Build lookup map for fast binding access.

        Returns:
            Dict mapping (actionmap_name, action_name) -> List[ActionBinding]
        """
        bindings_map = {}
        for action_map in action_maps:
            for binding in action_map.actions:
                key = (action_map.name, binding.action_name)
                if key not in bindings_map:
                    bindings_map[key] = []
                bindings_map[key].append(binding)
        return bindings_map

    def _overlay_bindings(self, template_maps: List[ActionMap], source_bindings: Dict[tuple, List[ActionBinding]]) -> List[ActionMap]:
        """
        Overlay source bindings onto template action maps.

        For each action in template:
        - If source has mapped binding → use source binding (once)
        - If source has only unmapped → keep template unmapped (js1_ )
        - If source has no binding → keep template unmapped

        Args:
            template_maps: Complete action structure from blank.xml
            source_bindings: User's bindings lookup map

        Returns:
            List of ActionMaps with overlaid bindings
        """
        result_maps = []
        processed_source_keys = set()

        for template_map in template_maps:
            overlaid_actions = []
            processed_actions = set()  # Track which actions we've already handled

            for template_binding in template_map.actions:
                action_name = template_binding.action_name
                key = (template_map.name, action_name)
                processed_source_keys.add(key)

                # Check if source has bindings for this action
                if key in source_bindings and key not in processed_actions:
                    source_bindings_for_action = source_bindings[key]

                    # Filter out unmapped bindings from source
                    mapped_bindings = [b for b in source_bindings_for_action
                                     if not b.input_code.rstrip().endswith('_')]

                    if mapped_bindings:
                        # Use source's mapped bindings (only once per action, not once per template binding)
                        overlaid_actions.extend(mapped_bindings)
                        processed_actions.add(key)
                    else:
                        # Source only has unmapped, keep template's binding
                        overlaid_actions.append(template_binding)
                elif key not in processed_actions:
                    # No source binding, keep template's binding
                    overlaid_actions.append(template_binding)

            # Create new ActionMap with overlaid bindings
            result_maps.append(ActionMap(
                name=template_map.name,
                actions=overlaid_actions
            ))

        # Handle source-only actions (shouldn't happen but handle gracefully)
        source_only_maps = {}
        for (map_name, action_name), bindings in source_bindings.items():
            key = (map_name, action_name)
            if key not in processed_source_keys:
                logger.warning(f"Source has action not in template: {map_name}.{action_name}")
                if map_name not in source_only_maps:
                    source_only_maps[map_name] = []
                source_only_maps[map_name].extend(bindings)

        # Append source-only actionmaps
        for map_name, actions in source_only_maps.items():
            # Check if map exists in results
            existing_map = None
            for result_map in result_maps:
                if result_map.name == map_name:
                    existing_map = result_map
                    break

            if existing_map:
                existing_map.actions.extend(actions)
            else:
                logger.warning(f"Source has actionmap not in template: {map_name}")
                result_maps.append(ActionMap(name=map_name, actions=actions))

        return result_maps

    def _merge_default_bindings(self, user_profile: ControlProfile):
        """
        DEPRECATED: Legacy method for merging actionmaps.xml.
        This is only used when blank.xml is unavailable.
        New code should use _overlay_source_onto_template() instead.

        Merge default bindings from actionmaps.xml where user bindings are unmapped.
        User bindings override defaults.
        """
        logger.warning("Using deprecated _merge_default_bindings - the overlay system with blank.xml should be preferred")
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
