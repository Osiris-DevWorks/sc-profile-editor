#!/usr/bin/env python3
"""
Add all missing actions from other profiles to the BLANK profile,
organized by actionmap with proper XML formatting.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

def indent(elem, level=0):
    """Add pretty-print indentation to XML elements."""
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
        for child in elem:
            indent(child, level + 1)
        if not child.tail or not child.tail.strip():
            child.tail = i
    else:
        if level and (not elem.tail or not elem.tail.strip()):
            elem.tail = i

def extract_actions_from_profile(xml_file):
    """Extract all actions grouped by actionmap from an XML profile."""
    actions_by_map = defaultdict(set)

    try:
        tree = ET.parse(xml_file)
        root = tree.getroot()

        for actionmap in root.findall('actionmap'):
            map_name = actionmap.get('name')
            if map_name:
                for action in actionmap.findall('action'):
                    action_name = action.get('name')
                    if action_name:
                        actions_by_map[map_name].add(action_name)

        return actions_by_map
    except Exception as e:
        print(f"Error parsing {xml_file}: {e}")
        return {}

def main():
    profile_dir = Path("example-profiles")
    all_profiles = list(profile_dir.glob("*.xml"))

    # Collect all actions from all profiles
    master_actions = defaultdict(set)

    for profile in sorted(all_profiles):
        actions = extract_actions_from_profile(profile)
        for map_name, action_set in actions.items():
            master_actions[map_name].update(action_set)

    # Read the BLANK profile
    blank_profile = profile_dir / "layout_BLANK_exported.xml"

    # Register namespace to preserve original formatting
    ET.register_namespace('', '')

    blank_tree = ET.parse(blank_profile)
    blank_root = blank_tree.getroot()

    blank_actions = extract_actions_from_profile(blank_profile)

    # Track what we're adding
    added_count = 0
    maps_modified = set()

    # For each actionmap in the BLANK profile, add missing actions
    for blank_actionmap in blank_root.findall('actionmap'):
        map_name = blank_actionmap.get('name')
        if map_name and map_name in master_actions:
            missing = master_actions[map_name] - blank_actions.get(map_name, set())

            if missing:
                maps_modified.add(map_name)
                # Sort missing actions and add them
                for action_name in sorted(missing):
                    # Create new action element
                    action_elem = ET.Element('action')
                    action_elem.set('name', action_name)

                    # Create rebind element
                    rebind_elem = ET.SubElement(action_elem, 'rebind')
                    rebind_elem.set('input', 'js1_ ')

                    # Append to actionmap
                    blank_actionmap.append(action_elem)
                    added_count += 1

    # Also add any actionmaps that don't exist in BLANK profile at all
    blank_map_names = {am.get('name') for am in blank_root.findall('actionmap')}
    missing_maps = set(master_actions.keys()) - blank_map_names

    for missing_map_name in sorted(missing_maps):
        maps_modified.add(missing_map_name)
        # Create new actionmap
        actionmap_elem = ET.Element('actionmap')
        actionmap_elem.set('name', missing_map_name)

        # Add all actions from master for this map
        for action_name in sorted(master_actions[missing_map_name]):
            action_elem = ET.Element('action')
            action_elem.set('name', action_name)

            rebind_elem = ET.SubElement(action_elem, 'rebind')
            rebind_elem.set('input', 'js1_ ')

            actionmap_elem.append(action_elem)
            added_count += 1

        # Insert before closing </ActionMaps> tag
        blank_root.append(actionmap_elem)

    # Apply proper indentation
    indent(blank_root)

    # Write back to file with XML declaration
    tree_string = ET.tostring(blank_root, encoding='unicode')
    with open(blank_profile, 'w', encoding='utf-8') as f:
        f.write('<?xml version="1.0" encoding="utf-8"?>\n')
        f.write(tree_string)

    print(f"Updated {blank_profile}")
    print(f"Added {added_count} actions")
    print(f"Modified {len(maps_modified)} actionmaps:")
    for map_name in sorted(maps_modified):
        print(f"  - {map_name}")

if __name__ == "__main__":
    main()
