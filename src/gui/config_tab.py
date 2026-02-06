"""
Configuration tab for device-to-joystick mapping management
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
                              QComboBox, QTableWidget, QTableWidgetItem, QMessageBox, QLineEdit, QFileDialog, QCheckBox,
                              QListWidget, QListWidgetItem)
from PyQt6.QtCore import Qt, pyqtSignal

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.input_detector import InputDetector
from utils.settings import AppSettings

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
        self.setup_ui()
        self.load_device_config()

    def setup_ui(self):
        """Set up the configuration tab UI"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # === CONNECTED DEVICES SECTION ===
        devices_group = QGroupBox("Connected Devices")
        devices_layout = QVBoxLayout()
        devices_group.setLayout(devices_layout)

        # Devices table
        self.devices_table = QTableWidget()
        self.devices_table.setColumnCount(3)
        self.devices_table.setHorizontalHeaderLabels(["Device Type", "Product Name", "Instance"])
        self.devices_table.setColumnWidth(0, 120)
        self.devices_table.setColumnWidth(1, 300)
        self.devices_table.setColumnWidth(2, 100)
        self.devices_table.setMaximumHeight(200)  # Increased from 150 to show all devices
        devices_layout.addWidget(self.devices_table)

        # Refresh button
        refresh_btn = QPushButton("Refresh Devices")
        refresh_btn.clicked.connect(self.on_refresh_devices_clicked)
        refresh_layout = QHBoxLayout()
        refresh_layout.addStretch()
        refresh_layout.addWidget(refresh_btn)
        devices_layout.addLayout(refresh_layout)

        layout.addWidget(devices_group)

        # === DEVICE MAPPING SECTION ===
        mapping_group = QGroupBox("Device-to-Joystick Mapping")
        mapping_layout = QVBoxLayout()
        mapping_group.setLayout(mapping_layout)

        # Instructions
        instructions = QLabel(
            "Map physical devices to joystick slots (js1, js2, js3, etc.).\n"
            "This helps keep your profile working when devices are connected in different order."
        )
        instructions.setStyleSheet("QLabel { color: palette(text); font-size: 10px; font-style: italic; }")
        instructions.setWordWrap(True)
        mapping_layout.addWidget(instructions)
        mapping_layout.addSpacing(10)

        # Create mapping dropdowns for js1, js2, js3
        self.mapping_combos = {}
        for i in range(1, 4):
            js_label = f"js{i}"
            h_layout = QHBoxLayout()
            h_layout.setContentsMargins(20, 8, 20, 8)
            h_layout.setSpacing(15)  # Better spacing between elements

            label = QLabel(f"{js_label}:")
            label.setMinimumWidth(40)  # Ensure label has minimum width
            h_layout.addWidget(label)

            combo = QComboBox()
            combo.addItem("-- None --", None)
            combo.setMinimumWidth(200)  # Ensure combo box is wide enough
            self.mapping_combos[js_label] = combo

            h_layout.addWidget(combo)
            h_layout.addStretch()
            mapping_layout.addLayout(h_layout)

        mapping_layout.addSpacing(10)

        # Auto-populate and Save buttons
        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(20, 10, 20, 10)
        button_layout.setSpacing(10)

        auto_populate_btn = QPushButton("Auto-Populate from Connected Devices")
        auto_populate_btn.setToolTip("Automatically map connected joysticks to js1, js2, js3 based on detection order")
        auto_populate_btn.setMinimumHeight(35)
        auto_populate_btn.clicked.connect(self.on_auto_populate_clicked)
        button_layout.addWidget(auto_populate_btn)

        button_layout.addStretch()

        save_btn = QPushButton("Save Configuration")
        save_btn.setMinimumHeight(35)
        save_btn.clicked.connect(self.on_save_config_clicked)
        button_layout.addWidget(save_btn)

        mapping_layout.addLayout(button_layout)

        layout.addWidget(mapping_group)

        # === STAR CITIZEN PROFILES DIRECTORY SECTION ===
        sc_dir_group = QGroupBox("Star Citizen Profiles Directory")
        sc_dir_layout = QVBoxLayout()
        sc_dir_group.setLayout(sc_dir_layout)

        # Instructions
        sc_instructions = QLabel(
            "Specify the location of your Star Citizen control profiles.\n"
            "This allows the app to easily import profiles from your SC installation."
        )
        sc_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 10px; font-style: italic; }")
        sc_instructions.setWordWrap(True)
        sc_dir_layout.addWidget(sc_instructions)
        sc_dir_layout.addSpacing(10)

        # Directory path input
        path_input_layout = QHBoxLayout()
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
        sc_dir_layout.addSpacing(10)

        # Save button
        sc_save_btn = QPushButton("Save SC Directory")
        sc_save_btn.clicked.connect(self.on_save_sc_directory_clicked)
        sc_save_layout = QHBoxLayout()
        sc_save_layout.addStretch()
        sc_save_layout.addWidget(sc_save_btn)
        sc_dir_layout.addLayout(sc_save_layout)

        layout.addWidget(sc_dir_group)

        # === SYSTEM TRAY SECTION ===
        tray_group = QGroupBox("System Tray")
        tray_layout = QVBoxLayout()
        tray_group.setLayout(tray_layout)

        # Instructions
        tray_instructions = QLabel(
            "Control minimize-to-tray behavior.\n"
            "When enabled, minimizing the window will hide it to the system tray instead of the taskbar."
        )
        tray_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 10px; font-style: italic; }")
        tray_instructions.setWordWrap(True)
        tray_layout.addWidget(tray_instructions)
        tray_layout.addSpacing(10)

        # Minimize to tray checkbox
        self.minimize_to_tray_checkbox = QCheckBox("Minimize to system tray when window is minimized")
        self.minimize_to_tray_checkbox.setChecked(self.settings.get_minimize_to_tray_enabled())
        self.minimize_to_tray_checkbox.stateChanged.connect(self.on_minimize_to_tray_changed)
        tray_layout.addWidget(self.minimize_to_tray_checkbox)

        layout.addWidget(tray_group)

        # === INPUT FILTERING SECTION ===
        filter_group = QGroupBox("Input Filtering")
        filter_layout = QVBoxLayout()
        filter_group.setLayout(filter_layout)

        # Instructions
        filter_instructions = QLabel(
            "Filter inputs that constantly trigger (e.g., VKB STECS mode selector).\n"
            "These inputs will be ignored during input detection."
        )
        filter_instructions.setStyleSheet("QLabel { color: palette(text); font-size: 10px; font-style: italic; }")
        filter_instructions.setWordWrap(True)
        filter_layout.addWidget(filter_instructions)
        filter_layout.addSpacing(10)

        # Current filters list
        filter_list_label = QLabel("Current Filters:")
        filter_layout.addWidget(filter_list_label)

        self.filter_list_widget = QListWidget()
        self.filter_list_widget.setMaximumHeight(120)
        filter_layout.addWidget(self.filter_list_widget)

        # Buttons
        filter_button_layout = QHBoxLayout()

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
        layout.addStretch()

        # Load current filters into the list
        self.load_ignored_inputs()

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

            # Update mapping dropdowns with current devices
            # Also clean up device_mapping to remove disconnected devices
            connected_device_names = set()
            for device in self.current_devices:
                if device.get('type') == 'joystick':
                    connected_device_names.add(device.get('name', f"Joystick {device.get('instance', 0)}"))

            for combo in self.mapping_combos.values():
                combo.blockSignals(True)
                current_selection = combo.currentData()
                combo.clear()
                combo.addItem("-- None --", None)

                # Add all joystick devices
                for device in self.current_devices:
                    if device.get('type') == 'joystick':
                        instance = device.get('instance', 0)
                        product_name = device.get('name', f"Joystick {instance}")
                        display_text = f"js{instance}: {product_name}"
                        combo.addItem(display_text, product_name)

                # Restore previous selection if still available
                if current_selection and current_selection in connected_device_names:
                    for i in range(combo.count()):
                        if combo.itemData(i) == current_selection:
                            combo.setCurrentIndex(i)
                            break

                combo.blockSignals(False)

            # Clean up device_mapping: remove devices that are no longer connected
            updated_mapping = {}
            for js_label, device_name in self.device_mapping.items():
                if device_name in connected_device_names:
                    updated_mapping[js_label] = device_name

            if updated_mapping != self.device_mapping:
                logger.info(f"Cleaned up device mapping: removed {len(self.device_mapping) - len(updated_mapping)} disconnected device(s)")
                self.device_mapping = updated_mapping
                # Save the cleaned up mapping
                self.settings.set_device_config(updated_mapping)

            logger.info(f"Devices refreshed: {len(self.current_devices)} devices found")

        except Exception as e:
            logger.error(f"Error refreshing devices: {e}", exc_info=True)
            QMessageBox.warning(self, "Device Refresh Error", f"Failed to refresh devices:\n{e}")

    def load_device_config(self):
        """Load device configuration from settings"""
        try:
            self.device_mapping = self.settings.get_device_config()
            logger.debug(f"Loaded device mapping: {self.device_mapping}")

            # Apply mapping to dropdowns
            for js_label, combo in self.mapping_combos.items():
                device_name = self.device_mapping.get(js_label)
                if device_name:
                    for i in range(combo.count()):
                        if combo.itemData(i) == device_name:
                            combo.setCurrentIndex(i)
                            break

            self.refresh_devices()

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

            self.settings.set_device_config(new_mapping)
            self.device_mapping = new_mapping
            logger.info(f"Device config saved: {new_mapping}")

            QMessageBox.information(self, "Success", "Device configuration saved successfully!")

        except Exception as e:
            logger.error(f"Error saving device config: {e}", exc_info=True)
            QMessageBox.warning(self, "Save Error", f"Failed to save device configuration:\n{e}")

    def on_refresh_devices_clicked(self):
        """Handle Refresh Devices button click"""
        self.refresh_devices()
        QMessageBox.information(self, "Devices Refreshed", f"Found {len(self.current_devices)} device(s)")

    def on_auto_populate_clicked(self):
        """Auto-populate device mappings from connected joysticks"""
        try:
            # Get list of connected joystick devices
            joysticks = [d for d in self.current_devices if d.get('type') == 'joystick']

            if not joysticks:
                QMessageBox.warning(self, "No Joysticks", "No joystick devices are currently connected.")
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

            # Show summary message
            summary = f"Auto-populated {len(joysticks)} joystick device mapping(s):\n\n"
            for idx, device in enumerate(joysticks[:3], 1):
                summary += f"js{idx}: {device.get('name', f'Joystick {idx}')}\n"

            QMessageBox.information(self, "Auto-Population Complete", summary)
            logger.info(f"Auto-populated device mappings: {summary}")

        except Exception as e:
            logger.error(f"Error auto-populating device mappings: {e}", exc_info=True)
            QMessageBox.warning(self, "Auto-Population Error", f"Failed to auto-populate device mappings:\n{e}")

    def on_save_config_clicked(self):
        """Handle Save Configuration button click"""
        self.save_device_config()

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
