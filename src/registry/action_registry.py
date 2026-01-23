"""
Action Registry - Single source of truth for all Star Citizen actions
Loads from UNBIND_ALL.xml containing all 1,085 bindable actions across 49 actionmaps
"""

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class ActionMetadata:
    """Metadata for a single Star Citizen action"""
    action_name: str
    actionmap_name: str
    category: Optional[str] = None
    is_deprecated: bool = False
    description: Optional[str] = None
    default_device: Optional[str] = None  # kb1, js1, etc.


@dataclass
class ActionMapMetadata:
    """Metadata for an actionmap (group of related actions)"""
    name: str
    action_count: int
    actions: List[str]  # List of action names


class ActionRegistry:
    """
    Single source of truth for all Star Citizen actions.
    Loaded from UNBIND_ALL.xml (1,085 actions across 49 actionmaps).
    Provides validation, discovery, and template services for profile system.
    """

    def __init__(self):
        self._actions: Dict[Tuple[str, str], ActionMetadata] = {}  # (actionmap, action) -> metadata
        self._actionmaps: Dict[str, ActionMapMetadata] = {}  # actionmap_name -> metadata
        self._action_to_map: Dict[str, str] = {}  # action_name -> actionmap_name
        self._loaded: bool = False
        self._xml_tree: Optional[ET.ElementTree] = None
        self._xml_root: Optional[ET.Element] = None

    def load_from_xml(self, xml_path: str) -> None:
        """
        Load all actions from UNBIND_ALL.xml or equivalent master template.

        Args:
            xml_path: Path to UNBIND_ALL.xml file

        Raises:
            FileNotFoundError: If XML file not found
            ET.ParseError: If XML is malformed
        """
        try:
            logger.info(f"Loading action registry from: {xml_path}")

            # Parse XML
            self._xml_tree = ET.parse(xml_path)
            self._xml_root = self._xml_tree.getroot()

            if self._xml_root.tag != "ActionMaps":
                raise ValueError(f"Invalid root element: {self._xml_root.tag}, expected 'ActionMaps'")

            # Extract all actions
            action_count = 0
            for actionmap_elem in self._xml_root.findall('actionmap'):
                actionmap_name = actionmap_elem.get('name', '')
                if not actionmap_name:
                    logger.warning("Found actionmap without name attribute")
                    continue

                actions = []
                for action_elem in actionmap_elem.findall('action'):
                    action_name = action_elem.get('name', '')
                    if not action_name:
                        logger.warning(f"Found action without name in actionmap {actionmap_name}")
                        continue

                    # Create metadata
                    metadata = ActionMetadata(
                        action_name=action_name,
                        actionmap_name=actionmap_name
                    )

                    # Store in registry
                    key = (actionmap_name, action_name)
                    self._actions[key] = metadata
                    self._action_to_map[action_name] = actionmap_name
                    actions.append(action_name)
                    action_count += 1

                # Store actionmap metadata
                if actions:
                    self._actionmaps[actionmap_name] = ActionMapMetadata(
                        name=actionmap_name,
                        action_count=len(actions),
                        actions=actions
                    )

            self._loaded = True
            logger.info(f"Action registry loaded: {action_count} actions across {len(self._actionmaps)} actionmaps")

        except FileNotFoundError:
            logger.error(f"Action registry file not found: {xml_path}")
            raise
        except ET.ParseError as e:
            logger.error(f"Failed to parse action registry XML: {e}")
            raise

    def is_loaded(self) -> bool:
        """Check if registry has been loaded"""
        return self._loaded

    def is_valid_action(self, actionmap_name: str, action_name: str) -> bool:
        """
        Validate if an action exists in the registry.

        Args:
            actionmap_name: Name of the actionmap (e.g., 'spaceship_weapons')
            action_name: Name of the action (e.g., 'v_attack1')

        Returns:
            True if action exists, False otherwise
        """
        if not self._loaded:
            logger.warning("Registry not loaded, cannot validate action")
            return False

        return (actionmap_name, action_name) in self._actions

    def get_action_metadata(self, actionmap_name: str, action_name: str) -> Optional[ActionMetadata]:
        """
        Get metadata for a specific action.

        Args:
            actionmap_name: Name of the actionmap
            action_name: Name of the action

        Returns:
            ActionMetadata if action exists, None otherwise
        """
        if not self._loaded:
            return None

        return self._actions.get((actionmap_name, action_name))

    def get_actionmap_metadata(self, actionmap_name: str) -> Optional[ActionMapMetadata]:
        """
        Get metadata for an actionmap.

        Args:
            actionmap_name: Name of the actionmap

        Returns:
            ActionMapMetadata if actionmap exists, None otherwise
        """
        if not self._loaded:
            return None

        return self._actionmaps.get(actionmap_name)

    def list_all_actions(self) -> List[ActionMetadata]:
        """
        Get all registered actions.

        Returns:
            List of all ActionMetadata objects
        """
        if not self._loaded:
            return []

        return list(self._actions.values())

    def list_actionmaps(self) -> List[str]:
        """
        Get all actionmap names.

        Returns:
            List of actionmap names
        """
        if not self._loaded:
            return []

        return sorted(self._actionmaps.keys())

    def find_actionmap_for_action(self, action_name: str) -> Optional[str]:
        """
        Find which actionmap contains a given action (by name only).

        Args:
            action_name: Name of the action to find

        Returns:
            Actionmap name if found, None otherwise
        """
        if not self._loaded:
            return None

        return self._action_to_map.get(action_name)

    def get_master_template_tree(self) -> ET.ElementTree:
        """
        Get the complete XML tree for use as master template in overlay system.

        Returns:
            ElementTree of the master template (from UNBIND_ALL.xml)

        Raises:
            RuntimeError: If registry not loaded
        """
        if not self._loaded or self._xml_tree is None:
            raise RuntimeError("Registry not loaded, cannot get master template tree")

        return self._xml_tree

    def validate_profile(self, profile: 'ControlProfile') -> List[str]:  # noqa: F821
        """
        Validate a profile against the registry.
        Returns list of warnings/errors for unknown or deprecated actions.

        Args:
            profile: ControlProfile to validate

        Returns:
            List of validation warning/error messages
        """
        if not self._loaded:
            return ["Registry not loaded, cannot validate profile"]

        warnings = []

        # Check each action in the profile
        for action_map in profile.action_maps:
            for action in action_map.actions:
                if not self.is_valid_action(action_map.name, action.action_name):
                    warnings.append(
                        f"Unknown action: {action_map.name}.{action.action_name}"
                    )

        return warnings

    def get_action_count(self) -> int:
        """Get total number of actions in registry"""
        return len(self._actions)

    def get_actionmap_count(self) -> int:
        """Get total number of actionmaps in registry"""
        return len(self._actionmaps)


