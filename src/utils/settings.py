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
