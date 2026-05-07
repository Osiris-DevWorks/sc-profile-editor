"""
Remapping dialog for editing button assignments with multi-action support
"""

import sys
import os
import logging
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                              QLineEdit, QComboBox, QGroupBox, QMessageBox,
                              QFormLayout, QDialogButtonBox, QScrollArea, QWidget)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from models.profile_model import ActionBinding, ControlProfile
from parser.label_generator import LabelGenerator
from utils.input_validator import InputValidator
from utils.input_detector import InputDetector
from utils.settings import AppSettings

logger = logging.getLogger(__name__)


class SearchableComboBox(QComboBox):
    """ComboBox that makes the dropdown searchable with standard filtering behavior"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # Store all items and their data for search/filtering
        self.all_items = []  # List of (text, userData) tuples
        self.items_data = {}  # Map from text to userData
        logger.debug("SearchableComboBox initialized")

    def addItem(self, text, userData=None):
        """Add item with optional user data"""
        try:
            logger.debug(f"addItem called: text='{text}', userData={userData}")
            super().addItem(text, userData)
            self.all_items.append((text, userData))
            self.items_data[text] = userData
            logger.debug(f"Item added successfully. Total items: {len(self.all_items)}")
        except Exception as e:
            logger.error(f"Error in addItem: {e}", exc_info=True)
            raise

    def addItems(self, items):
        """Add multiple items (list of strings)"""
        logger.debug(f"addItems called with {len(items)} items")
        for text in items:
            self.addItem(text)

    def currentData(self, role=Qt.ItemDataRole.UserRole):
        """Get data for current item"""
        try:
            current_text = self.currentText()
            logger.debug(f"currentData called: currentText='{current_text}'")

            # Try exact match from our mapping
            if current_text in self.items_data:
                data = self.items_data[current_text]
                logger.debug(f"Returning data from items_data: {data}")
                return data

            # Fall back to standard implementation
            data = super().currentData(role)
            logger.debug(f"Returning data from super(): {data}")
            return data
        except Exception as e:
            logger.error(f"Error in currentData: {e}", exc_info=True)
            raise

    def itemData(self, index):
        """Override itemData to handle items"""
        try:
            logger.debug(f"itemData called: index={index}, count={super().count()}")
            if index < 0 or index >= super().count():
                logger.debug(f"Index {index} out of bounds")
                return None
            text = super().itemText(index)
            logger.debug(f"itemText at index {index}: '{text}'")
            data = self.items_data.get(text, None)
            logger.debug(f"itemData returning: {data}")
            return data
        except Exception as e:
            logger.error(f"Error in itemData: {e}", exc_info=True)
            raise

    def clear(self):
        """Clear all items"""
        try:
            logger.debug(f"clear called. Current items: {len(self.all_items)}")
            super().clear()
            self.all_items.clear()
            self.items_data.clear()
            logger.debug("clear completed successfully")
        except Exception as e:
            logger.error(f"Error in clear: {e}", exc_info=True)
            raise


class ActionAssignmentWidget(QWidget):
    """Widget for displaying and editing a single action assignment"""

    # Signals
    delete_requested = pyqtSignal(object)  # Emits the binding

    def __init__(self, binding: ActionBinding, label_generator, parent=None):
        super().__init__(parent)
        self.binding = binding
        self.label_generator = label_generator
        self.setup_ui()

    def setup_ui(self):
        """Set up the UI for this action assignment"""
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        self.setLayout(layout)

        # Action name and label display
        action_label = self.label_generator.get_action_label(
            self.binding.action_name,
            self.binding
        )

        # Header with action info
        header_layout = QHBoxLayout()

        action_info_label = QLabel(f"<b>{action_label}</b>")
        action_info_label.setStyleSheet("font-size: 10px;")
        header_layout.addWidget(action_info_label)

        action_name_label = QLabel(f"<span style='color: #666; font-size: 9px;'>({self.binding.action_name})</span>")
        header_layout.addWidget(action_name_label)

        header_layout.addStretch()

        # Delete button
        delete_btn = QPushButton("Delete")
        delete_btn.setMaximumWidth(80)
        delete_btn.setStyleSheet("font-size: 9px; padding: 3px 6px;")
        delete_btn.clicked.connect(self.on_delete_clicked)
        header_layout.addWidget(delete_btn)

        layout.addLayout(header_layout)

        # Custom label editor and activation mode
        label_layout = QFormLayout()

        self.label_edit = QLineEdit()
        custom_label = getattr(self.binding, 'custom_label', None) or ""
        self.label_edit.setText(custom_label)
        self.label_edit.setPlaceholderText(f"Default: {action_label}")
        label_layout.addRow("Custom Label:", self.label_edit)

        # Activation mode dropdown
        self.activation_mode_combo = QComboBox()
        self.activation_mode_combo.addItem("press", "press")
        self.activation_mode_combo.addItem("double_tap", "double_tap")

        # Check if this is an analog axis - they don't support activation modes
        is_analog = InputValidator.is_analog_axis(self.binding.input_code)

        if is_analog:
            # Disable activation mode for analog axes
            self.activation_mode_combo.setEnabled(False)
            self.activation_mode_combo.addItem("(Analog axis - uses continuous input)", None)
            self.activation_mode_combo.setCurrentIndex(2)
        else:
            # Set current activation mode (default to "press" if not set)
            current_activation = self.binding.activation_mode or "press"
            index = self.activation_mode_combo.findData(current_activation)
            if index >= 0:
                self.activation_mode_combo.setCurrentIndex(index)
            else:
                self.activation_mode_combo.setCurrentIndex(0)  # Default to "press"

        label_layout.addRow("Activation Mode:", self.activation_mode_combo)

        layout.addLayout(label_layout)

        # Border styling — palette-driven so the panel reads correctly on
        # every theme background.
        self.setStyleSheet("""
            ActionAssignmentWidget {
                border: 1px solid palette(mid);
                border-radius: 4px;
                background-color: palette(alternate-base);
                margin: 4px 0px;
            }
        """)

    def on_delete_clicked(self):
        """Handle delete button click"""
        reply = QMessageBox.question(
            self,
            "Delete Assignment",
            f"Are you sure you want to delete the assignment for:\n{self.binding.action_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            self.delete_requested.emit(self.binding)

    def get_custom_label(self) -> str:
        """Get the custom label from the text field"""
        return self.label_edit.text().strip()

    def get_activation_mode(self) -> str:
        """Get the selected activation mode (or 'press' as default)"""
        return self.activation_mode_combo.currentData() or "press"


class RemapDialog(QDialog):
    """Dialog for editing button assignments with support for multiple actions"""

    # Signal emitted when bindings are changed
    bindings_changed = pyqtSignal(list)  # List of modified bindings

    def __init__(self, input_code: str, profile: ControlProfile, parent=None, single_action_mode: bool = False, binding: 'ActionBinding' = None, show_input_binding: bool = True):
        logger.info(f"RemapDialog.__init__ called with input_code={input_code}, single_action_mode={single_action_mode}, binding={binding is not None}, show_input_binding={show_input_binding}")
        try:
            super().__init__(parent)
            self.input_code = input_code
            self.profile = profile
            self.single_action_mode = single_action_mode  # Hide "Add New Action" section when editing from table
            self.show_input_binding = show_input_binding  # Hide "Change Input Binding" section when editing from device view

            # If a specific binding is provided (e.g., from table edit), use it directly
            # Otherwise, search for bindings by input code
            if binding is not None:
                logger.debug(f"Using provided binding for action: {binding.action_name}")
                self.bindings_for_input = [binding]
            else:
                logger.debug(f"Finding bindings for input_code: {input_code}")
                self.bindings_for_input = self.find_bindings_by_input_code(input_code)
            self.deleted_bindings = []  # Track bindings to be deleted

            # Store all actions grouped by action map
            self.actions_by_map = {}
            self.action_map_friendly_names = {}
            logger.debug("Building action maps")
            self._build_action_maps()
            logger.debug(f"Built {len(self.actions_by_map)} action maps")

            # Input detection setup
            logger.debug("Setting up input detector")
            self.input_detector = InputDetector()
            self.detecting_input = False

            # Load device mapping from settings (for remapping detected input)
            settings = AppSettings()
            self.device_mapping = settings.get_device_config()
            logger.debug(f"Loaded device mapping: {self.device_mapping}")

            # Store action assignment widgets for easy access
            self.action_widgets = []

            self.setWindowTitle("Edit Button Assignment")
            self.setMinimumWidth(700)
            self.setMinimumHeight(500)

            logger.debug("Setting up UI")
            self.setup_ui()
            logger.debug("Populating from bindings")
            self.populate_from_bindings()
            logger.info("RemapDialog initialization complete")
        except Exception as e:
            logger.error(f"Error in RemapDialog.__init__: {e}", exc_info=True)
            raise

    def _build_action_maps(self):
        """Build action map structure for dropdowns"""
        for action_map in self.profile.action_maps:
            # Convert internal name to friendly name
            friendly_name = self._get_friendly_map_name(action_map.name)
            self.action_map_friendly_names[action_map.name] = friendly_name

            # Store actions by map
            self.actions_by_map[action_map.name] = action_map.actions

    def _get_friendly_map_name(self, map_name: str) -> str:
        """Convert internal action map name to friendly display name"""
        words = map_name.replace('_', ' ').split()
        return ' '.join(word.capitalize() for word in words)

    def find_bindings_by_input_code(self, input_code: str) -> list:
        """Find all bindings for an input code (excluding unmapped/unbound actions)"""
        bindings = []
        # Don't search for unmapped input codes (those ending with underscore)
        if input_code.rstrip().endswith('_'):
            return bindings

        for action_map in self.profile.action_maps:
            for binding in action_map.actions:
                if binding.input_code == input_code:
                    bindings.append(binding)
        return bindings

    def _get_current_input_display(self) -> str:
        """Get display text for current input binding"""
        # Check if input code is unmapped (ends with underscore)
        if self.input_code.rstrip().endswith('_'):
            return "none"
        else:
            return InputValidator.get_input_description(self.input_code)

    def setup_ui(self):
        """Set up the user interface"""
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Header - show action being edited
        # Get the first binding's action name if available
        action_name = ""
        if self.bindings_for_input:
            action_name = self.bindings_for_input[0].action_name

        if action_name:
            header_text = f"<b>Editing Action:</b> {action_name}"
        else:
            header_text = "<b>Editing Action:</b> (unmapped)"

        header_label = QLabel(header_text)
        header_font = QFont()
        header_font.setPointSize(11)
        header_label.setFont(header_font)
        layout.addWidget(header_label)

        # === CURRENT ACTIONS SECTION ===
        current_group = QGroupBox("Current Actions for This Button")
        current_layout = QVBoxLayout()
        current_group.setLayout(current_layout)

        # Scrollable area for action widgets
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")

        self.actions_container = QWidget()
        self.actions_container_layout = QVBoxLayout()
        self.actions_container_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_container.setLayout(self.actions_container_layout)

        scroll_area.setWidget(self.actions_container)
        current_layout.addWidget(scroll_area)

        # "No actions" placeholder
        self.no_actions_label = QLabel("No actions assigned to this button yet.")
        # Use a stylesheet that respects the system theme - works in both light and dark mode
        self.no_actions_label.setStyleSheet("QLabel { color: palette(text); font-style: italic; padding: 10px; opacity: 0.6; }")
        self.actions_container_layout.addWidget(self.no_actions_label)

        layout.addWidget(current_group, 1)  # Stretch this section

        layout.addSpacing(10)

        # === CHANGE INPUT SECTION ===
        change_input_group = QGroupBox("Change Input Binding")
        change_input_layout = QVBoxLayout()
        change_input_group.setLayout(change_input_layout)

        # Show current input
        current_input_text = self._get_current_input_display()
        desc_label = QLabel(f"<b>Current:</b> {current_input_text}")
        # Use a stylesheet that respects the system theme - works in both light and dark mode
        desc_label.setStyleSheet("QLabel { color: palette(text); font-size: 10px; }")
        self.desc_label = desc_label
        change_input_layout.addWidget(desc_label)

        # Input selection layout with dropdown and detect button
        input_selection_layout = QHBoxLayout()

        # Or label (select manually section first)
        or_label = QLabel("or select manually:")
        input_selection_layout.addWidget(or_label)

        # Input code dropdown
        self.input_code_combo = SearchableComboBox()
        self.input_code_combo.addItem("-- Select Input Code --", None)
        self._populate_input_codes()
        self.input_code_combo.currentIndexChanged.connect(self.on_input_code_selected)
        input_selection_layout.addWidget(self.input_code_combo, 1)  # Make dropdown stretch

        # Detect input button (right side)
        self.detect_input_btn = QPushButton("Detect Input")
        self.detect_input_btn.setMaximumWidth(120)
        self.detect_input_btn.clicked.connect(self.on_detect_input_clicked)
        input_selection_layout.addWidget(self.detect_input_btn)

        change_input_layout.addLayout(input_selection_layout)

        layout.addWidget(change_input_group)

        # Hide "Change Input Binding" section when editing from device view
        if not self.show_input_binding:
            change_input_group.hide()

        # === ADD NEW ACTION SECTION ===
        add_group = QGroupBox("Add New Action")
        add_layout = QVBoxLayout()
        add_group.setLayout(add_layout)

        # Action map category selection
        category_layout = QFormLayout()

        self.action_map_combo = SearchableComboBox()
        self.action_map_combo.addItem("-- Select Action Category --", None)
        self.action_map_combo.addItem("ALL", "ALL")

        for map_name in sorted(self.actions_by_map.keys()):
            friendly_name = self.action_map_friendly_names[map_name]
            self.action_map_combo.addItem(friendly_name, map_name)

        self.action_map_combo.currentIndexChanged.connect(self.on_action_map_changed)
        category_layout.addRow("Action Category:", self.action_map_combo)

        # Action selection (filtered by category)
        self.action_combo = SearchableComboBox()
        self.action_combo.addItem("-- Select Action --", None)
        self.action_combo.setEnabled(False)
        category_layout.addRow("Action:", self.action_combo)

        add_layout.addLayout(category_layout)

        # Show action description when selected
        self.action_desc_label = QLabel("")
        # Use a stylesheet that respects the system theme - works in both light and dark mode
        self.action_desc_label.setStyleSheet("QLabel { color: palette(text); font-size: 10px; font-style: italic; }")
        self.action_desc_label.setWordWrap(True)
        add_layout.addWidget(self.action_desc_label)
        self.action_combo.currentIndexChanged.connect(self.on_action_selected)

        # Add button
        add_btn_layout = QHBoxLayout()
        add_btn_layout.addStretch()
        self.add_action_btn = QPushButton("Add Action")
        self.add_action_btn.setMaximumWidth(120)
        self.add_action_btn.clicked.connect(self.on_add_action_clicked)
        self.add_action_btn.setEnabled(False)
        add_btn_layout.addWidget(self.add_action_btn)
        add_layout.addLayout(add_btn_layout)

        # Hide "Add New Action" section when editing from table (single action mode)
        if self.single_action_mode:
            add_group.hide()

        layout.addWidget(add_group)

        # Info message
        info_label = QLabel("You can add multiple actions to the same button, or delete existing ones.")
        info_label.setStyleSheet("color: #888; font-size: 10px; font-style: italic;")
        info_label.setWordWrap(True)

        # Hide info message when in single action mode
        if self.single_action_mode:
            info_label.hide()

        layout.addWidget(info_label)

        # Dialog buttons with Clear All button
        button_layout = QHBoxLayout()

        clear_all_btn = QPushButton("Clear All")
        # Use the palette's BrightText role for the destructive action — it's
        # red in light/dark, orange in default (navy), and copper in ODW.
        clear_all_btn.setStyleSheet("color: palette(bright-text);")
        clear_all_btn.clicked.connect(self.clear_all_bindings)
        clear_all_btn.setToolTip("Remove all mappings for this button")
        button_layout.addWidget(clear_all_btn)

        button_layout.addStretch()

        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept_changes)
        button_box.rejected.connect(self.reject)
        button_layout.addWidget(button_box)

        layout.addLayout(button_layout)

    def populate_from_bindings(self):
        """Populate dialog from all bindings for this input code"""
        if self.bindings_for_input:
            # Hide "no actions" label
            self.no_actions_label.hide()

            # Create widget for each action
            for binding in self.bindings_for_input:
                self.add_action_widget(binding)
        else:
            # Show "no actions" label
            self.no_actions_label.show()

    def add_action_widget(self, binding: ActionBinding):
        """Add an action assignment widget to the display"""
        widget = ActionAssignmentWidget(binding, LabelGenerator, self)
        widget.delete_requested.connect(self.on_action_delete_requested)
        self.action_widgets.append(widget)

        # Insert before the stretch
        self.actions_container_layout.insertWidget(
            self.actions_container_layout.count() - 1,
            widget
        )

    def on_action_delete_requested(self, binding: ActionBinding):
        """Handle request to delete an action"""
        self.deleted_bindings.append(binding)

        # Remove widget from display
        for i, widget in enumerate(self.action_widgets):
            if widget.binding == binding:
                self.actions_container_layout.removeWidget(widget)
                widget.deleteLater()
                self.action_widgets.pop(i)
                break

        # Remove from current bindings list
        if binding in self.bindings_for_input:
            self.bindings_for_input.remove(binding)

        # Show "no actions" label if empty
        if not self.action_widgets:
            self.no_actions_label.show()

    def clear_all_bindings(self):
        """Clear all bindings for this button"""
        if not self.action_widgets:
            QMessageBox.information(self, "No Mappings", "No mappings to clear for this button.")
            return

        # Confirm action
        reply = QMessageBox.warning(
            self,
            "Clear All Mappings",
            f"Remove all {len(self.action_widgets)} mapping(s) from this button?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete all action widgets
        for binding in list(self.bindings_for_input):
            self.deleted_bindings.append(binding)

        # Clear all widgets
        for widget in self.action_widgets:
            self.actions_container_layout.removeWidget(widget)
            widget.deleteLater()

        self.action_widgets.clear()
        self.bindings_for_input.clear()

        # Show "no actions" label
        self.no_actions_label.show()

        logger.info(f"Cleared all {len(self.deleted_bindings)} mapping(s) for {self.input_code}")

    def on_action_map_changed(self, index: int):
        """Handle action map category selection"""
        self.action_combo.clear()
        self.action_combo.addItem("-- Select Action --", None)
        self.action_desc_label.setText("")
        self.add_action_btn.setEnabled(False)

        map_name = self.action_map_combo.itemData(index)

        if map_name == "ALL":
            all_actions = []
            seen_action_names = set()  # Track which actions we've already added

            for actions in self.actions_by_map.values():
                all_actions.extend(actions)

            # Sort and deduplicate by action name
            for action_binding in sorted(all_actions, key=lambda b: LabelGenerator.get_action_label(b.action_name, b)):
                # Skip if we've already added this action name
                if action_binding.action_name in seen_action_names:
                    continue

                seen_action_names.add(action_binding.action_name)
                action_label = LabelGenerator.get_action_label(action_binding.action_name, action_binding)
                display_text = f"{action_label} ({action_binding.action_name})"
                self.action_combo.addItem(display_text, action_binding)

            self.action_combo.setEnabled(True)

        elif map_name:
            actions = self.actions_by_map.get(map_name, [])
            seen_action_names = set()  # Track which actions we've already added

            for action_binding in sorted(actions, key=lambda b: LabelGenerator.get_action_label(b.action_name, b)):
                # Skip if we've already added this action name
                if action_binding.action_name in seen_action_names:
                    continue

                seen_action_names.add(action_binding.action_name)
                action_label = LabelGenerator.get_action_label(action_binding.action_name, action_binding)
                display_text = f"{action_label} ({action_binding.action_name})"
                self.action_combo.addItem(display_text, action_binding)

            self.action_combo.setEnabled(True)
        else:
            self.action_combo.setEnabled(False)

    def on_action_selected(self, index: int):
        """Handle action selection"""
        selected_binding = self.action_combo.itemData(index)

        if selected_binding:
            # Check if this action is already assigned to this button
            already_assigned = any(b.action_name == selected_binding.action_name
                                  for b in self.bindings_for_input)

            if already_assigned:
                self.action_desc_label.setText("(Already assigned to this button)")
                self.add_action_btn.setEnabled(False)
            else:
                default_label = LabelGenerator.generate_action_label(selected_binding.action_name)
                self.action_desc_label.setText(f"Default label: {default_label}")
                self.add_action_btn.setEnabled(True)
        else:
            self.action_desc_label.setText("")
            self.add_action_btn.setEnabled(False)

    def on_add_action_clicked(self):
        """Handle adding a new action to this button"""
        selected_binding = self.action_combo.currentData()

        if not selected_binding:
            return

        logger.info(f"on_add_action_clicked: action_name={selected_binding.action_name}, current_input_code={repr(selected_binding.input_code)}, new_input_code={repr(self.input_code)}")

        # Check if action is already bound elsewhere
        # Only show rebind warning if the action is bound to a different input
        # Unbound actions have input ending with underscore (e.g., "js1_ " or "js1_")
        is_bound = selected_binding.input_code and not selected_binding.input_code.rstrip().endswith('_')
        action_was_moved = False

        if is_bound and selected_binding.input_code != self.input_code:
            # Create dialog with three button options: Move, Duplicate, Cancel
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Action Already Mapped")
            msg_box.setText(f"The action '{selected_binding.action_name}' is currently bound to:")
            msg_box.setInformativeText(
                f"  {selected_binding.input_code} ({InputValidator.get_input_description(selected_binding.input_code)})\n\n"
                f"What would you like to do?"
            )

            # Add three custom buttons
            move_btn = msg_box.addButton("Move", QMessageBox.ButtonRole.AcceptRole)
            duplicate_btn = msg_box.addButton("Duplicate", QMessageBox.ButtonRole.ApplyRole)
            cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

            msg_box.exec()

            clicked_btn = msg_box.clickedButton()

            if clicked_btn == cancel_btn:
                return
            elif clicked_btn == move_btn:
                # Move: remove from old input and bind to new one
                action_was_moved = True
            elif clicked_btn == duplicate_btn:
                # Duplicate: keep the action bound to the old input and add to new one
                # Create a copy of the binding for the new input
                selected_binding = ActionBinding(
                    action_name=selected_binding.action_name,
                    input_code=self.input_code,
                    custom_label=selected_binding.custom_label
                )
                action_was_moved = False
            else:
                return

        # Bind the action to this button
        selected_binding.input_code = self.input_code
        logger.info(f"on_add_action_clicked: Updated binding input_code to {repr(self.input_code)}, binding object id={id(selected_binding)}, is it in profile? checking...")

        # Add to our current bindings list
        if selected_binding not in self.bindings_for_input:
            self.bindings_for_input.append(selected_binding)
            logger.info(f"on_add_action_clicked: Added binding to bindings_for_input")

        # Add widget to display
        self.add_action_widget(selected_binding)

        # Hide "no actions" label
        if self.action_widgets:
            self.no_actions_label.hide()

        # Reset the selector
        self.action_map_combo.setCurrentIndex(0)
        self.action_combo.setCurrentIndex(0)

    def _find_conflicting_bindings(self, input_code: str) -> list:
        """
        Find all bindings in the profile that are already mapped to the given input code
        (excluding bindings for the current action being edited)

        Args:
            input_code: The input code to check (e.g., "js1_button1")

        Returns:
            List of (action_name, input_code) tuples for conflicting bindings
        """
        if not self.profile or not input_code:
            logger.debug(f"_find_conflicting_bindings: profile={bool(self.profile)}, input_code={repr(input_code)}")
            return []

        try:
            conflicting = []
            current_action_names = {binding.action_name for binding in self.bindings_for_input}

            logger.debug(f"_find_conflicting_bindings: Looking for conflicts with input_code={repr(input_code)}")
            logger.debug(f"_find_conflicting_bindings: Current action names: {current_action_names}")

            # Check all bindings in the profile
            for action_map in self.profile.action_maps:
                for binding in action_map.actions:
                    # Skip if this binding is for one of the actions we're currently editing
                    if binding.action_name in current_action_names:
                        continue

                    # Check if this binding uses the same input code
                    if binding.input_code:
                        binding_code_stripped = binding.input_code.rstrip()
                        input_code_stripped = input_code.rstrip()
                        logger.debug(f"  Checking: {binding.action_name} has {repr(binding_code_stripped)} vs {repr(input_code_stripped)}")

                        if binding_code_stripped == input_code_stripped:
                            logger.info(f"Found conflict: {binding.action_name} is mapped to {repr(binding.input_code)}")
                            conflicting.append((binding.action_name, binding.input_code))

            logger.debug(f"_find_conflicting_bindings: Found {len(conflicting)} conflicts")
            return conflicting
        except Exception as e:
            logger.error(f"Error finding conflicting bindings: {e}", exc_info=True)
            return []

    def accept_changes(self):
        """Accept and apply all changes"""
        logger.debug(f"accept_changes: single_action_mode={self.single_action_mode}, input_code={repr(self.input_code)}")

        # For single_action_mode (editing from Controls Table), check for button conflicts
        # Only check for conflicts if we're actually setting a new binding (not clearing)
        if self.single_action_mode and self.input_code and self.input_code.strip() and not self.input_code.rstrip().endswith('_'):
            logger.debug(f"accept_changes: Checking for conflicting bindings")
            conflicting = self._find_conflicting_bindings(self.input_code)
            logger.debug(f"accept_changes: Found {len(conflicting)} conflicting bindings")

            if conflicting:
                # Show enhanced dialog with multiple options
                conflict_list = "\n".join([f"  • {action_name}" for action_name, _ in conflicting])

                logger.info(f"Showing 'Button Already Mapped' dialog for {len(conflicting)} conflicts")
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Button Already Mapped")
                msg_box.setText(f"The button '{InputValidator.get_input_description(self.input_code)}' is already mapped to:")
                msg_box.setInformativeText(
                    f"{conflict_list}\n\n"
                    f"What would you like to do?"
                )

                # Add three buttons with different roles
                replace_btn = msg_box.addButton("Replace All", QMessageBox.ButtonRole.AcceptRole)
                duplicate_btn = msg_box.addButton("Duplicate", QMessageBox.ButtonRole.ApplyRole)
                cancel_btn = msg_box.addButton("Cancel", QMessageBox.ButtonRole.RejectRole)

                msg_box.exec()

                clicked_button = msg_box.clickedButton()

                if clicked_button == cancel_btn:
                    logger.info("User cancelled binding change")
                    return
                elif clicked_button == replace_btn:
                    logger.info(f"User chose 'Replace All' - removing binding from {len(conflicting)} conflicting actions")
                    # Remove the input binding from all conflicting actions
                    for action_name, _ in conflicting:
                        for action_map in self.profile.action_maps:
                            for binding in action_map.actions:
                                if binding.action_name == action_name and binding.input_code == self.input_code:
                                    logger.debug(f"Removing binding from {action_name}")
                                    binding.input_code = ""
                elif clicked_button == duplicate_btn:
                    logger.info("User chose 'Duplicate' - allowing multiple actions to use this button")
                    # Just continue - this allows the binding to be added without removing others

        # Collect all modified bindings (with custom labels and updated input code)
        modified_bindings = []

        # Update custom labels, activation mode, and input code for all current bindings
        for i, widget in enumerate(self.action_widgets):
            custom_label = widget.get_custom_label()
            activation_mode = widget.get_activation_mode()
            binding = widget.binding

            logger.info(f"accept_changes: Processing binding {binding.action_name}, current input_code={repr(binding.input_code)}")

            # Set custom label
            default_label = LabelGenerator.generate_action_label(binding.action_name)
            if custom_label:
                binding.custom_label = custom_label
            else:
                binding.custom_label = None

            # Set activation mode
            # Analog axes should NOT have activationMode (they use continuous input)
            # Only buttons, keys, and hat switches should have activationMode
            if InputValidator.is_analog_axis(binding.input_code):
                binding.activation_mode = None
                logger.debug(f"Analog axis detected: {binding.input_code}, setting activation_mode to None")
            else:
                binding.activation_mode = activation_mode if activation_mode else "press"

            # Update input code if it has changed
            # For single_action_mode (editing from table), apply the current input code to the binding
            if self.single_action_mode and binding in self.bindings_for_input:
                old_code = binding.input_code
                binding.input_code = self.input_code
                logger.info(f"Updated binding {binding.action_name}: {old_code} → {self.input_code}")
            elif self.single_action_mode:
                logger.warning(f"Binding not in bindings_for_input! {binding.action_name}, action_name={binding.action_name}, input_code={binding.input_code}, bindings_for_input={[(b.action_name, b.input_code) for b in self.bindings_for_input]}")

            logger.info(f"accept_changes: Final binding {binding.action_name}, input_code={repr(binding.input_code)}")
            modified_bindings.append(binding)

        # Clear input code for deleted bindings
        for binding in self.deleted_bindings:
            binding.input_code = ""
            modified_bindings.append(binding)

        # Emit signal with all modified bindings
        self.bindings_changed.emit(modified_bindings)

        # Accept dialog
        self.accept()

    def on_detect_input_clicked(self):
        """Handle Detect Input button click"""
        if self.detecting_input:
            # Stop detection
            self.input_detector.stop_detection()
            self.detecting_input = False
            self.detect_input_btn.setText("Detect Input")
            self.detect_input_btn.setEnabled(True)
            self._disable_controls(False)
            logger.info("Input detection cancelled")
        else:
            # Start detection
            self.detecting_input = True
            self.detect_input_btn.setText("Listening... (Cancel)")
            self._disable_controls(True)
            logger.info("Starting input detection")

            # Start input detection
            detector_thread = self.input_detector.start_detection(timeout_ms=10000)
            detector_thread.input_detected.connect(self.on_input_detected)
            detector_thread.detection_cancelled.connect(self.on_input_detection_timeout)

    def _apply_device_mapping(self, input_code: str) -> str:
        """Apply device mapping to remap joystick indices if configured"""
        if not self.device_mapping or not input_code.startswith('js'):
            return input_code

        # Extract joystick instance from input code (e.g., "js1_button1" -> 1)
        import re
        match = re.match(r'js(\d+)_', input_code)
        if not match:
            return input_code

        detected_instance = int(match.group(1))
        rest_of_code = input_code[len(f"js{detected_instance}_"):]  # e.g., "button1"

        # Get the list of connected devices
        connected_devices = InputDetector.get_available_devices()

        # Find which physical device was detected at the detected_instance
        detected_device_name = None
        for device in connected_devices:
            if device.get('type') == 'joystick' and device.get('instance') == detected_instance:
                detected_device_name = device.get('name', '')
                logger.debug(f"Detected device at js{detected_instance}: {detected_device_name}")
                break

        if not detected_device_name:
            logger.debug(f"No device found at js{detected_instance}, no mapping applied")
            return input_code

        # Now find which js slot in the mapping corresponds to this physical device
        # device_mapping format: {"js1": "Thrustmaster T.16000M", "js2": "VKB Stick", ...}
        for js_slot, mapped_device_name in self.device_mapping.items():
            # Check if this is the device we detected
            if mapped_device_name and mapped_device_name.lower() in detected_device_name.lower():
                try:
                    target_instance = int(js_slot.replace('js', ''))
                    if target_instance != detected_instance:
                        # Remap: detected js1_button1 -> js2_button1 if that's where it's mapped
                        remapped_code = f"js{target_instance}_{rest_of_code}"
                        logger.info(f"Device mapping applied: {input_code} -> {remapped_code}")
                        return remapped_code
                except (ValueError, AttributeError):
                    continue

        logger.debug(f"No mapping found for device '{detected_device_name}', keeping original js{detected_instance}")
        return input_code

    def on_input_detected(self, input_code: str, description: str):
        """Handle detected input"""
        logger.info(f"Input detected: {input_code} - {description}")

        # Apply device mapping to remap joystick indices
        mapped_input_code = self._apply_device_mapping(input_code)
        logger.debug(f"After mapping: {input_code} -> {mapped_input_code}")

        # Update the stored input code
        self.input_code = mapped_input_code

        # Update the UI with proper formatting
        current_display = self._get_current_input_display()
        self.desc_label.setText(f"<b>Current:</b> {current_display}")

        # Stop detection and re-enable controls
        self.detecting_input = False
        self.detect_input_btn.setText("Detect Input")
        self._disable_controls(False)

    def on_input_detection_timeout(self):
        """Handle input detection timeout"""
        logger.info("Input detection timed out")

        QMessageBox.warning(
            self,
            "No Input Detected",
            "No input was detected within 10 seconds.\n\nPlease try again."
        )

        self.detecting_input = False
        self.detect_input_btn.setText("Detect Input")
        self._disable_controls(False)

    def _disable_controls(self, disable: bool):
        """Enable/disable controls during input detection"""
        self.action_map_combo.setEnabled(not disable)
        self.action_combo.setEnabled(not disable)
        self.add_action_btn.setEnabled(not disable)
        self.input_code_combo.setEnabled(not disable)
        for child in self.findChildren(QPushButton):
            if child != self.detect_input_btn:
                child.setEnabled(not disable)

    def _populate_input_codes(self):
        """Populate the input code dropdown with available inputs"""
        try:
            # Get list of available devices
            devices = InputDetector.get_available_devices()

            # Group inputs by device type
            inputs_by_device = {}

            # Add joystick inputs
            for device in devices:
                if device.get('type') == 'joystick':
                    instance = device.get('instance', 0)
                    product_name = device.get('name', f"Joystick {instance}")
                    device_label = f"Joystick {instance}: {product_name}"

                    if device_label not in inputs_by_device:
                        inputs_by_device[device_label] = []

                    # Add buttons (1-128)
                    for btn in range(1, 129):
                        code = f"js{instance}_button{btn}"
                        inputs_by_device[device_label].append((code, f"Button {btn}"))

                    # Add axes
                    for axis in ['x', 'y', 'z', 'rotx', 'roty', 'rotz', 'slider1', 'slider2']:
                        code = f"js{instance}_{axis}"
                        inputs_by_device[device_label].append((code, f"Axis {axis.upper()}"))

                    # Add POV/hat switches
                    for hat in range(1, 5):
                        for direction in ['up', 'down', 'left', 'right']:
                            code = f"js{instance}_hat{hat}_{direction}"
                            inputs_by_device[device_label].append((code, f"Hat {hat} {direction.capitalize()}"))

            # Add keyboard inputs
            keyboard_inputs = [
                ('kb1_escape', 'ESC'), ('kb1_1', '1'), ('kb1_2', '2'), ('kb1_3', '3'),
                ('kb1_4', '4'), ('kb1_5', '5'), ('kb1_6', '6'), ('kb1_7', '7'),
                ('kb1_8', '8'), ('kb1_9', '9'), ('kb1_0', '0'), ('kb1_minus', 'Minus'),
                ('kb1_equals', 'Equals'), ('kb1_backspace', 'Backspace'),
                ('kb1_tab', 'Tab'), ('kb1_q', 'Q'), ('kb1_w', 'W'), ('kb1_e', 'E'),
                ('kb1_r', 'R'), ('kb1_t', 'T'), ('kb1_y', 'Y'), ('kb1_u', 'U'),
                ('kb1_i', 'I'), ('kb1_o', 'O'), ('kb1_p', 'P'), ('kb1_lbracket', '['),
                ('kb1_rbracket', ']'), ('kb1_return', 'Enter'),
                ('kb1_lctrl', 'L Ctrl'), ('kb1_a', 'A'), ('kb1_s', 'S'), ('kb1_d', 'D'),
                ('kb1_f', 'F'), ('kb1_g', 'G'), ('kb1_h', 'H'), ('kb1_j', 'J'),
                ('kb1_k', 'K'), ('kb1_l', 'L'), ('kb1_semicolon', ';'), ('kb1_apostrophe', "'"),
                ('kb1_grave', '`'), ('kb1_lshift', 'L Shift'), ('kb1_backslash', '\\'),
                ('kb1_z', 'Z'), ('kb1_x', 'X'), ('kb1_c', 'C'), ('kb1_v', 'V'),
                ('kb1_b', 'B'), ('kb1_n', 'N'), ('kb1_m', 'M'), ('kb1_comma', ','),
                ('kb1_period', '.'), ('kb1_slash', '/'), ('kb1_rshift', 'R Shift'),
                ('kb1_np_multiply', 'Numpad *'), ('kb1_lalt', 'L Alt'), ('kb1_space', 'Space'),
                ('kb1_capslock', 'Caps Lock'), ('kb1_f1', 'F1'), ('kb1_f2', 'F2'),
                ('kb1_f3', 'F3'), ('kb1_f4', 'F4'), ('kb1_f5', 'F5'), ('kb1_f6', 'F6'),
                ('kb1_f7', 'F7'), ('kb1_f8', 'F8'), ('kb1_f9', 'F9'), ('kb1_f10', 'F10'),
                ('kb1_numlock', 'Num Lock'), ('kb1_scrolllock', 'Scroll Lock'),
                ('kb1_np_7', 'Numpad 7'), ('kb1_np_8', 'Numpad 8'),
                ('kb1_np_9', 'Numpad 9'), ('kb1_np_subtract', 'Numpad -'),
                ('kb1_np_4', 'Numpad 4'), ('kb1_np_5', 'Numpad 5'),
                ('kb1_np_6', 'Numpad 6'), ('kb1_np_add', 'Numpad +'),
                ('kb1_np_1', 'Numpad 1'), ('kb1_np_2', 'Numpad 2'),
                ('kb1_np_3', 'Numpad 3'), ('kb1_np_0', 'Numpad 0'),
                ('kb1_decimal', 'Numpad .'), ('kb1_f11', 'F11'), ('kb1_f12', 'F12'),
                ('kb1_np_divide', 'Numpad /'), ('kb1_rctrl', 'R Ctrl'),
                ('kb1_up', 'Up'), ('kb1_down', 'Down'), ('kb1_left', 'Left'),
                ('kb1_right', 'Right'), ('kb1_home', 'Home'), ('kb1_end', 'End'),
                ('kb1_pgup', 'Page Up'), ('kb1_pgdn', 'Page Down'),
                ('kb1_insert', 'Insert'), ('kb1_delete', 'Delete'),
                ('kb1_ralt', 'R Alt'), ('kb1_pause', 'Pause'), ('kb1_print', 'Print'),
            ]
            inputs_by_device['Keyboard'] = keyboard_inputs

            # Add mouse inputs
            mouse_inputs = [
                ('mouse1', 'Left Click'),
                ('mouse2', 'Right Click'),
                ('mouse3', 'Middle Click'),
                ('mouse4', 'Button 4'),
                ('mouse5', 'Button 5'),
                ('mwheel_up', 'Wheel Up'),
                ('mwheel_down', 'Wheel Down'),
            ]
            inputs_by_device['Mouse'] = mouse_inputs

            # Add items to combo box, grouped by device
            for device_label in sorted(inputs_by_device.keys()):
                for input_code, label in sorted(inputs_by_device[device_label], key=lambda x: x[1]):
                    display_text = f"{device_label} - {label}"
                    self.input_code_combo.addItem(display_text, input_code)

            logger.debug(f"Populated input codes dropdown with {self.input_code_combo.count()} items")
        except Exception as e:
            logger.error(f"Error populating input codes: {e}", exc_info=True)

    def on_input_code_selected(self, index: int):
        """Handle input code selection from dropdown"""
        if index <= 0:
            return

        new_input_code = self.input_code_combo.currentData()
        if not new_input_code:
            return

        # Update the stored input code
        old_input_code = self.input_code
        self.input_code = new_input_code

        # Update the description using consistent formatting
        current_display = self._get_current_input_display()
        self.desc_label.setText(f"<b>Current:</b> {current_display}")

        logger.info(f"Input code changed: {old_input_code} → {new_input_code}")

        # Reset dropdown to show "(Select Input Code)"
        self.input_code_combo.blockSignals(True)
        self.input_code_combo.setCurrentIndex(0)
        self.input_code_combo.blockSignals(False)