# Singleton instance
_registry_instance: Optional[ActionRegistry] = None


def get_action_registry() -> ActionRegistry:
    """
    Get or create the singleton ActionRegistry instance.
    Loads from UNBIND_ALL.xml on first access.

    Returns:
        Singleton ActionRegistry instance
    """
    global _registry_instance

    if _registry_instance is None:
        _registry_instance = ActionRegistry()

        # Determine path to UNBIND_ALL.xml
        try:
            # Try bundled UNBIND_ALL.xml first
            import sys
            import os

            # Handle both dev and PyInstaller environments
            try:
                base_path = sys._MEIPASS  # PyInstaller
            except AttributeError:
                # Development environment - go up from src/registry to project root
                current_dir = Path(__file__).parent.parent.parent
                base_path = str(current_dir)

            unbind_path = os.path.join(base_path, 'UNBIND_ALL.xml')

            if not os.path.exists(unbind_path):
                logger.error(f"UNBIND_ALL.xml not found at {unbind_path}")
                logger.error("Falling back to empty registry")
                return _registry_instance

            _registry_instance.load_from_xml(unbind_path)

        except Exception as e:
            logger.error(f"Failed to initialize action registry: {e}", exc_info=True)
            # Return empty registry rather than crashing
            logger.warning("Using empty action registry - profile loading may be incomplete")

    return _registry_instance
