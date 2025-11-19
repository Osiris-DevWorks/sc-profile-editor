#!/usr/bin/env python3
"""
Analyze all profiles to find unique actions by actionmap.
"""

import xml.etree.ElementTree as ET
from pathlib import Path
from collections import defaultdict

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

    print(f"Found {len(all_profiles)} profiles\n")

    for profile in sorted(all_profiles):
        print(f"Processing: {profile.name}")
        actions = extract_actions_from_profile(profile)

        for map_name, action_set in actions.items():
            master_actions[map_name].update(action_set)
            print(f"  {map_name}: {len(action_set)} actions")

    # Now read the BLANK profile to see what it's missing
    blank_profile = profile_dir / "layout_BLANK_exported.xml"
    blank_actions = extract_actions_from_profile(blank_profile)

    print("\n" + "="*80)
    print("MISSING ACTIONS IN BLANK PROFILE")
    print("="*80 + "\n")

    total_missing = 0

    for map_name in sorted(master_actions.keys()):
        missing = master_actions[map_name] - blank_actions.get(map_name, set())

        if missing:
            print(f"{map_name}:")
            for action in sorted(missing):
                print(f"  - {action}")
            print()
            total_missing += len(missing)

    print(f"Total missing actions: {total_missing}")

    # Output in format suitable for XML insertion
    print("\n" + "="*80)
    print("XML TO ADD (copy into layout_BLANK_exported.xml)")
    print("="*80 + "\n")

    for map_name in sorted(master_actions.keys()):
        missing = master_actions[map_name] - blank_actions.get(map_name, set())

        if missing:
            print(f"<!-- Missing actions in {map_name} -->")
            for action in sorted(missing):
                print(f'<action name="{action}">')
                print(f'  <rebind input="js1_ "/>')
                print(f'</action>')
            print()

if __name__ == "__main__":
    main()
