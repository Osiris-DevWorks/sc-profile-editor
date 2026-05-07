"""
Application settings management using QSettings
"""

import logging
from PyQt6.QtCore import QSettings

logger = logging.getLogger(__name__)


class AppSettings:
    """Manages application settings using QSettings for persistence"""

    def __init__(self):
        """Initialize settings manager"""
        # QSettings automatically stores in platform-appropriate location
        # Windows: HKEY_CURRENT_USER\Software\SC Tools\Star Citizen Profile Viewer
        # macOS: ~/Library/Preferences/com.SC Tools.Star Citizen Profile Viewer.plist
        # Linux: ~/.config/SC Tools/Star Citizen Profile Viewer.conf
        self.settings = QSettings("SC Tools", "Star Citizen Profile Viewer")
        logger.debug(f"Settings file location: {self.settings.fileName()}")

    def get_last_profile_path(self) -> str:
        """
        Get the last opened profile path

        Returns:
            Path to last profile, or empty string if none
        """
        path = self.settings.value("last_profile_path", "", type=str)
        logger.debug(f"Retrieved last profile path: {path}")
        return path

    def set_last_profile_path(self, path: str):
        """
        Save the last opened profile path

        Args:
            path: Full path to the profile XML file
        """
        self.settings.setValue("last_profile_path", path)
        self.settings.sync()  # Force immediate write to disk
        logger.info(f"Saved last profile path: {path}")

    def clear_last_profile_path(self):
        """Clear the last opened profile path"""
        self.settings.remove("last_profile_path")
        self.settings.sync()
        logger.info("Cleared last profile path")

    def get_window_geometry(self):
        """Get saved window geometry"""
        return self.settings.value("window_geometry")

    def set_window_geometry(self, geometry):
        """Save window geometry"""
        self.settings.setValue("window_geometry", geometry)
        self.settings.sync()

    def get_window_state(self):
        """Get saved window state (maximized, etc.)"""
        return self.settings.value("window_state")

    def set_window_state(self, state):
        """Save window state"""
        self.settings.setValue("window_state", state)
        self.settings.sync()

    def get_device_config(self) -> dict:
        """
        Get the device-to-joystick mapping configuration

        Returns:
            Dictionary mapping device names to js slots, e.g.:
            {
                "js1": "VKBsim Gladiator EVO R",
                "js2": "Thrustmaster TWCS Throttle",
                "js3": None
            }
        """
        # Get the raw setting value (stored as a dictionary in QSettings)
        device_config = self.settings.value("device_config", {}, type=dict)
        logger.debug(f"Retrieved device config: {device_config}")
        return device_config

    def set_device_config(self, config: dict):
        """
        Save the device-to-joystick mapping configuration

        Args:
            config: Dictionary mapping js slots to device names
        """
        self.settings.setValue("device_config", config)
        self.settings.sync()
        logger.info(f"Saved device config: {config}")

    def clear_device_config(self):
        """Clear the device configuration"""
        self.settings.remove("device_config")
        self.settings.sync()
        logger.info("Cleared device configuration")

    def get_sc_profiles_directory(self) -> str:
        """
        Get the Star Citizen profiles directory path

        Returns:
            Path to Star Citizen profiles directory, or default path if not set
        """
        default_path = r"C:\Program Files\Roberts Space Industries\StarCitizen\LIVE\USER\Client\0\Controls\Mappings"
        path = self.settings.value("sc_profiles_directory", default_path, type=str)
        logger.debug(f"Retrieved SC profiles directory: {path}")
        return path

    def set_sc_profiles_directory(self, path: str):
        """
        Save the Star Citizen profiles directory path

        Args:
            path: Full path to the Star Citizen Mappings directory
        """
        self.settings.setValue("sc_profiles_directory", path)
        self.settings.sync()
        logger.info(f"Saved SC profiles directory: {path}")

    def clear_sc_profiles_directory(self):
        """Clear the Star Citizen profiles directory setting"""
        self.settings.remove("sc_profiles_directory")
        self.settings.sync()
        logger.info("Cleared SC profiles directory")

    def get_merge_defaults_enabled(self) -> bool:
        """
        DEPRECATED: Get whether default bindings merge is enabled.

        This setting is deprecated as the overlay system with blank.xml is always active.
        The overlay system provides a more comprehensive solution with complete action coverage.

        This method now always returns True for backwards compatibility.

        Returns:
            Always returns True (overlay system always enabled)
        """
        logger.debug("get_merge_defaults_enabled called (deprecated, always returns True)")
        return True

    def set_merge_defaults_enabled(self, enabled: bool):
        """
        DEPRECATED: Save whether default bindings merge is enabled.

        This setting no longer has any effect. The overlay system with blank.xml
        is always active and provides complete action coverage.

        This method is kept for backwards compatibility but is a no-op.

        Args:
            enabled: (ignored - has no effect)
        """
        logger.warning("set_merge_defaults_enabled called but has no effect (deprecated)")
        # Don't save anything - this setting is deprecated

    def get_minimize_to_tray_enabled(self) -> bool:
        """
        Get whether minimize-to-tray is enabled

        Returns:
            True if minimize-to-tray is enabled, False otherwise
        """
        enabled = self.settings.value("minimize_to_tray_enabled", False, type=bool)
        logger.debug(f"Retrieved minimize to tray enabled: {enabled}")
        return enabled

    def set_minimize_to_tray_enabled(self, enabled: bool):
        """
        Save whether minimize-to-tray is enabled

        Args:
            enabled: True to enable minimize-to-tray, False to disable
        """
        self.settings.setValue("minimize_to_tray_enabled", enabled)
        self.settings.sync()
        logger.info(f"Saved minimize to tray enabled: {enabled}")

    def get_ignored_inputs(self) -> list:
        """
        Get the list of input codes that should be filtered/ignored during detection

        Returns:
            List of input code strings (e.g., ["js1_button32", "js2_hat3_up"])
        """
        ignored = self.settings.value("ignored_inputs", [], type=list)
        logger.debug(f"Retrieved ignored inputs: {ignored}")
        return ignored

    def set_ignored_inputs(self, inputs: list):
        """
        Save the list of input codes to ignore

        Args:
            inputs: List of input code strings to filter
        """
        self.settings.setValue("ignored_inputs", inputs)
        self.settings.sync()
        logger.info(f"Saved ignored inputs: {inputs}")

    def add_ignored_input(self, input_code: str) -> bool:
        """
        Add a single input code to the ignore list

        Args:
            input_code: Input code to ignore (e.g., "js1_button32")

        Returns:
            True if added, False if already in list
        """
        ignored = self.get_ignored_inputs()
        if input_code not in ignored:
            ignored.append(input_code)
            self.set_ignored_inputs(ignored)
            logger.info(f"Added input to ignore list: {input_code}")
            return True
        logger.debug(f"Input already in ignore list: {input_code}")
        return False

    def remove_ignored_input(self, input_code: str) -> bool:
        """
        Remove a single input code from the ignore list

        Args:
            input_code: Input code to remove

        Returns:
            True if removed, False if not in list
        """
        ignored = self.get_ignored_inputs()
        if input_code in ignored:
            ignored.remove(input_code)
            self.set_ignored_inputs(ignored)
            logger.info(f"Removed input from ignore list: {input_code}")
            return True
        logger.debug(f"Input not in ignore list: {input_code}")
        return False

    def is_input_ignored(self, input_code: str) -> bool:
        """
        Check if an input code is in the ignore list

        Args:
            input_code: Input code to check

        Returns:
            True if input should be ignored, False otherwise
        """
        ignored = self.get_ignored_inputs()
        return input_code in ignored

    def clear_ignored_inputs(self):
        """Clear all ignored inputs from the list"""
        self.settings.remove("ignored_inputs")
        self.settings.sync()
        logger.info("Cleared all ignored inputs")

    def get_theme(self) -> str:
        """Get the current UI theme name. Falls back to DEFAULT_THEME if unset
        or invalid (e.g. settings file written by an older version with a
        retired theme name).

        The theme module is imported lazily and via two paths because
        AppSettings is reachable both through the bare ``utils.settings``
        path (after main_window's sys.path munge) and through the absolute
        ``src.utils.settings`` path (during early app startup, before any
        widget imports). Whichever path is importable wins."""
        AVAILABLE_THEMES, DEFAULT_THEME = _theme_constants()
        theme = self.settings.value("theme", DEFAULT_THEME, type=str)
        if theme not in AVAILABLE_THEMES:
            logger.warning(f"Persisted theme {theme!r} not recognized; using {DEFAULT_THEME}")
            return DEFAULT_THEME
        return theme

    def set_theme(self, theme: str):
        """Save the selected UI theme. Validated against AVAILABLE_THEMES."""
        AVAILABLE_THEMES, _ = _theme_constants()
        if theme not in AVAILABLE_THEMES:
            logger.error(f"Refusing to save unknown theme {theme!r}")
            return
        self.settings.setValue("theme", theme)
        self.settings.sync()
        logger.info(f"Saved theme: {theme}")


def _theme_constants():
    """Resolve theme constants regardless of which import path is on sys.path.
    Tried absolute first (works during early startup), bare second (works
    after main_window's path munge)."""
    try:
        from src.gui.theme import AVAILABLE_THEMES, DEFAULT_THEME
    except ImportError:
        from gui.theme import AVAILABLE_THEMES, DEFAULT_THEME
    return AVAILABLE_THEMES, DEFAULT_THEME
