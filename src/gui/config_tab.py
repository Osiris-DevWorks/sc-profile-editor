"""
Configuration tab for device-to-joystick mapping management
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
                              QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit, QFileDialog, QCheckBox,
                              QListWidget, QListWidgetItem, QAbstractItemView)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QShowEvent

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.input_detector import InputDetector
from utils.settings import AppSettings
from gui.theme import (apply_theme, AVAILABLE_THEMES,
                       THEME_LIGHT, THEME_DARK, THEME_DEFAULT, THEME_ODW)

logger = logging.getLogger(__name__)


class ConfigTab(QWidget):
    """Tab for managing device configuration and device-to-js mappings"""

    # Signal emitted when connected devices change
    devices_changed = pyqtSignal(list)  # Emits list of connected devices

    def __init__(self, parent=None):
        super().__init__(parent)
        self.settings = AppSettings()
        self.current_devices = []
        self.device_mapping = {}  # js1 -> device name mapping
        self._current_profile = None  # Current loaded profile (for add device feature)
        self.setup_ui()
        self.load_device_config()

    def showEvent(self, event: QShowEvent):
        """
        Automatically refresh connected devices when the Config tab is shown.
        This fixes Issue #17 by detecting newly connected devices when the user
        switches to the Config tab, without requiring a manual refresh click.
        """
        super().showEvent(event)
        if event.isAccepted():
            logger.debug("Config tab shown - auto-refreshing device list")
            self.refresh_devices()

    def setup_ui(self):
        """Set up the configuration tab UI"""
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Reduce spacing between sections
        layout.setContentsMargins(5, 5, 5, 5)  # Reduce margins
        self.setLayout(layout)

        # === APPEARANCE SECTION ===
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QHBoxLayout()
        appearance_layout.setContentsMargins(8, 5, 8, 8)
        appearance_group.setLayout(appearance_layout)

        appearance_layout.addWidget(QLabel("Theme:"))
        self.theme_combo = QComboBox()
        self.theme_combo.setToolTip(
            "Switch the app theme. Takes effect immediately across the main "
            "window, header buttons, tabs, and dialogs."
        )
        self.theme_combo.addItem("Default", THEME_DEFAULT)
        self.theme_combo.addItem("Light", THEME_LIGHT)
        self.theme_combo.addItem("Dark", THEME_DARK)
        self.theme_combo.addItem("ODW", THEME_ODW)
        current = self.settings.get_theme()
        idx = self.theme_combo.findData(current)
        if idx >= 0:
            self.theme_combo.setCurrentIndex(idx)
        self.theme_combo.currentIndexChanged.connect(self._on_theme_changed)
        self.theme_combo.setMaximumWidth(150)
        appearance_layout.addWidget(self.theme_combo)
        appearance_layout.addStretch()

        layout.addWidget(appearance_group)

        # === CONNECTED DEVICES SECTION ===
        devices_group = QGroupBox("Connected Devices")
        devices_layout = QVBoxLayout()
        devices_layout.setSpacing(3)  # Reduce internal spacing
        devices_layout.setContentsMargins(8, 5, 8, 8)  # Reduce margins
        devices_group.setLayout(devices_layout)

        # Devices table
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels(["Device Type", "Device Name", "Instance"])
        self.devices_table.setColumnWidth(0, 120)
        self.devices_table.setColumnWidth(1, 300)
        self.devices_table.setColumnWidth(2, 100)
        self.devices_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.devices_table.setAlternatingRowColors(True)  # Better visibility
        self.devices_table.setMaximumHeight(16777215)  # Remove height limit, will auto-size
        devices_layout.addWidget(self.devices_table)

        # Refresh button
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.on_refresh_devices_clicked)
        refresh_layout = QHBoxLayout()
        refresh_layout.setContentsMargins(0, 3, 0, 0)
        refresh_layout.addStretch()
        refresh_layout.addWidget(refresh_btn)
        devices_layout.addLayout(refresh_layout)

        layout.addWidget(devices_group)

        # === DEVICE MAPPING SECTION ===
        mapping_group = QGroupBox("Joystick Number Assignment")
        mapping_layout = QVBoxLayout()
        mapping_layout.setSpacing(2)  # Minimal spacing between elements
        mapping_layout.setContentsMargins(8, 5, 8, 8)  # Reduce margins
        mapping_group.setLayout(mapping_layout)

        # Instructions
        instructions = QLabel(
            "Assign physical joystick devices to js1, js2, js3 slots.\n"
            "This ensures your profile works consistently regardless of connection order."
        )
        instructions.setStyleSheet("QLabel { color: palette(text); font-size: 9px; font-style: italic; }")
        instructions.setWordWrap(True)
        mapping_layout.addWidget(instructions)
        mapping_layout.addSpacing(5)  # Minimal spacing

        # Create mapping dropdowns for js1, js2, js3
        self.mapping_combos = {}
        for i in range(1, 4):
            js_label = f"js{i}"
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(10, 2, 10, 2)  # Reduced margins
            h_layout.setSpacing(10)  # Reduced spacing

            label = QLabel(f"{js_label}:")
            label.setMinimumWidth(40)
            h_layout.addWidget(label)

            combo = QComboBox()
            combo.addItem("-- None --", None)
            combo.setMinimumWidth(200)
            self.mapping_combos[js_label] = combo

            h_layout.addWidget(combo)
            h_layout.addStretch()
            mapping_layout.addLayout(h_layout)

        mapping_layout.addSpacing(5)  # Minimal spacing before button

        # Save button (auto-populate happens automatically on tab load)
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(10, 2, 10, 2)  # Reduced margins
        button_layout.setSpacing(10)

        button_layout.addStretch()

        save_btn = QPushButton("Save Configuration")
        save_btn.setMinimumHeight(30)  # Reduced from 35
        save_btn.setMinimumWidth(150)
        save_btn.clicked.connect(self.on_save_config_clicked)
        button_layout.addWidget(save_btn)

        add_device_btn = QPushButton("+ Add Device to Profile")
        add_device_btn.setMinimumHeight(30)
        add_device_btn.setMinimumWidth(200)
        add_device_btn.clicked.connect(self._on_add_device_clicked)
        button_layout.addWidget(add_device_btn)

        mapping_layout.addLayout(button_layout)

        layout.addWidget(mapping_group)

        # === INPUT FILTERING SECTION ===
        filter_group = QGroupBox("Input Filtering")
        filter_layout = QVBoxLayout()
        filter_layout.setSpacing(3)
        filter_layout.setContentsMargins(8, 5, 8, 8)
        filter_group.setLayout(filter_layout)

        # Instructions
        filter_instructions = QLabel(
            "Filter inputs that constantly trigger (e.g., VKB STECS mode selector).\n"
            "These inputs will be ignored during input detection."
        )
        filter_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 9px; font-style: italic; }")
        filter_instructions.setWordWrap(True)
        filter_layout.addWidget(filter_instructions)
        filter_layout.addSpacing(3)

        # Current filters list
        filter_list_label = QLabel("Current Filters:")
        filter_layout.addWidget(filter_list_label)

        self.filter_list_widget = QListWidget()
        self.filter_list_widget.setMaximumHeight(80)  # Reduced from 120
        filter_layout.addWidget(self.filter_list_widget)

        # Buttons
        filter_button_layout = QHBoxLayout()
        filter_button_layout.setContentsMargins(0, 0, 0, 0)
        filter_button_layout.setSpacing(5)

        self.add_filter_btn = QPushButton("Add Input...")
        self.add_filter_btn.clicked.connect(self.on_add_filter_clicked)
        filter_button_layout.addWidget(self.add_filter_btn)

        self.remove_filter_btn = QPushButton("Remove Selected")
        self.remove_filter_btn.clicked.connect(self.on_remove_filter_clicked)
        filter_button_layout.addWidget(self.remove_filter_btn)

        self.clear_filters_btn = QPushButton("Clear All")
        self.clear_filters_btn.clicked.connect(self.on_clear_filters_clicked)
        filter_button_layout.addWidget(self.clear_filters_btn)

        filter_button_layout.addStretch()
        filter_layout.addLayout(filter_button_layout)

        layout.addWidget(filter_group)

        # === STAR CITIZEN PROFILES DIRECTORY SECTION ===
        sc_dir_group = QGroupBox("Star Citizen Profiles Directory")
        sc_dir_layout = QVBoxLayout()
        sc_dir_layout.setSpacing(3)
        sc_dir_layout.setContentsMargins(8, 5, 8, 8)
        sc_dir_group.setLayout(sc_dir_layout)

        # Instructions
        sc_instructions = QLabel(
            "Specify the location of your Star Citizen control profiles.\n"
            "This allows the app to easily import profiles from your SC installation."
        )
        sc_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 9px; font-style: italic; }")
        sc_instructions.setWordWrap(True)
        sc_dir_layout.addWidget(sc_instructions)
        sc_dir_layout.addSpacing(3)

        # Directory path input
        path_input_layout = QHBoxLayout()
        path_input_layout.setContentsMargins(0, 0, 0, 0)
        path_input_layout.setSpacing(5)
        path_input_layout.addWidget(QLabel("Directory:"))
        self.sc_profiles_path_input = QLineEdit()
        self.sc_profiles_path_input.setPlaceholderText("C:\\Program Files\\Roberts Space Industries\\StarCitizen\\LIVE\\USER\\Client\\0\\Controls\\Mappings")
        self.sc_profiles_path_input.setText(self.settings.get_sc_profiles_directory())
        path_input_layout.addWidget(self.sc_profiles_path_input)

        # Browse button
        browse_btn = QPushButton("Browse...")
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.on_browse_sc_directory)
        path_input_layout.addWidget(browse_btn)

        sc_dir_layout.addLayout(path_input_layout)
        sc_dir_layout.addSpacing(3)

        # Save button
        sc_save_btn = QPushButton("Save SC Directory")
        sc_save_btn.clicked.connect(self.on_save_sc_directory_clicked)
        sc_save_layout = QHBoxLayout()
        sc_save_layout.setContentsMargins(0, 0, 0, 0)
        sc_save_layout.addStretch()
        sc_save_layout.addWidget(sc_save_btn)
        sc_dir_layout.addLayout(sc_save_layout)

        layout.addWidget(sc_dir_group)

        # === SYSTEM TRAY SECTION ===
        tray_group = QGroupBox("System Tray")
        tray_layout = QVBoxLayout()
        tray_layout.setSpacing(3)
        tray_layout.setContentsMargins(8, 5, 8, 8)
        tray_group.setLayout(tray_layout)

        # Instructions
        tray_instructions = QLabel(
            "Control minimize-to-tray behavior.\n"
            "When enabled, minimizing the window will hide it to the system tray instead of the taskbar."
        )
        tray_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 9px; font-style: italic; }")
        tray_instructions.setWordWrap(True)
        tray_layout.addWidget(tray_instructions)
        tray_layout.addSpacing(3)

        # Minimize to tray checkbox
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to system tray when window is minimized")
        self.minimize_to_tray_checkbox.setChecked(self.settings.get_minimize_to_tray_enabled())
        self.minimize_to_tray_checkbox.stateChanged.connect(self.on_minimize_to_tray_changed)
        tray_layout.addWidget(self.minimize_to_tray_checkbox)

        layout.addWidget(tray_group)

        # Load current filters into the list
        self.load_ignored_inputs()

    def _on_theme_changed(self, _index: int):
        """Defer the actual swap to the next event-loop tick. Calling
        app.setPalette() directly from a QComboBox.currentIndexChanged slot
        crashes Qt 6 because the combo's event chain hasn't finished unwinding.
        """
        theme = self.theme_combo.currentData()
        if theme not in AVAILABLE_THEMES:
            return
        QTimer.singleShot(0, lambda: self._apply_theme_change(theme))

    def _apply_theme_change(self, theme: str):
        """Persist and apply the theme. Runs via QTimer.singleShot so we're
        outside the combo's event handling — required for setPalette safety.
        Asks the main window to re-apply per-button stylesheets so the colored
        header buttons recolor without a restart."""
        from PyQt6.QtWidgets import QApplication
        self.settings.set_theme(theme)
        app = QApplication.instance()
        if app is not None:
            apply_theme(app, theme)
        mw = self.window()
        if hasattr(mw, "refresh_action_buttons"):
            mw.refresh_action_buttons()

    def refresh_devices(self):
        """Refresh the list of connected devices"""
        try:
            self.current_devices = InputDetector.get_available_devices()
            logger.info(f"Found {len(self.current_devices)} devices:")
            for d in self.current_devices:
                logger.info(f"  - {d.get('type')}: {d.get('name')} (instance {d.get('instance')})")

            # Emit signal so other widgets (like Device View) can update
            self.devices_changed.emit(self.current_devices)

            # Update devices table
            logger.info(f"Setting devices table row count to {len(self.current_devices)}")
            self.devices_table.setRowCount(len(self.current_devices))

            for row, device in enumerate(self.current_devices):
                device_type = device.get('type', 'unknown').capitalize()
                product_name = device.get('name', 'Unknown Device')
                instance = str(device.get('instance', '?'))

                logger.info(f"Adding device to table row {row}: {device_type} - {product_name} (instance {instance})")

                type_item = QTableWidgetItem(device_type)
                type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.devices_table.setItem(row, 0, type_item)

                name_item = QTableWidgetItem(product_name)
                name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.devices_table.setItem(row, 1, name_item)

                inst_item = QTableWidgetItem(instance)
                inst_item.setFlags(inst_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.devices_table.setItem(row, 2, inst_item)

            # Dynamically resize table to fit content
            self.devices_table.resizeRowsToContents()
            # Calculate total height needed with padding
            header_height = self.devices_table.horizontalHeader().height()
            rows_height = sum(self.devices_table.rowHeight(i) for i in range(self.devices_table.rowCount()))
            total_height = header_height + rows_height + 10  # Add 10px padding

            # Set both min and fixed height to ensure it displays correctly
            self.devices_table.setMinimumHeight(total_height)
            self.devices_table.setMaximumHeight(total_height)

            # Update mapping dropdowns with current devices
            # Also clean up device_mapping to remove disconnected devices
            connected_device_names = set()
            for device in self.current_devices:
                if device.get('type') == 'joystick':
                    connected_device_names.add(device.get('name', f"Joystick {device.get('instance', 0)}"))

            for combo in self.mapping_combos.values():
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("-- None --", None)

                # Add all joystick devices
                for device in self.current_devices:
                    if device.get('type') == 'joystick':
                        instance = device.get('instance', 0)
                        product_name = device.get('name', f"Joystick {instance}")
                        combo.addItem(product_name, product_name)

                # Reset to "-- None --" - let on_refresh_devices_clicked or load_device_config handle restoration
                combo.setCurrentIndex(0)

                combo.blockSignals(False)

            # Note: Device cleanup is handled in on_refresh_devices_clicked() to avoid
            # modifying the mapping during a simple device list update

            logger.info(f"Devices refreshed: {len(self.current_devices)} devices found")

        except Exception as e:
            logger.error(f"Error refreshing devices: {e}", exc_info=True)
            QMessageBox.warning(self, "Device Refresh Error", f"Failed to refresh devices:\n{e}")

    def set_current_profile(self, profile):
        """
        Set the current loaded profile (used for add device feature)

        Args:
            profile: ControlProfile object or None
        """
        self._current_profile = profile

    def load_device_config(self):
        """Load device configuration from settings, auto-detect on startup"""
        try:
            self.device_mapping = self.settings.get_device_config()
            logger.debug(f"Loaded device mapping: {self.device_mapping}")

            self.refresh_devices()

            # Always auto-populate based on current device detection
            # This ensures the initial state reflects the actual connected devices
            logger.info("Auto-detecting device mapping based on current detection")
            self._auto_populate_internal()

            # Capture the auto-populated mapping so Refresh will preserve it
            auto_detected_mapping = {}
            for js_label, combo in self.mapping_combos.items():
                device_name = combo.currentData()
                if device_name:
                    auto_detected_mapping[js_label] = device_name

            self.device_mapping = auto_detected_mapping
            logger.info(f"Auto-detected device mapping: {auto_detected_mapping}")

        except Exception as e:
            logger.error(f"Error loading device config: {e}", exc_info=True)

    def save_device_config(self):
        """Save current device configuration"""
        try:
            new_mapping = {}
            for js_label, combo in self.mapping_combos.items():
                device_name = combo.currentData()
                if device_name:
                    new_mapping[js_label] = device_name

            self.settings.set_device_config(new_mapping, self.current_devices)
            self.device_mapping = new_mapping
            logger.info(f"Device config saved: {new_mapping}")

            QMessageBox.information(self, "Success", "Device configuration saved successfully!")

        except Exception as e:
            logger.error(f"Error saving device config: {e}", exc_info=True)
            QMessageBox.warning(self, "Save Error", f"Failed to save device configuration:\n{e}")

    def on_refresh_devices_clicked(self):
        """Handle Refresh Devices button click"""
        self.refresh_devices()

        # Get list of currently connected device names
        connected_device_names = set()
        for device in self.current_devices:
            if device.get('type') == 'joystick':
                connected_device_names.add(device.get('name', f"Joystick {device.get('instance', 0)}"))

        # If user has saved a config, preserve it but clean up disconnected devices
        if self.device_mapping and any(self.device_mapping.values()):
            # User has saved a custom mapping, preserve it
            logger.info("Preserving saved device mapping after refresh")

            # First, clean up mapping to remove disconnected devices
            updated_mapping = {}
            for js_label, device_name in self.device_mapping.items():
                if device_name in connected_device_names:
                    updated_mapping[js_label] = device_name
                else:
                    logger.info(f"Removing disconnected device {device_name} from {js_label}")

            if updated_mapping != self.device_mapping:
                self.device_mapping = updated_mapping
                self.settings.set_device_config(updated_mapping, self.current_devices)

            # Now restore the (cleaned up) mapping to combos
            for js_label, combo in self.mapping_combos.items():
                device_name = self.device_mapping.get(js_label)
                if device_name:
                    for i in range(combo.count()):
                        if combo.itemData(i) == device_name:
                            combo.setCurrentIndex(i)
                            logger.info(f"Restored {js_label} to {device_name}")
                            break

            # Auto-assign newly connected devices to empty slots
            assigned_devices = set(self.device_mapping.values())
            unassigned_devices = connected_device_names - assigned_devices

            if unassigned_devices:
                logger.info(f"Found unassigned devices: {unassigned_devices}")
                # Find empty js slots and assign unassigned devices
                for js_label in ["js1", "js2", "js3"]:
                    if not self.device_mapping.get(js_label) and unassigned_devices:
                        device_name = unassigned_devices.pop()
                        self.device_mapping[js_label] = device_name

                        # Set the combo to this device
                        combo = self.mapping_combos[js_label]
                        for i in range(combo.count()):
                            if combo.itemData(i) == device_name:
                                combo.setCurrentIndex(i)
                                logger.info(f"Auto-assigned {js_label} to newly detected {device_name}")
                                break

                # Save the updated mapping
                self.settings.set_device_config(self.device_mapping, self.current_devices)
        else:
            # No saved config, auto-detect mapping from current devices
            logger.info("Auto-detecting device mapping based on current detection")
            self._auto_populate_internal()

        QMessageBox.information(self, "Devices Refreshed", f"Found {len(self.current_devices)} device(s)")

    def _auto_populate_internal(self):
        """Auto-populate device mappings from connected joysticks (internal, silent)"""
        try:
            # Get list of connected joystick devices
            joysticks = [d for d in self.current_devices if d.get('type') == 'joystick']

            if not joysticks:
                logger.debug("No joystick devices connected for auto-population")
                return

            # Sort by instance to ensure consistent ordering
            joysticks.sort(key=lambda d: d.get('instance', 0))

            logger.info(f"Auto-populating device mappings for {len(joysticks)} joystick(s)")

            # Map first N joysticks to js1, js2, js3, etc.
            for idx, device in enumerate(joysticks, 1):
                if idx > 3:
                    # Only map up to js3 for now
                    break

                js_label = f"js{idx}"
                device_name = device.get('name', f"Joystick {idx}")

                # Find and select this device in the corresponding combo
                if js_label in self.mapping_combos:
                    combo = self.mapping_combos[js_label]
                    for i in range(combo.count()):
                        if combo.itemData(i) == device_name:
                            combo.setCurrentIndex(i)
                            logger.info(f"Mapped {js_label} to {device_name}")
                            break

            logger.info(f"Auto-populated device mappings for {len(joysticks)} joystick(s)")

        except Exception as e:
            logger.error(f"Error auto-populating device mappings: {e}", exc_info=True)

    def on_save_config_clicked(self):
        """Handle Save Configuration button click"""
        self.save_device_config()

    def _on_add_device_clicked(self):
        """Handle Add Device to Profile button click"""
        try:
            # Check that a profile is loaded
            if not hasattr(self, '_current_profile') or self._current_profile is None:
                QMessageBox.information(
                    self,
                    "No Profile Loaded",
                    "Please load a profile before adding devices."
                )
                return

            # Import here to avoid circular imports
            from src.gui.add_device_dialog import AddDeviceDialog
            from src.graphics.pdf_template_manager import PDFTemplateManager
            from src.main import get_resource_path

            # Get the PDF manager from main window or create one
            pdf_manager = PDFTemplateManager(get_resource_path("visual-templates"))

            dialog = AddDeviceDialog(
                pdf_manager,
                self._current_profile,
                self.device_mapping,
                parent=self
            )

            if dialog.exec():
                template, slot_str = dialog.get_selected_device_and_slot()
                if template and slot_str:
                    self._add_device_to_profile(template, slot_str)

        except Exception as e:
            logger.error(f"Error in add device dialog: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to open add device dialog:\n{e}")

    def _add_device_to_profile(self, template, slot_str: str):
        """
        Add a new device to the profile

        Args:
            template: PDFDeviceTemplate to add
            slot_str: Joystick slot string (e.g., "js2")
        """
        try:
            from src.models.profile_model import Device

            # Extract slot number (js2 -> 2)
            slot_number = int(slot_str[2:])

            # Create new Device object
            new_device = Device(
                device_type="joystick",
                instance=slot_number,
                product_name=template.name,
                product_id=template.product_ids[0] if template.product_ids else None
            )

            # Add to profile
            self._current_profile.devices.append(new_device)
            self._current_profile.is_modified = True

            # Update device mapping
            self.device_mapping[slot_str] = template.name

            # Save device mapping
            self.settings.set_device_config(self.device_mapping, self.current_devices)

            # Rebuild the js1/js2/js3 combo dropdowns
            self._rebuild_mapping_combos()

            # Emit devices_changed signal so Device View and other widgets update
            self.devices_changed.emit(self.current_devices)

            logger.info(f"Added device '{template.name}' to slot '{slot_str}'")
            QMessageBox.information(
                self,
                "Device Added",
                f"'{template.name}' has been added to slot '{slot_str}'.\n\n"
                f"The device now appears in Device View and Controls Table.\n"
                f"You can now map buttons to this device."
            )

        except Exception as e:
            logger.error(f"Error adding device to profile: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to add device to profile:\n{e}")

    def _rebuild_mapping_combos(self):
        """Rebuild the js1/js2/js3 mapping combo boxes with current devices and mapping"""
        try:
            # Get list of currently connected device names
            connected_device_names = []
            for device in self.current_devices:
                if device.get('type') == 'joystick':
                    connected_device_names.append(device.get('name', f"Joystick {device.get('instance', 0)}"))

            # Add devices from the profile's device list
            if self._current_profile:
                for device in self._current_profile.devices:
                    if device.device_type == 'joystick' and device.product_name:
                        if device.product_name not in connected_device_names:
                            connected_device_names.append(device.product_name)

            # Rebuild combos
            for js_label, combo in self.mapping_combos.items():
                combo.blockSignals(True)
                combo.clear()
                combo.addItem("-- None --", None)

                # Add all devices (both connected and from profile)
                for device_name in sorted(set(connected_device_names)):
                    combo.addItem(device_name, device_name)

                # Restore current selection from mapping
                current_device = self.device_mapping.get(js_label)
                if current_device:
                    for i in range(combo.count()):
                        if combo.itemData(i) == current_device:
                            combo.setCurrentIndex(i)
                            break
                else:
                    combo.setCurrentIndex(0)

                combo.blockSignals(False)

            logger.debug("Rebuilt mapping combo boxes")

        except Exception as e:
            logger.error(f"Error rebuilding mapping combos: {e}", exc_info=True)

    def on_browse_sc_directory(self):
        """Handle Browse button click for Star Citizen directory"""
        try:
            current_path = self.sc_profiles_path_input.text()
            if not current_path or not os.path.exists(current_path):
                current_path = os.path.expandvars(r"C:\Program Files\Roberts Space Industries")

            selected_dir = QFileDialog.getExistingDirectory(
                self,
                "Select Star Citizen Profiles Directory",
                current_path,
                QFileDialog.Option.ShowDirsOnly
            )

            if selected_dir:
                self.sc_profiles_path_input.setText(selected_dir)
                logger.info(f"Selected SC directory: {selected_dir}")

        except Exception as e:
            logger.error(f"Error browsing directory: {e}", exc_info=True)
            QMessageBox.warning(self, "Browse Error", f"Failed to open directory browser:\n{e}")

    def on_save_sc_directory_clicked(self):
        """Handle Save SC Directory button click"""
        try:
            directory = self.sc_profiles_path_input.text().strip()

            if not directory:
                QMessageBox.warning(self, "Invalid Path", "Please enter a valid directory path.")
                return

            if not os.path.exists(directory):
                reply = QMessageBox.question(
                    self,
                    "Directory Not Found",
                    f"The directory does not exist:\n{directory}\n\nDo you want to save it anyway?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply != QMessageBox.StandardButton.Yes:
                    return

            self.settings.set_sc_profiles_directory(directory)
            logger.info(f"SC profiles directory saved: {directory}")
            QMessageBox.information(self, "Success", "Star Citizen profiles directory saved successfully!")

        except Exception as e:
            logger.error(f"Error saving SC directory: {e}", exc_info=True)
            QMessageBox.warning(self, "Save Error", f"Failed to save Star Citizen directory:\n{e}")

    def on_minimize_to_tray_changed(self, state):
        """Handle minimize to tray checkbox state change"""
        try:
            enabled = state == Qt.CheckState.Checked.value
            self.settings.set_minimize_to_tray_enabled(enabled)
            status = "enabled" if enabled else "disabled"
            logger.info(f"Minimize to tray: {status}")
        except Exception as e:
            logger.error(f"Error setting minimize to tray: {e}", exc_info=True)

    def load_ignored_inputs(self):
        """Load and display current ignored inputs"""
        try:
            self.filter_list_widget.clear()
            ignored_inputs = self.settings.get_ignored_inputs()

            for input_code in ignored_inputs:
                # Create a more readable description
                display_text = self._format_input_code(input_code)
                item = QListWidgetItem(display_text)
                item.setData(Qt.ItemDataRole.UserRole, input_code)  # Store actual code
                self.filter_list_widget.addItem(item)

            if ignored_inputs:
                logger.debug(f"Loaded {len(ignored_inputs)} ignored inputs")
            else:
                # Add placeholder text
                placeholder = QListWidgetItem("(No filters configured)")
                placeholder.setFlags(placeholder.flags() & ~Qt.ItemFlag.ItemIsSelectable)
                self.filter_list_widget.addItem(placeholder)

        except Exception as e:
            logger.error(f"Error loading ignored inputs: {e}", exc_info=True)

    def _format_input_code(self, input_code: str) -> str:
        """
        Format input code to human-readable description

        Args:
            input_code: Code like "js1_button32" or "js2_hat3_up"

        Returns:
            Formatted description
        """
        # Parse the input code
        parts = input_code.split('_')
        if len(parts) < 2:
            return input_code

        js_num = parts[0]  # js1, js2, etc.

        if parts[1].startswith('button'):
            button_num = parts[1].replace('button', '')
            return f"{js_num} Button {button_num}"
        elif parts[1].startswith('hat'):
            hat_num = parts[1].replace('hat', '')
            direction = parts[2] if len(parts) > 2 else '?'
            return f"{js_num} Hat {hat_num} {direction.upper()}"
        elif len(parts) >= 2:
            axis_name = parts[1]
            direction = '+' if len(parts) == 2 else parts[2]
            return f"{js_num} {axis_name.upper()} ({direction})"

        return input_code

    def on_add_filter_clicked(self):
        """Handle Add Input button click"""
        try:
            from src.gui.input_filter_dialog import InputFilterDialog

            dialog = InputFilterDialog(self)
            dialog.input_added.connect(self._on_filter_added)
            dialog.exec()

        except Exception as e:
            logger.error(f"Error opening input filter dialog: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to open filter dialog:\n{e}")

    def _on_filter_added(self, input_code: str, input_description: str):
        """
        Handle signal when a new filter is added from the dialog

        Args:
            input_code: Code of the input to filter
            input_description: Description of the input
        """
        try:
            self.load_ignored_inputs()
            logger.info(f"Filter added and UI updated: {input_code}")
        except Exception as e:
            logger.error(f"Error updating filter list: {e}", exc_info=True)

    def on_remove_filter_clicked(self):
        """Handle Remove Selected button click"""
        try:
            selected_item = self.filter_list_widget.currentItem()
            if not selected_item:
                QMessageBox.warning(self, "No Selection", "Please select a filter to remove.")
                return

            input_code = selected_item.data(Qt.ItemDataRole.UserRole)
            if not input_code:
                return

            # Remove from settings
            self.settings.remove_ignored_input(input_code)
            logger.info(f"Removed input from filter list: {input_code}")

            # Reload list
            self.load_ignored_inputs()
            QMessageBox.information(self, "Removed", f"Filter removed: {self._format_input_code(input_code)}")

        except Exception as e:
            logger.error(f"Error removing filter: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to remove filter:\n{e}")

    def on_clear_filters_clicked(self):
        """Handle Clear All button click"""
        try:
            ignored_inputs = self.settings.get_ignored_inputs()
            if not ignored_inputs:
                QMessageBox.information(self, "No Filters", "There are no filters to clear.")
                return

            # Confirmation dialog
            reply = QMessageBox.question(
                self,
                "Clear All Filters",
                f"Are you sure you want to remove all {len(ignored_inputs)} filter(s)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if reply != QMessageBox.StandardButton.Yes:
                return

            # Clear all filters
            self.settings.clear_ignored_inputs()
            logger.info("Cleared all input filters")

            # Reload list
            self.load_ignored_inputs()
            QMessageBox.information(self, "Cleared", "All filters have been removed.")

        except Exception as e:
            logger.error(f"Error clearing filters: {e}", exc_info=True)
            QMessageBox.warning(self, "Error", f"Failed to clear filters:\n{e}")
