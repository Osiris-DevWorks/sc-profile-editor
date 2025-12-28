"""
Data models for Star Citizen profiles
"""

from dataclasses import dataclass
from typing import List, Dict, Optional


@dataclass
class Device:
    """Represents a game controller device"""
    device_type: str  # keyboard, mouse, joystick
    instance: int
    product_id: Optional[str] = None
    product_name: Optional[str] = None


@dataclass
class ActionBinding:
    """Represents a single action binding"""
    action_name: str
    input_code: str
    activation_mode: Optional[str] = None
    custom_label: Optional[str] = None


@dataclass
class ActionMap:
    """Represents a group of related actions (e.g., spaceship_movement)"""
    name: str
    actions: List[ActionBinding]


@dataclass
class ControlProfile:
    """Represents a complete Star Citizen control profile"""
    profile_name: str
    devices: List[Device]
    action_maps: List[ActionMap]
    categories: List[str]
    is_modified: bool = False  # Track if profile has unsaved changes
    source_xml_path: Optional[str] = None  # Path to original XML file
    merged_defaults: bool = False  # Track if default bindings were merged into this profile
    # Device configuration preservation fields (for export)
    _source_deviceoptions: Optional[object] = None  # Raw ElementTree element for deviceoptions
    _source_options: Optional[List[object]] = None  # Raw ElementTree elements for options
    _source_modifiers: Optional[object] = None  # Raw ElementTree element for modifiers

    def get_all_bindings(self) -> List[ActionBinding]:
        """Get all action bindings across all action maps"""
        bindings = []
        for action_map in self.action_maps:
            bindings.extend(action_map.actions)
        return bindings

    def mark_modified(self):
        """Mark the profile as having unsaved changes"""
        self.is_modified = True

    def mark_saved(self):
        """Mark the profile as saved (no unsaved changes)"""
        self.is_modified = False
