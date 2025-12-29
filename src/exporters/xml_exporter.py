"""
XML exporter for saving modified Star Citizen control profiles
"""

import xml.etree.ElementTree as ET
from xml.dom import minidom
import sys
import os
import logging
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.profile_model import ControlProfile, ActionBinding

logger = logging.getLogger(__name__)


class XMLExporter:
    """Export modified control profiles to Star Citizen XML format"""

    def __init__(self, original_xml_path: str):
        """
        Initialize exporter with original XML path

        Args:
            original_xml_path: Path to the original XML file (to preserve structure)
        """
        self.original_xml_path = original_xml_path
        self.tree = None
        self.root = None

    def export(self, profile: ControlProfile, output_path: str) -> bool:
        """
        Export modified profile to XML file

        Args:
            profile: Modified ControlProfile object
            output_path: Path where to save the modified XML

        Returns:
            True if successful, False otherwise
        """
        try:
            # Load original XML to preserve structure
            self.tree = ET.parse(self.original_xml_path)
            self.root = self.tree.getroot()

            # Update profile name if changed
            if profile.profile_name:
                self.root.set('profileName', profile.profile_name)

                # Also update in CustomisationUIHeader
                header = self.root.find('CustomisationUIHeader')
                if header is not None:
                    header.set('label', profile.profile_name)

            # Update all rebind elements with modified bindings
            self.update_bindings(profile)

            # Write to output file with proper formatting
            self.write_formatted_xml(output_path)

            logger.info(f"Successfully exported profile to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to export profile: {e}", exc_info=True)
            return False

    def update_bindings(self, profile: ControlProfile):
        """Update all rebind elements in the XML tree"""

        # Create a lookup map for quick access to modified bindings
        # Key: (action_map_name, action_name) -> ActionBinding
        binding_map = {}

        # Debug: Count all bindings in profile
        total_bindings = sum(len(am.actions) for am in profile.action_maps)
        logger.info(f"EXPORT DEBUG: Starting update_bindings with {total_bindings} total bindings in profile")

        for action_map in profile.action_maps:
            for binding in action_map.actions:
                key = (action_map.name, binding.action_name)
                # Store all bindings with this key (support for multiple bindings per action)
                if key not in binding_map:
                    binding_map[key] = []
                binding_map[key].append(binding)
                # Debug: Log all mouse5 bindings
                if "mouse5" in binding.input_code:
                    logger.info(f"EXPORT DEBUG: Found mouse5 binding: {binding.action_name} in {action_map.name} -> {binding.input_code}")
                # Debug: Log all shift+equals bindings
                if "lshift+equals" in binding.input_code or "rshift+equals" in binding.input_code:
                    logger.info(f"EXPORT DEBUG: Found shift+equals binding: {binding.action_name} in {action_map.name} -> {binding.input_code}")

        # Debug: Log emote_salute if found
        emote_key = None
        emote_found = False
        for key in binding_map:
            if key[1] == 'emote_salute':
                emote_key = key
                emote_found = True
                logger.info(f"EXPORT DEBUG: Found emote_salute in binding_map: key={key}, bindings={[(b.action_name, b.input_code) for b in binding_map[key]]}")
                break
        if not emote_found:
            logger.info("EXPORT DEBUG: emote_salute NOT found in binding_map!")

        # Track which (action_map_name, action_name) pairs have been processed
        processed_keys = set()

        # Iterate through XML and update matching bindings
        for actionmap_elem in self.root.findall('.//actionmap'):
            map_name = actionmap_elem.get('name', '')

            # Find ALL actions with this name in the actionmap (may have duplicates from overlay)
            action_elems = actionmap_elem.findall('action')
            for action_elem in action_elems:
                action_name = action_elem.get('name', '')
                key = (map_name, action_name)

                # Skip if we've already processed this action in this actionmap
                if key in processed_keys:
                    continue

                # Check if we have modified bindings for this action
                if key not in binding_map:
                    continue

                modified_bindings = binding_map[key]
                # Debug: Log if this is a mouse5 action
                if any("mouse5" in b.input_code for b in modified_bindings):
                    logger.info(f"EXPORT DEBUG: Found mouse5 in XML at {map_name}.{action_name}")

                # Debug log for emote_salute
                if action_name == 'emote_salute':
                    logger.info(f"EXPORT DEBUG: Found emote_salute in XML at {map_name}, modified_bindings={[(b.action_name, b.input_code) for b in modified_bindings]}")
                    old_bindings = [r.get('input') for r in action_elem.findall('rebind')]
                    logger.info(f"EXPORT DEBUG: Old bindings before clear: {old_bindings}")

                # Clear existing rebind elements
                for rebind_elem in list(action_elem.findall('rebind')):
                    action_elem.remove(rebind_elem)

                # Add updated rebind elements (skip empty ones)
                for binding in modified_bindings:
                    # Skip empty/unmapped bindings
                    if not binding.input_code or binding.input_code.rstrip().endswith('_'):
                        logger.debug(f"EXPORT DEBUG: Skipping empty/unbound binding: {binding.action_name} -> {repr(binding.input_code)}")
                        continue

                    # Debug: Log all mouse5 bindings being written
                    if "mouse5" in binding.input_code:
                        logger.info(f"EXPORT DEBUG: Writing mouse5 binding to XML: {binding.action_name} -> {binding.input_code}")
                    # Debug: Log all shift+equals bindings being written
                    if "lshift+equals" in binding.input_code or "rshift+equals" in binding.input_code:
                        logger.info(f"EXPORT DEBUG: Writing shift+equals binding to XML: {binding.action_name} -> {binding.input_code}")

                    rebind_elem = ET.SubElement(action_elem, 'rebind')
                    rebind_elem.set('input', binding.input_code)

                    # Add activation mode if specified
                    if binding.activation_mode:
                        rebind_elem.set('activationMode', binding.activation_mode)

                    # Debug log for emote_salute
                    if action_name == 'emote_salute':
                        logger.info(f"EXPORT DEBUG: Set emote_salute rebind to: {binding.input_code}")
                        new_bindings = [r.get('input') for r in action_elem.findall('rebind')]
                        logger.info(f"EXPORT DEBUG: New bindings after update: {new_bindings}")

                processed_keys.add(key)
                logger.debug(f"Updated binding: {map_name}.{action_name} -> {[b.input_code for b in modified_bindings if b.input_code and not b.input_code.rstrip().endswith('_')]}")

        # Remove empty/unmapped actions and duplicates from XML
        for actionmap_elem in self.root.findall('.//actionmap'):
            map_name = actionmap_elem.get('name', '')
            # Track which action names we've seen in this actionmap
            # Store as action_name -> list of (elem, has_binding, binding_input_code)
            seen_actions = {}
            actions_to_remove = []

            for action_elem in actionmap_elem.findall('action'):
                action_name = action_elem.get('name', '')

                # Check if action has any non-empty bindings
                rebinds = action_elem.findall('rebind')
                has_binding = any(r.get('input', '').strip() and not r.get('input', '').rstrip().endswith('_') for r in rebinds)

                # Get the actual binding input code if it exists
                binding_input = None
                if has_binding:
                    for r in rebinds:
                        inp = r.get('input', '')
                        if inp.strip() and not inp.rstrip().endswith('_'):
                            binding_input = inp
                            break

                if not has_binding:
                    # Mark empty actions for removal
                    actions_to_remove.append(action_elem)
                elif action_name in seen_actions:
                    # Duplicate action found - keep the one with actual mapped binding, remove unmapped
                    prev_elem, prev_has_binding, prev_binding = seen_actions[action_name]

                    if has_binding and not prev_has_binding:
                        # Current has binding, previous doesn't - remove previous, keep current
                        actions_to_remove.append(prev_elem)
                        seen_actions[action_name] = (action_elem, has_binding, binding_input)
                        logger.debug(f"Removing duplicate unmapped action: {map_name}.{action_name}, keeping mapped version")
                    elif has_binding and prev_has_binding:
                        # Both have bindings - keep first, remove second
                        actions_to_remove.append(action_elem)
                        logger.debug(f"Removing duplicate action: {map_name}.{action_name}")
                    else:
                        # Previous has binding or both are unmapped - keep previous
                        actions_to_remove.append(action_elem)
                        logger.debug(f"Removing duplicate action: {map_name}.{action_name}")
                else:
                    seen_actions[action_name] = (action_elem, has_binding, binding_input)

            # Remove marked actions
            for action_elem in actions_to_remove:
                actionmap_elem.remove(action_elem)

    def write_formatted_xml(self, output_path: str):
        """Write XML with proper formatting and indentation"""

        # Convert ElementTree to string
        xml_string = ET.tostring(self.root, encoding='unicode')

        # Pretty print with minidom
        dom = minidom.parseString(xml_string)
        pretty_xml = dom.toprettyxml(indent=' ', encoding='utf-8')

        # Remove extra blank lines that minidom adds
        lines = pretty_xml.decode('utf-8').split('\n')
        non_empty_lines = [line for line in lines if line.strip()]

        # Write to file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(non_empty_lines))

    @staticmethod
    def create_new_profile(profile: ControlProfile, output_path: str,
                          version: str = "1", options_version: str = "2",
                          rebind_version: str = "2") -> bool:
        """
        Create a new XML profile from scratch (not from an existing file)

        Args:
            profile: ControlProfile object
            output_path: Path where to save the XML
            version: ActionMaps version
            options_version: Options version
            rebind_version: Rebind version

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create root element
            root = ET.Element('ActionMaps')
            root.set('version', version)
            root.set('optionsVersion', options_version)
            root.set('rebindVersion', rebind_version)
            root.set('profileName', profile.profile_name)

            # Create CustomisationUIHeader
            header = ET.SubElement(root, 'CustomisationUIHeader')
            header.set('label', profile.profile_name)
            header.set('description', '')
            header.set('image', '')

            # Add devices
            devices_elem = ET.SubElement(header, 'devices')
            for device in profile.devices:
                device_elem = ET.SubElement(devices_elem, device.device_type)
                device_elem.set('instance', str(device.instance))

            # Add categories
            if profile.categories:
                categories_elem = ET.SubElement(header, 'categories')
                for category in profile.categories:
                    category_elem = ET.SubElement(categories_elem, 'category')
                    category_elem.set('label', category)

            # Add device options
            for device in profile.devices:
                if device.product_id:
                    options_elem = ET.SubElement(root, 'options')
                    options_elem.set('type', device.device_type)
                    options_elem.set('instance', str(device.instance))
                    options_elem.set('Product', device.product_id)

            # Add modifiers (empty for now)
            ET.SubElement(root, 'modifiers')

            # Add action maps and bindings
            for action_map in profile.action_maps:
                actionmap_elem = ET.SubElement(root, 'actionmap')
                actionmap_elem.set('name', action_map.name)

                # Group bindings by action name
                from collections import defaultdict
                actions_dict = defaultdict(list)

                for binding in action_map.actions:
                    actions_dict[binding.action_name].append(binding)

                # Create action elements
                for action_name, bindings in actions_dict.items():
                    action_elem = ET.SubElement(actionmap_elem, 'action')
                    action_elem.set('name', action_name)

                    # Add rebind elements
                    for binding in bindings:
                        rebind_elem = ET.SubElement(action_elem, 'rebind')
                        rebind_elem.set('input', binding.input_code)

                        if binding.activation_mode:
                            rebind_elem.set('activationMode', binding.activation_mode)

            # Write formatted XML
            xml_string = ET.tostring(root, encoding='unicode')
            dom = minidom.parseString(xml_string)
            pretty_xml = dom.toprettyxml(indent=' ', encoding='utf-8')

            # Remove extra blank lines
            lines = pretty_xml.decode('utf-8').split('\n')
            non_empty_lines = [line for line in lines if line.strip()]

            # Write to file
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write('\n'.join(non_empty_lines))

            logger.info(f"Successfully created new profile: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to create new profile: {e}", exc_info=True)
            return False


def _is_valid_star_citizen_profile_structure(xml_path: str) -> bool:
    """
    Check if XML file has a valid Star Citizen profile structure
    Valid structure has ActionMaps as root with CustomisationUIHeader child
    Invalid structure has ActionProfiles wrapper or other non-standard layouts

    Returns:
        True if structure is valid, False otherwise
    """
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # Star Citizen profiles have ActionMaps as root
        if root.tag != 'ActionMaps':
            logger.warning(f"Invalid root element: {root.tag} (expected ActionMaps)")
            return False

        # Should have CustomisationUIHeader child
        if root.find('CustomisationUIHeader') is None:
            logger.warning("Missing CustomisationUIHeader element")
            return False

        # Should NOT have ActionProfiles wrapper (that's invalid for SC)
        if root.find('ActionProfiles') is not None:
            logger.warning("Invalid structure: found ActionProfiles wrapper (preset format)")
            return False

        return True
    except Exception as e:
        logger.error(f"Error validating XML structure: {e}")
        return False


def export_profile(profile: ControlProfile, original_xml_path: str,
                  output_path: str) -> bool:
    """
    Convenience function to export a modified profile

    Args:
        profile: Modified ControlProfile object
        original_xml_path: Path to original XML (for structure preservation)
        output_path: Path where to save the modified XML

    Returns:
        True if successful, False otherwise
    """
    # Check if source XML has valid Star Citizen structure
    # If not (e.g., preset format with ActionProfiles wrapper), create new profile instead
    if not _is_valid_star_citizen_profile_structure(original_xml_path):
        logger.info(f"Source XML has invalid Star Citizen structure, creating new profile instead")
        return XMLExporter.create_new_profile(profile, output_path)

    exporter = XMLExporter(original_xml_path)
    return exporter.export(profile, output_path)
