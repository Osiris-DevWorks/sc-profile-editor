"""
Configuration tab for device-to-joystick mapping management
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QPushButton,
                              QComboBox, QTableWidget, QTableWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from utils.input_detector import InputDetector
from utils.settings import AppSettings

logger = logging.getLogger(__name__)


class ConfigTab(QWidget):
    """Tab for managing device configuration and device-to-js mappings"""

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
        self.devices_table.setMaximumHeight(150)
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
        instructions.setStyleSheet("color: #666; font-size: 10px; font-style: italic;")
        instructions.setWordWrap(True)
        mapping_layout.addWidget(instructions)
        mapping_layout.addSpacing(10)

        # Create mapping dropdowns for js1, js2, js3
        self.mapping_combos = {}
        for i in range(1, 4):
            js_label = f"js{i}"
            h_layout = QHBoxLayout()
            h_layout.addWidget(QLabel(f"{js_label}:"))
            h_layout.setContentsMargins(20, 5, 20, 5)

            combo = QComboBox()
            combo.addItem("-- None --", None)
            self.mapping_combos[js_label] = combo

            h_layout.addWidget(combo)
            h_layout.addStretch()
            mapping_layout.addLayout(h_layout)

        mapping_layout.addSpacing(10)

        # Save button
        save_btn = QPushButton("Save Configuration")
        save_btn.clicked.connect(self.on_save_config_clicked)
        save_layout = QHBoxLayout()
        save_layout.addStretch()
        save_layout.addWidget(save_btn)
        mapping_layout.addLayout(save_layout)

        layout.addWidget(mapping_group)
        layout.addStretch()

    def refresh_devices(self):
        """Refresh the list of connected devices"""
        try:
            self.current_devices = InputDetector.get_available_devices()
            logger.debug(f"Found {len(self.current_devices)} devices")

            # Update devices table
            self.devices_table.setRowCount(len(self.current_devices))
            for row, device in enumerate(self.current_devices):
                device_type = device.get('type', 'unknown').capitalize()
                product_name = device.get('name', 'Unknown Device')
                instance = str(device.get('instance', '?'))

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
                if current_selection:
                    for i in range(combo.count()):
                        if combo.itemData(i) == current_selection:
                            combo.setCurrentIndex(i)
                            break

                combo.blockSignals(False)

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

    def on_save_config_clicked(self):
        """Handle Save Configuration button click"""
        self.save_device_config()
