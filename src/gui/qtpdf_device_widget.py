"""
QtPdf-based PDF widget with clickable field regions

This widget renders PDFs as images and provides clickable regions
that open dialog popups for editing labels.
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                              QComboBox, QMessageBox, QGraphicsView, QGraphicsScene,
                              QGraphicsPixmapItem, QInputDialog, QPushButton, QSizePolicy, QToolTip, QCheckBox)
from PyQt6.QtGui import QPainter, QFont
from PyQt6.QtCore import Qt, pyqtSignal, QRectF, QTimer

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from graphics.pdf_template_manager import PDFTemplateManager, PDFDeviceTemplate
from models.profile_model import ControlProfile, Device
from parser.label_generator import LabelGenerator
from utils.device_joystick_mapper import DeviceJoystickMapper
from utils.device_splitter import get_friendly_device_name
from utils.settings import AppSettings

logger = logging.getLogger(__name__)


class InteractivePDFGraphicsView(QGraphicsView):
    """Custom QGraphicsView with clickable form fields"""

    # Signal emitted when a field is clicked: (input_code, current_value)
    field_clicked = pyqtSignal(str, str)

    def __init__(self, scene):
        super().__init__(scene)
        self._fit_on_resize = True
        self.field_regions = {}  # input_code -> QRectF (in scene coordinates)
        self.field_values = {}  # input_code -> current_value
        self.full_labels = {}  # input_code -> list of action labels (for tooltips)

        # Tooltip delay support
        try:
            self.setMouseTracking(True)  # Enable mouseMoveEvent
            self.tooltip_timer = QTimer()
            self.tooltip_timer.setSingleShot(True)
            self.tooltip_timer.timeout.connect(self._show_delayed_tooltip)

            # Tooltip minimum display timer - keeps tooltip visible for at least 2 seconds
            self.tooltip_display_timer = QTimer()
            self.tooltip_display_timer.setSingleShot(True)
            self.tooltip_display_timer.timeout.connect(self._hide_tooltip)

            self.pending_tooltip_input_code = None
            self.pending_tooltip_labels = None
            self.pending_tooltip_pos = None
            self.current_hover_field = None
            self.tooltip_minimum_display_ms = 2000  # Minimum 2 seconds to display tooltip
            self.tooltip_visible = False  # Track if tooltip is currently visible

            # Grace period timer - ignores field changes for 500ms after tooltip appears
            self.tooltip_grace_period_timer = QTimer()
            self.tooltip_grace_period_timer.setSingleShot(True)
            self.tooltip_grace_period_timer.timeout.connect(self._end_grace_period)
            self.in_grace_period = False  # Track if we're in the grace period
            self.tooltip_grace_period_ms = 500  # 500ms grace period

            logger.debug("Tooltip support initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing tooltip support: {e}", exc_info=True)

    def set_field_regions(self, field_regions: dict, field_values: dict, full_labels: dict = None):
        """Set clickable field regions"""
        self.field_regions = field_regions
        self.field_values = field_values
        self.full_labels = full_labels or {}  # Store full labels for tooltips
        logger.debug(f"set_field_regions called with {len(field_regions)} regions and full_labels: {bool(full_labels)}")

    def resizeEvent(self, event):
        """Re-fit the view when resized"""
        super().resizeEvent(event)
        if self._fit_on_resize and self.scene() and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def zoom_in(self):
        """Zoom in by 25%"""
        self._fit_on_resize = False  # Disable auto-fit when manually zooming
        self.scale(1.25, 1.25)

    def zoom_out(self):
        """Zoom out by 20%"""
        self._fit_on_resize = False  # Disable auto-fit when manually zooming
        self.scale(0.8, 0.8)

    def fit_to_window(self):
        """Fit the view to the window and re-enable auto-fit"""
        self._fit_on_resize = True
        if self.scene() and not self.scene().sceneRect().isEmpty():
            self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def mouseMoveEvent(self, event):
        """Handle mouse movement for tooltip display"""
        try:
            logger.debug(f"mouseMoveEvent at {event.pos()}, in_grace_period: {self.in_grace_period}")

            # Map view coordinates to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if hovering over any field
            hovered_field = None
            for input_code, rect in self.field_regions.items():
                if rect.contains(scene_pos):
                    hovered_field = input_code
                    break

            logger.debug(f"Found hovered_field: {hovered_field}, current_hover_field: {self.current_hover_field}")

            # If we're in grace period, ignore field changes (prevent race condition)
            if self.in_grace_period and hovered_field == self.current_hover_field:
                logger.debug("In grace period, ignoring mouse movement on same field")
                return

            # If we changed fields, update the tooltip timer
            if hovered_field != self.current_hover_field:
                logger.debug(f"Hover changed from {self.current_hover_field} to {hovered_field}")
                self.current_hover_field = hovered_field
                self.tooltip_timer.stop()
                self.tooltip_display_timer.stop()
                self.tooltip_visible = False
                self.in_grace_period = False
                self.tooltip_grace_period_timer.stop()
                QToolTip.hideText()

                if hovered_field:
                    # Check if this field has multiple actions
                    labels = self.full_labels.get(hovered_field, [])
                    logger.debug(f"Hovering over {hovered_field}, {len(labels)} labels: {labels}")

                    if len(labels) > 1:
                        logger.debug(f"Starting tooltip timer for {hovered_field}")
                        # Store tooltip info and start timer
                        self.pending_tooltip_input_code = hovered_field
                        self.pending_tooltip_labels = labels
                        # Use globalPosition() in PyQt6 (not globalPos())
                        self.pending_tooltip_pos = event.globalPosition().toPoint()

                        # Start timer for 1.5-second delay (gives mouse time to settle)
                        self.tooltip_timer.start(1500)
                else:
                    logger.debug("Not over any field")
        except Exception as e:
            logger.error(f"Error in mouseMoveEvent: {e}", exc_info=True)

    def leaveEvent(self, event):
        """Handle mouse leaving the view"""
        logger.debug("Mouse left view, stopping tooltip timers")
        self.tooltip_timer.stop()
        self.tooltip_display_timer.stop()
        self.tooltip_grace_period_timer.stop()
        self.current_hover_field = None
        self.tooltip_visible = False
        self.in_grace_period = False
        QToolTip.hideText()

        super().leaveEvent(event)

    def mousePressEvent(self, event):
        """Handle mouse clicks to detect field clicks"""
        if event.button() == Qt.MouseButton.LeftButton:
            # Map view coordinates to scene coordinates
            scene_pos = self.mapToScene(event.pos())

            # Check if click is within any field region
            for input_code, rect in self.field_regions.items():
                if rect.contains(scene_pos):
                    # Field clicked - emit signal
                    current_value = self.field_values.get(input_code, "")
                    self.field_clicked.emit(input_code, current_value)
                    return

        # Default handling for non-field clicks
        super().mousePressEvent(event)

    def _show_delayed_tooltip(self):
        """Show the tooltip after the delay expires"""
        logger.debug(f"Tooltip timer expired, showing tooltip for {self.pending_tooltip_input_code}")
        logger.debug(f"Pending labels: {self.pending_tooltip_labels}")

        if self.pending_tooltip_input_code and self.pending_tooltip_labels and self.pending_tooltip_pos:
            # Format tooltip text - extract button number from input code
            # Convert "js1_button5" to "Button 5", "js1_hat1_down" to "HAT1 Down", etc.
            input_code = self.pending_tooltip_input_code
            if "js" in input_code:
                # Remove the "jsX_" prefix to get the button part
                parts = input_code.split("_", 1)  # Split on first underscore
                if len(parts) == 2:
                    button_part = parts[1]  # Get everything after "jsX_"
                    # Format nicely
                    if button_part.startswith("button"):
                        button_name = "Button " + button_part.replace("button", "")
                    elif button_part.startswith("hat"):
                        button_name = button_part.upper()
                    elif button_part.startswith("axis"):
                        button_name = button_part.upper()
                    else:
                        button_name = button_part.upper()
                else:
                    button_name = input_code
            else:
                button_name = input_code

            tooltip_lines = [button_name + ":"]
            for label in self.pending_tooltip_labels:
                tooltip_lines.append(f"• {label}")
            tooltip_text = "\n".join(tooltip_lines)

            logger.debug(f"Showing tooltip: {tooltip_text}")
            # Show tooltip at the stored position
            QToolTip.showText(self.pending_tooltip_pos, tooltip_text, self)

            # Mark tooltip as visible and start minimum display timer
            # This prevents hiding if user moves away during the first 2 seconds
            self.tooltip_visible = True
            self.tooltip_display_timer.start(self.tooltip_minimum_display_ms)

            # Start grace period - ignores mouse movements for 500ms to prevent race condition
            self.in_grace_period = True
            self.tooltip_grace_period_timer.start(self.tooltip_grace_period_ms)

            logger.debug(f"Tooltip visible, started minimum display timer for {self.tooltip_minimum_display_ms}ms and grace period for {self.tooltip_grace_period_ms}ms")
        else:
            logger.warning(f"Tooltip data incomplete: input_code={self.pending_tooltip_input_code}, labels={self.pending_tooltip_labels}, pos={self.pending_tooltip_pos}")

    def _hide_tooltip(self):
        """Allow tooltip to be hidden after minimum display time has expired"""
        logger.debug("Minimum display time expired, tooltip can now be hidden on mouse movement")
        self.tooltip_visible = False

    def _end_grace_period(self):
        """End the grace period after tooltip appears"""
        logger.debug("Grace period ended, now responding to mouse movements")
        self.in_grace_period = False


class QtPdfDeviceWidget(QWidget):
    """Widget for displaying device PDFs with interactive clickable form fields"""

    # Signal emitted when export availability changes
    export_available_changed = pyqtSignal(bool)

    def __init__(self, templates_dir: str):
        super().__init__()
        self.templates_dir = templates_dir
        self.pdf_manager = PDFTemplateManager(templates_dir)
        self.current_profile: ControlProfile = None
        self.current_device: Device = None
        self.current_template: PDFDeviceTemplate = None
        self.current_template_search_name: str = None  # For split devices (e.g., VKB + SEM)
        self.device_mapper: DeviceJoystickMapper = None
        self.current_field_values: dict = {}  # Store current field values
        self.field_to_input_code: dict = {}  # Map PDF field names to input codes

        # Track connected devices for filtering
        self.connected_devices = []  # List of connected device dicts from InputDetector
        self.show_all_templates = False  # Toggle to show all templates or just connected

        self.setup_ui()

    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Device selection with toggle for all templates
        selection_layout = QHBoxLayout()
        selection_layout.addWidget(QLabel("Select Device:"))

        self.device_combo = QComboBox()
        self.device_combo.currentIndexChanged.connect(self.on_device_changed)
        selection_layout.addWidget(self.device_combo, 1)

        # Toggle to show all templates (not just connected devices)
        self.show_all_checkbox = QCheckBox("Show all templates")
        self.show_all_checkbox.setToolTip("When unchecked, only shows templates for connected devices")
        self.show_all_checkbox.stateChanged.connect(self.on_show_all_toggled)
        selection_layout.addWidget(self.show_all_checkbox)

        layout.addLayout(selection_layout)

        # Zoom controls
        zoom_layout = QHBoxLayout()

        zoom_in_btn = QPushButton("Zoom In")
        zoom_in_btn.setMaximumWidth(100)
        zoom_in_btn.clicked.connect(lambda: self.view.zoom_in())
        zoom_layout.addWidget(zoom_in_btn)

        zoom_out_btn = QPushButton("Zoom Out")
        zoom_out_btn.setMaximumWidth(100)
        zoom_out_btn.clicked.connect(lambda: self.view.zoom_out())
        zoom_layout.addWidget(zoom_out_btn)

        fit_btn = QPushButton("Fit to Window")
        fit_btn.setMaximumWidth(120)
        fit_btn.clicked.connect(lambda: self.view.fit_to_window())
        zoom_layout.addWidget(fit_btn)

        zoom_layout.addStretch()
        layout.addLayout(zoom_layout)

        # Graphics view (interactive)
        self.scene = QGraphicsScene()
        self.view = InteractivePDFGraphicsView(self.scene)
        self.view.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.view.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        self.view.setDragMode(QGraphicsView.DragMode.NoDrag)  # Allow clicks
        self.view.field_clicked.connect(self.on_field_clicked)
        layout.addWidget(self.view)

        # Status label
        self.status_label = QLabel("No device selected")
        self.status_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addWidget(self.status_label)

    def set_connected_devices(self, devices: list):
        """
        Set the list of currently connected devices

        Args:
            devices: List of device dicts from InputDetector.get_available_devices()
                     Each dict has: {'type': 'joystick'|'keyboard'|'mouse', 'instance': N, 'name': 'Device Name'}
        """
        self.connected_devices = devices
        logger.debug(f"Connected devices updated: {len(devices)} devices")

        # Reload profile if one is loaded to update device list
        if self.current_profile:
            self.load_profile(self.current_profile)

    def on_show_all_toggled(self, state):
        """Handle toggle for showing all templates vs only connected devices"""
        self.show_all_templates = (state != 0)
        logger.debug(f"Show all templates toggled: {self.show_all_templates}")

        # Reload device list with new filter
        if self.current_profile:
            self.load_profile(self.current_profile)

    def _is_device_connected(self, device: Device) -> bool:
        """Check if a device is actually connected (for visual indicator purposes)"""
        if not self.connected_devices:
            return False  # No devices connected if list is empty

        # For joystick devices, check both instance and product name match
        if device.device_type == 'joystick':
            for connected in self.connected_devices:
                if connected.get('type') == 'joystick':
                    # Match by instance number first
                    if connected.get('instance') == device.instance:
                        # Also check if product name matches (if device has product name)
                        if device.product_name:
                            connected_name = connected.get('name', '').lower()
                            device_product = device.product_name.lower()
                            # Check if the product name appears in the connected device name
                            if device_product in connected_name or any(
                                word in connected_name for word in device_product.split()
                            ):
                                return True
                        else:
                            # No product name in profile, just match by instance
                            return True

        return False

    def load_profile(self, profile: ControlProfile):
        """Load a profile and populate device list"""
        self.current_profile = profile
        self.device_combo.clear()

        if not profile:
            return

        # Create device-to-joystick mapper
        try:
            self.device_mapper = DeviceJoystickMapper(profile,
                os.path.join(self.templates_dir, "template_registry.json"))
        except Exception as e:
            logger.error(f"Error creating device mapper: {e}", exc_info=True)
            self.device_mapper = None

        # Add devices that have PDF templates
        from utils.device_splitter import is_vkb_with_sem, get_base_stick_name

        # Determine which devices to show based on show_all_templates flag
        if self.show_all_templates:
            # Show all available templates, not just connected devices
            logger.debug("Show all templates enabled - displaying all available templates")
            all_templates = self.pdf_manager.get_all_templates()
            # Convert template names to device-like dicts for consistent processing
            joystick_devices = [{'name': t.name, 'instance': 0, 'type': 'joystick'}
                               for t in all_templates]
        else:
            # Use connected devices from Config tab
            # This ensures Device View shows what's actually connected
            joystick_devices = [d for d in self.connected_devices if d.get('type') == 'joystick']

        for device_dict in joystick_devices:
            # Extract device info from connected_devices dict
            device_name = device_dict.get('name', f"Joystick {device_dict.get('instance', 0)}")
            device_instance = device_dict.get('instance', 0)

            # Connected devices from Config tab are always connected
            connection_status = ""
            raw_device_name = device_name

            # Check if this is a VKB device with SEM module
            if is_vkb_with_sem(raw_device_name):
                # Split into two entries: base stick and SEM module

                # 1. Add ALL matching base stick templates (user can choose)
                base_stick_name = get_base_stick_name(raw_device_name)
                matching_templates = self.find_all_matching_templates(base_stick_name)

                if matching_templates:
                    for template in matching_templates:
                        # Store tuple: (device_name, device_instance, template.name)
                        display_text = template.name + connection_status
                        self.device_combo.addItem(display_text, (device_name, device_instance, template.name))
                else:
                    friendly_base_name = get_friendly_device_name(base_stick_name)
                    display_text = f"{friendly_base_name} (No template){connection_status}"
                    self.device_combo.addItem(display_text, (device_name, device_instance, base_stick_name))

                # 2. Add SEM module entry
                sem_template = self.pdf_manager.find_template("VKB SEM")

                if sem_template:
                    # Store tuple: (device_name, device_instance, "VKB SEM")
                    display_text = "VKB SEM" + connection_status
                    self.device_combo.addItem(display_text, (device_name, device_instance, "VKB SEM"))
                else:
                    display_text = f"VKB SEM (No template){connection_status}"
                    self.device_combo.addItem(display_text, (device_name, device_instance, "VKB SEM"))
            else:
                # Regular device (no SEM) - show ALL matching templates
                matching_templates = self.find_all_matching_templates(raw_device_name)

                if matching_templates:
                    for template in matching_templates:
                        # Store tuple: (device_name, device_instance, template.name)
                        display_text = template.name + connection_status
                        self.device_combo.addItem(display_text, (device_name, device_instance, template.name))
                else:
                    friendly_device_name = get_friendly_device_name(raw_device_name)
                    display_text = f"{friendly_device_name} (No template){connection_status}"
                    self.device_combo.addItem(display_text, (device_name, device_instance, raw_device_name))

        if self.device_combo.count() == 0:
            self.status_label.setText("No connected devices found")
            self.device_combo.addItem("No devices available", None)
        else:
            # All connected devices are by definition connected
            connected_count = len(joystick_devices)
            self.status_label.setText(f"Found {connected_count} connected device(s)")

    def find_all_matching_templates(self, device_name: str) -> list:
        """
        Find all templates that match a device name

        Args:
            device_name: Device product name

        Returns:
            List of matching PDFDeviceTemplate objects
        """
        if not device_name:
            return []

        matching_templates = []
        device_name_lower = device_name.lower().strip()

        # Get all templates from the registry
        for template in self.pdf_manager.templates:
            # Check each device match pattern
            for pattern in template.device_match_patterns:
                pattern_lower = pattern.lower().strip()
                if pattern_lower in device_name_lower or device_name_lower in pattern_lower:
                    matching_templates.append(template)
                    break  # Don't add the same template multiple times

        return matching_templates

    def find_template_by_name(self, template_name: str):
        """
        Find a template by its display name

        Args:
            template_name: Template display name (e.g., "VKB Gladiator SCG OTA (Left)")

        Returns:
            PDFDeviceTemplate object or None
        """
        if not template_name:
            return None

        for template in self.pdf_manager.templates:
            if template.name == template_name:
                return template

        return None

    def select_device_by_name(self, device_name: str) -> bool:
        """Select a device in the combo box by its name"""
        if not device_name:
            return False

        for i in range(self.device_combo.count()):
            item_data = self.device_combo.itemData(i)

            if item_data and hasattr(item_data, 'product_name'):
                if item_data.product_name == device_name:
                    self.device_combo.setCurrentIndex(i)
                    return True

        return False

    def on_device_changed(self, index: int):
        """Handle device selection change"""
        if index < 0:
            return

        item_data = self.device_combo.itemData(index)
        if not item_data:
            self.scene.clear()
            self.status_label.setText("No device selected")
            self.export_available_changed.emit(False)
            return

        # Handle tuple format (device_name, device_instance, template_name)
        if isinstance(item_data, tuple):
            if len(item_data) == 3:
                # New format: (device_name, device_instance, template_name)
                self.current_device = item_data[0]  # device_name
                self.current_device_instance = item_data[1]  # device_instance
                self.current_template_search_name = item_data[2]  # template_name
            elif len(item_data) == 2:
                # Old format: (device, template_name) - for backwards compatibility
                self.current_device = item_data[0]
                self.current_template_search_name = item_data[1]
        else:
            self.current_device = item_data
            self.current_template_search_name = None

        self.load_device_pdf()

    def load_device_pdf(self):
        """Load and display device PDF with populated form fields"""
        if not self.current_device:
            return

        # Find PDF template for this device
        # Use the template search name if set (for split devices or user selection)
        if self.current_template_search_name:
            # Search name might be a template name (e.g., "VKB Gladiator SCG OTA (Left)")
            # Try to find by template name first
            template = self.find_template_by_name(self.current_template_search_name)
            if not template:
                # Fallback: try as device name pattern
                template = self.pdf_manager.find_template(self.current_template_search_name)
        else:
            # No specific template selected, use device name for matching
            # current_device is now a device name string (from connected_devices)
            template = self.pdf_manager.find_template(self.current_device)

        if not template:
            self.scene.clear()
            self.status_label.setText("No PDF template available for this device")
            self.export_available_changed.emit(False)
            return

        self.current_template = template

        # Verify PDF exists
        if not os.path.exists(template.pdf_path):
            self.scene.clear()
            self.status_label.setText(f"PDF template not found: {template.pdf_path}")
            self.export_available_changed.emit(False)
            return

        # Get field values from bindings
        field_values = self.get_field_values_for_device()
        self.current_field_values = field_values

        # Get field regions for clickable areas
        field_regions, field_value_map = self.get_field_regions(template, dpi=150)

        # Render PDF with populated fields
        try:
            pixmap = self.pdf_manager.render_template(template, field_values, dpi=150)

            if pixmap is None or pixmap.isNull():
                self.scene.clear()
                self.status_label.setText(f"Failed to render PDF: {template.pdf_path}")
                self.export_available_changed.emit(False)
                return

            # Clear scene and add pixmap
            self.scene.clear()
            pixmap_item = QGraphicsPixmapItem(pixmap)
            self.scene.addItem(pixmap_item)

            # Set clickable field regions in the view (with full labels for tooltips)
            full_labels = getattr(self, 'field_full_labels', {})
            self.view.set_field_regions(field_regions, field_value_map, full_labels)

            # Fit view to scene
            self.view.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

            self.status_label.setText(f"Loaded: {template.name} ({len(field_values)} fields populated) - Click fields to edit")
            self.export_available_changed.emit(True)

        except Exception as e:
            logger.error(f"Error rendering PDF template: {e}", exc_info=True)
            self.scene.clear()
            self.status_label.setText(f"Error rendering PDF: {str(e)}")
            self.export_available_changed.emit(False)

    def get_field_values_for_device(self) -> dict:
        """Get PDF form field values for the current device"""
        field_values = {}

        try:
            if not self.current_device or not self.current_profile or not self.device_mapper:
                logger.warning("Missing current_device, current_profile, or device_mapper")
                return field_values

            # Get joystick index for this device
            # current_device is now a device name string (from connected_devices)
            js_index = self.device_mapper.get_js_index_for_device(self.current_device or "")

            if js_index is None:
                logger.warning(f"No JS index found for device: {self.current_device}")
                return field_values

            # Extract JS number
            js_num = js_index.replace("js", "")
            logger.debug(f"Processing device with JS number: {js_num}")

            # Get all bindings for this device
            device_bindings = self.get_device_bindings()
            logger.debug(f"Found {len(device_bindings)} device bindings")

            # Group bindings by input code
            from collections import defaultdict
            grouped_bindings = defaultdict(list)

            for action_map_name, binding in device_bindings:
                input_code = binding.input_code.strip()
                logger.debug(f"Processing binding: {binding.action_name} -> {input_code}")
                if input_code and input_code.startswith(f"js{js_num}_"):
                    grouped_bindings[input_code].append((action_map_name, binding))
                    logger.debug(f"  Added to grouped_bindings for {input_code}")

            logger.debug(f"Grouped into {len(grouped_bindings)} input codes")

            # Create field values map
            for input_code, bindings in grouped_bindings.items():
                try:
                    # Get action labels
                    action_labels = []
                    for action_map_name, binding in bindings:
                        action_label = LabelGenerator.get_action_label(binding.action_name, binding)
                        action_labels.append(action_label)

                    # Remove duplicates
                    unique_labels = list(dict.fromkeys(action_labels))
                    logger.debug(f"{input_code}: {len(action_labels)} actions -> {len(unique_labels)} unique: {unique_labels}")

                    # Store full labels for tooltip display
                    if not hasattr(self, 'field_full_labels'):
                        self.field_full_labels = {}
                    self.field_full_labels[input_code] = unique_labels

                    # Truncate labels for PDF display
                    display_label = self._truncate_labels(unique_labels)
                    logger.debug(f"{input_code}: truncated to '{display_label}'")

                    # Store in field values
                    field_values[input_code] = display_label
                except Exception as e:
                    logger.error(f"Error processing input_code {input_code}: {e}", exc_info=True)
                    field_values[input_code] = ""

            logger.debug(f"Generated {len(field_values)} field values for device")
            return field_values

        except Exception as e:
            logger.error(f"Error in get_field_values_for_device: {e}", exc_info=True)
            return field_values

    def get_device_bindings(self) -> list:
        """Get all bindings for the current device"""
        if not self.current_device or not self.current_profile:
            logger.warning("Missing current_device or current_profile")
            return []

        bindings = []
        device_type = self.current_device.device_type

        # Get the correct JS index from device mapper (not the raw device instance)
        if device_type == 'joystick':
            if not self.device_mapper:
                logger.warning("No device mapper available")
                return []

            device_product_name = self.current_device.product_name or ""
            logger.debug(f"Looking for JS index for device: '{device_product_name}'")

            js_index = self.device_mapper.get_js_index_for_device(device_product_name)
            if not js_index:
                logger.warning(f"No JS index found for device: {device_product_name}")
                logger.debug(f"  Device instance: {self.current_device.instance}")
                logger.debug(f"  Available mappings: {self.device_mapper.device_to_joystick}")
                return []

            js_num = js_index.replace("js", "")
            js_prefix = f"js{js_num}_"
            logger.debug(f"Device '{device_product_name}' mapped to JS{js_num}, looking for prefix '{js_prefix}'")
        else:
            logger.debug(f"Device is not joystick, type: {device_type}")
            return []

        # Count total bindings in profile for debugging
        total_bindings = sum(len(am.actions) for am in self.current_profile.action_maps)
        logger.debug(f"Profile has {total_bindings} total bindings across {len(self.current_profile.action_maps)} action maps")

        for action_map in self.current_profile.action_maps:
            for binding in action_map.actions:
                if binding.input_code.startswith(js_prefix):
                    bindings.append((action_map.name, binding))
                    logger.debug(f"  Found binding in {action_map.name}: {binding.action_name} -> {binding.input_code}")

        logger.debug(f"Found {len(bindings)} bindings for device '{device_product_name}' (JS{js_num})")
        return bindings

    def _truncate_labels(self, labels: list, max_width: int = 30) -> str:
        """
        Truncate action labels to fit in PDF field while always showing the first action.

        Requirements:
        - Always display the first label (truncate if needed to fit (+N) suffix)
        - If there are more labels, add (+N) suffix showing count of remaining
        - If single label is too long, truncate it rather than downsizing
        - For multiple labels, show first label and any additional that fit, with (+N) for rest

        Args:
            labels: List of action label strings
            max_width: Maximum characters for the display string

        Returns:
            Formatted string with first label and optional (+N) suffix
        """
        if not labels:
            logger.debug(f"_truncate_labels: empty labels, returning ''")
            return ""

        if len(labels) == 1:
            # Single label - truncate if needed but don't downsize
            label = labels[0]
            if len(label) <= max_width:
                logger.debug(f"_truncate_labels: 1 label fits: '{label}'")
                return label
            else:
                # Truncate with ellipsis
                truncated = label[:max_width - 3] + "..."
                logger.debug(f"_truncate_labels: 1 label too long, truncated to: '{truncated}'")
                return truncated

        # Multiple labels - show first, then as many additional as fit, with count indicator
        separator = ' / '
        indicator_prefix = " (+"
        indicator_suffix = ")"

        # Start with the first label
        first_label = labels[0]
        displayed = [first_label]
        current_length = len(first_label)

        logger.debug(f"_truncate_labels: {len(labels)} labels, starting with first: '{first_label}'")

        # Try to add more labels after the first one
        for i in range(1, len(labels)):
            label = labels[i]
            # How many labels would remain after this one?
            remaining_after = len(labels) - i - 1
            # Build the indicator for remaining labels
            indicator = f"{indicator_prefix}{remaining_after + 1}{indicator_suffix}" if remaining_after > 0 else ""
            indicator_len = len(indicator)

            # Would adding this label fit with the indicator?
            test_length = current_length + len(separator) + len(label)

            logger.debug(f"_truncate_labels: trying label {i}: '{label}' (test_length={test_length}, indicator_len={indicator_len}, limit={max_width})")

            if test_length + indicator_len <= max_width:
                # It fits! Add it to display
                displayed.append(label)
                current_length = test_length
                logger.debug(f"_truncate_labels: added label {i}")
            else:
                # Doesn't fit, stop adding more
                logger.debug(f"_truncate_labels: label {i} doesn't fit, stopping")
                break

        # Build final result
        result = separator.join(displayed)
        remaining = len(labels) - len(displayed)

        if remaining > 0:
            # Add indicator for remaining labels
            result += f"{indicator_prefix}{remaining}{indicator_suffix}"
            logger.debug(f"_truncate_labels: final result: '{result}' ({remaining} more)")
        else:
            logger.debug(f"_truncate_labels: final result: '{result}' (all shown)")

        return result

    def get_field_regions(self, template: PDFDeviceTemplate, dpi: int = 150):
        """Get field regions from PDF for click detection"""
        import fitz

        field_regions = {}
        field_values = {}

        try:
            doc = fitz.open(template.pdf_path)
            page = doc[0]

            # Get field mapping if exists
            field_mapping = self.pdf_manager.load_field_mapping(template)

            # DPI scale factor
            zoom = dpi / 72.0

            for widget in page.widgets():
                field_name = widget.field_name
                rect = widget.rect

                # Scale rect to match rendered image
                scaled_rect = QRectF(
                    rect.x0 * zoom,
                    rect.y0 * zoom,
                    (rect.x1 - rect.x0) * zoom,
                    (rect.y1 - rect.y0) * zoom
                )

                # Map PDF field name to input code
                input_code = self.map_pdf_field_to_input_code(field_name, field_mapping)

                if input_code:
                    field_regions[input_code] = scaled_rect
                    # Store current value for this field
                    current_value = self.current_field_values.get(input_code, "")
                    field_values[input_code] = current_value
                    # Store reverse mapping
                    self.field_to_input_code[field_name] = input_code

            doc.close()

        except Exception as e:
            logger.error(f"Error getting field regions: {e}", exc_info=True)

        return field_regions, field_values

    def map_pdf_field_to_input_code(self, pdf_field_name: str, field_mapping: dict) -> str:
        """Map PDF field name to Star Citizen input code"""
        if not self.device_mapper:
            return None

        # Get JS index for this device
        # current_device is now a device name string (from connected_devices)
        js_index = self.device_mapper.get_js_index_for_device(self.current_device or "")
        if not js_index:
            return None

        js_num = js_index.replace("js", "")

        if field_mapping:
            # Has custom mapping - check all three mapping types
            button_mapping = field_mapping.get('button_mapping', {})
            hat_mapping = field_mapping.get('hat_mapping', {})
            axis_mapping = field_mapping.get('axis_mapping', {})

            # Try to find in each mapping type (with and without _1/_2 suffix)
            for mapping, mapping_type in [(button_mapping, 'button'), (hat_mapping, 'hat'), (axis_mapping, 'axis')]:
                # Try exact match first
                mapped_value = mapping.get(pdf_field_name)

                if mapped_value is None and (pdf_field_name.endswith('_1') or pdf_field_name.endswith('_2')):
                    # Try without _1/_2 suffix for backward compatibility
                    base_field_name = pdf_field_name[:-2]
                    mapped_value = mapping.get(base_field_name)

                if mapped_value is not None:
                    # Handle both integer and string identifiers
                    if isinstance(mapped_value, int):
                        # Integer: button number (e.g., 1 -> button1)
                        return f"js{js_num}_button{mapped_value}"
                    elif isinstance(mapped_value, str):
                        # String: direct identifier (e.g., "hat1_up" -> hat1_up)
                        return f"js{js_num}_{mapped_value}"

            # If not found in any mapping, return None
            return None
        else:
            # Direct mapping - PDF field should be input code
            return pdf_field_name

        return None

    def on_field_clicked(self, input_code: str, current_value: str):
        """Handle click on a PDF form field"""
        # Show remapping dialog with multi-action support
        # Hide "Change Input Binding" section since input is already determined by the button clicked
        try:
            from gui.remap_dialog import RemapDialog

            # Use non-modal dialog to avoid Windows keyboard listener suppression
            dialog = RemapDialog(input_code, self.current_profile, self, show_input_binding=False)
            dialog.bindings_changed.connect(self.on_bindings_changed)
            dialog.setWindowModality(Qt.WindowModality.NonModal)
            dialog.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
            dialog.show()
        except Exception as e:
            logger.error(f"Error showing remap dialog: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to open remapping dialog:\n{str(e)}"
            )

    def on_bindings_changed(self, bindings: list):
        """Handle changes to multiple bindings from the remapping dialog"""
        if not bindings:
            return

        # Mark profile as modified
        if self.current_profile:
            # Check if any bindings are not in the profile and add them
            for binding in bindings:
                binding_found = False
                for action_map in self.current_profile.action_maps:
                    for existing_binding in action_map.actions:
                        if existing_binding is binding:
                            binding_found = True
                            break
                    if binding_found:
                        break

                # If binding is not in profile, add it to the appropriate action map
                if not binding_found:
                    logger.info(f"on_bindings_changed: Binding {binding.action_name} not in profile, finding correct actionmap...")
                    # Find the correct action map for this action
                    added = False
                    for action_map in self.current_profile.action_maps:
                        for existing_binding in action_map.actions:
                            if existing_binding.action_name == binding.action_name:
                                # Add the new binding to this action map
                                action_map.actions.append(binding)
                                logger.info(f"on_bindings_changed: Added binding {binding.action_name} to {action_map.name}")
                                added = True
                                break
                        if added:
                            break

                    if not added:
                        logger.warning(f"on_bindings_changed: Could not find actionmap for action {binding.action_name}")

            self.current_profile.mark_modified()

        # Reload override manager cache
        from utils.label_overrides import get_override_manager
        override_manager = get_override_manager()
        override_manager.reload()

        # Reload the PDF with updated values
        self.load_device_pdf()

        # Notify parent to update table and window title
        self.notify_profile_changed()

        logger.info(f"Updated {len(bindings)} binding(s)")

    def find_binding_by_input_code(self, input_code: str):
        """Find binding object by input code"""
        if not self.current_profile:
            return None

        for action_map in self.current_profile.action_maps:
            for binding in action_map.actions:
                if binding.input_code == input_code:
                    return binding

        return None

    def update_binding_label(self, binding, new_label: str):
        """Update a binding's custom label"""
        try:
            from utils.label_overrides import get_override_manager

            override_manager = get_override_manager()

            # Get default label
            default_label = LabelGenerator.generate_action_label(binding.action_name)

            if new_label == default_label:
                # Remove custom override
                override_manager.remove_custom_override(binding.action_name)
                binding.custom_label = None
            else:
                # Save custom override
                override_manager.set_custom_override(binding.action_name, new_label)
                binding.custom_label = new_label

        except Exception as e:
            logger.error(f"Error updating binding label: {e}", exc_info=True)

    def notify_profile_changed(self):
        """Notify parent window that the profile has changed"""
        try:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'on_profile_modified'):
                    parent.on_profile_modified()
                    logger.info("Notified main window of profile changes")
                    break
                parent = parent.parent()
        except Exception as e:
            logger.warning(f"Could not notify main window: {e}")

    def export_graphic(self):
        """Export the rendered PDF graphic"""
        if not self.current_template:
            QMessageBox.warning(self, "No Template", "No device template is currently loaded.")
            return

        from PyQt6.QtWidgets import QFileDialog

        # Create default filename
        device_name = (self.current_device.product_name or 'device').replace(' ', '_')
        default_filename = f"{device_name}_controls.png"

        # Determine default directory with preference order:
        # 1. Star Citizen profiles directory (if configured and exists)
        # 2. Current directory
        default_dir = ""
        settings = AppSettings()
        sc_profiles_dir = settings.get_sc_profiles_directory()
        if sc_profiles_dir and os.path.exists(sc_profiles_dir):
            default_dir = sc_profiles_dir

        default_path = os.path.join(default_dir, default_filename) if default_dir else default_filename

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Device Graphic",
            default_path,
            "PNG Image (*.png);;PDF Document (*.pdf)"
        )

        if not file_path:
            return

        try:
            if file_path.lower().endswith('.pdf'):
                self.export_to_pdf(file_path)
            else:
                self.export_to_png(file_path)

            QMessageBox.information(
                self,
                "Success",
                f"Graphic exported successfully!\n\nSaved to:\n{file_path}"
            )
            self.status_label.setText(f"Exported to: {os.path.basename(file_path)}")

        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export graphic:\n{str(e)}")
            self.status_label.setText("Export failed")

    def export_to_png(self, file_path: str):
        """Export scene to PNG"""
        from PyQt6.QtGui import QImage

        # Get scene bounding rect
        rect = self.scene.sceneRect()

        # Create image
        image = QImage(int(rect.width()), int(rect.height()), QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)

        # Render scene to image
        painter = QPainter(image)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.scene.render(painter)
        painter.end()

        # Save image
        image.save(file_path, "PNG")

    def export_to_pdf(self, file_path: str):
        """Export as PDF with populated fields"""
        import tempfile
        import shutil

        # Create populated PDF
        temp_dir = os.path.dirname(self.current_template.pdf_path)
        fd, temp_pdf_path = tempfile.mkstemp(suffix='.pdf', dir=temp_dir, prefix='export_')
        os.close(fd)

        populated_pdf_path = self.pdf_manager.populate_pdf(
            self.current_template,
            self.current_field_values,
            temp_pdf_path
        )

        if populated_pdf_path:
            # Copy to final location
            shutil.copy2(populated_pdf_path, file_path)
            # Clean up temp file
            try:
                os.remove(populated_pdf_path)
            except:
                pass
        else:
            raise Exception("Failed to populate PDF")
