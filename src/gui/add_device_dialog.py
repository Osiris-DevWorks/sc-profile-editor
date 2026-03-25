"""
Dialog for adding a new device to the current profile
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
                              QListWidget, QListWidgetItem, QPushButton, QMessageBox)
from PyQt6.QtCore import Qt
import logging

logger = logging.getLogger(__name__)


class AddDeviceDialog(QDialog):
    """Dialog for selecting a device to add to the profile"""

    def __init__(self, pdf_manager, current_profile, current_device_mapping, parent=None):
        """
        Initialize the Add Device dialog

        Args:
            pdf_manager: PDFTemplateManager instance with loaded templates
            current_profile: ControlProfile object (to filter already-added devices)
            current_device_mapping: dict mapping "js1"/"js2"/"js3" to device names
            parent: Parent widget
        """
        super().__init__(parent)
        self.pdf_manager = pdf_manager
        self.current_profile = current_profile
        self.current_device_mapping = current_device_mapping
        self.selected_template = None
        self.selected_slot = None

        self.setWindowTitle("Add Device to Profile")
        self.setGeometry(100, 100, 600, 400)
        self.setup_ui()

    def setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # === LEFT PANEL: Device List ===
        devices_label = QLabel("Available Devices (with field mappings):")
        layout.addWidget(devices_label)

        self.device_list = QListWidget()
        self.device_list.itemSelectionChanged.connect(self._on_device_selected)
        layout.addWidget(self.device_list)

        # Populate device list grouped by manufacturer
        self._populate_device_list()

        # === RIGHT PANEL: Joystick Slot Selection ===
        slot_layout = QHBoxLayout()
        slot_label = QLabel("Assign to joystick slot:")
        slot_layout.addWidget(slot_label)

        self.slot_combo = QComboBox()
        self.slot_combo.addItems(["-- Select --", "js1", "js2", "js3"])
        slot_layout.addWidget(self.slot_combo)
        slot_layout.addStretch()

        layout.addLayout(slot_layout)

        # === BUTTON PANEL ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        confirm_btn = QPushButton("Add Device")
        confirm_btn.clicked.connect(self.on_confirm_clicked)
        button_layout.addWidget(confirm_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _populate_device_list(self):
        """Populate the device list grouped by manufacturer"""
        eligible_templates = self.pdf_manager.get_templates_with_field_mapping()

        if not eligible_templates:
            QMessageBox.information(
                self,
                "No Devices Available",
                "No device templates with complete field mappings are available.\n"
                "Add a field_mapping.json to your device templates to make them addable."
            )
            self.close()
            return

        # Get set of devices already in the profile (by product_name)
        profile_device_names = set()
        if self.current_profile:
            for device in self.current_profile.devices:
                if device.product_name:
                    profile_device_names.add(device.product_name)

        # Group templates by manufacturer
        by_manufacturer = {}
        for template in eligible_templates:
            # Skip if device is already in profile
            if template.name in profile_device_names:
                logger.debug(f"Skipping {template.name} - already in profile")
                continue

            manufacturer = template.manufacturer or "Other"
            if manufacturer not in by_manufacturer:
                by_manufacturer[manufacturer] = []
            by_manufacturer[manufacturer].append(template)

        # Add items to list, sorted by manufacturer
        for manufacturer in sorted(by_manufacturer.keys()):
            # Add manufacturer section header
            header = QListWidgetItem(f"--- {manufacturer} ---")
            header.setFlags(header.flags() & ~Qt.ItemFlag.ItemIsSelectable)
            header.setBackground(header.background().color().darker(115))
            self.device_list.addItem(header)

            # Add templates for this manufacturer
            for template in sorted(by_manufacturer[manufacturer], key=lambda t: t.name):
                item = QListWidgetItem(template.name)
                item.setData(Qt.ItemDataRole.UserRole, template)  # Store template as data
                self.device_list.addItem(item)

    def _on_device_selected(self):
        """Called when a device is selected from the list"""
        selected = self.device_list.selectedItems()
        if selected:
            item = selected[0]
            self.selected_template = item.data(Qt.ItemDataRole.UserRole)

    def on_confirm_clicked(self):
        """Called when Confirm button is clicked"""
        if not self.selected_template:
            QMessageBox.warning(self, "No Device Selected", "Please select a device from the list.")
            return

        slot_str = self.slot_combo.currentText()
        if slot_str == "-- Select --":
            QMessageBox.warning(self, "No Slot Selected", "Please select a joystick slot (js1, js2, or js3).")
            return

        self.selected_slot = slot_str
        self.accept()

    def get_selected_device_and_slot(self):
        """
        Get the selected device template and slot

        Returns:
            Tuple of (PDFDeviceTemplate, slot_str) or (None, None) if cancelled
        """
        return (self.selected_template, self.selected_slot)
