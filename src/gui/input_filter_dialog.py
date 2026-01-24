"""
Dialog for detecting and filtering inputs that should be ignored during detection
"""

import logging
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from src.utils.input_detector import InputDetectorThread
from src.utils.settings import AppSettings

logger = logging.getLogger(__name__)


class InputFilterDialog(QDialog):
    """Dialog for detecting and adding inputs to the ignore/filter list"""

    # Signal: (input_code, input_description) - emitted when user successfully adds an input to filter
    input_added = pyqtSignal(str, str)

    def __init__(self, parent=None):
        """
        Initialize the input filter dialog

        Args:
            parent: Parent widget
        """
        super().__init__(parent)
        self.setWindowTitle("Add Input to Filter")
        self.setModal(True)
        self.setMinimumWidth(400)

        self.settings = AppSettings()
        self.detector_thread = None
        self.detected_input_code = None
        self.detected_input_description = None

        self._setup_ui()

    def _setup_ui(self):
        """Set up the dialog UI"""
        layout = QVBoxLayout()

        # Instructions
        instructions = QLabel(
            "Click 'Detect Input' then press the button or control you want to ignore.\n"
            "It will be filtered during input detection."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        # Detection group
        detection_group = QGroupBox("Input Detection")
        detection_layout = QVBoxLayout()

        # Detect button
        self.detect_button = QPushButton("Detect Input")
        self.detect_button.clicked.connect(self._on_detect_clicked)
        detection_layout.addWidget(self.detect_button)

        # Detection result label
        self.result_label = QLabel("No input detected yet...")
        self.result_label.setStyleSheet("color: gray; font-style: italic;")
        detection_layout.addWidget(self.result_label)

        detection_group.setLayout(detection_layout)
        layout.addWidget(detection_group)

        # Buttons
        button_layout = QHBoxLayout()

        self.ignore_button = QPushButton("Add to Filter")
        self.ignore_button.clicked.connect(self._on_ignore_clicked)
        self.ignore_button.setEnabled(False)
        button_layout.addWidget(self.ignore_button)

        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def _on_detect_clicked(self):
        """Handle Detect Input button click"""
        self.detect_button.setEnabled(False)
        self.detect_button.setText("Listening... (10 sec)")
        self.result_label.setText("Waiting for input...")
        self.result_label.setStyleSheet("color: blue; font-style: italic;")
        self.ignore_button.setEnabled(False)
        self.detected_input_code = None
        self.detected_input_description = None

        # Start input detection thread
        self.detector_thread = InputDetectorThread(timeout_ms=10000)
        self.detector_thread.input_detected.connect(self._on_input_detected)
        self.detector_thread.detection_cancelled.connect(self._on_detection_cancelled)
        self.detector_thread.start()

    def _on_input_detected(self, input_code: str, input_description: str):
        """
        Handle detected input from the detector thread

        Args:
            input_code: Code of detected input (e.g., "js1_button32")
            input_description: Human-readable description of input
        """
        self.detected_input_code = input_code
        self.detected_input_description = input_description

        # Update UI
        self.result_label.setText(f"✓ {input_description}")
        self.result_label.setStyleSheet("color: green;")
        self.detect_button.setEnabled(True)
        self.detect_button.setText("Detect Input")
        self.ignore_button.setEnabled(True)

        logger.info(f"Detected input in filter dialog: {input_code}")

    def _on_detection_cancelled(self):
        """Handle detection timeout/cancellation"""
        self.result_label.setText("Detection timed out. Try again.")
        self.result_label.setStyleSheet("color: orange; font-style: italic;")
        self.detect_button.setEnabled(True)
        self.detect_button.setText("Detect Input")
        self.ignore_button.setEnabled(False)

    def _on_ignore_clicked(self):
        """Handle Add to Filter button click"""
        if not self.detected_input_code:
            QMessageBox.warning(
                self,
                "No Input Detected",
                "Please detect an input first before adding to filter."
            )
            return

        # Check if already in filter list
        if self.settings.is_input_ignored(self.detected_input_code):
            QMessageBox.information(
                self,
                "Already Filtered",
                f"'{self.detected_input_description}' is already in the filter list."
            )
            return

        # Add to filter list
        self.settings.add_ignored_input(self.detected_input_code)
        logger.info(f"Added input to filter list: {self.detected_input_code}")

        # Emit signal and show confirmation
        self.input_added.emit(self.detected_input_code, self.detected_input_description)
        QMessageBox.information(
            self,
            "Added to Filter",
            f"Input '{self.detected_input_description}' will now be ignored."
        )
        self.accept()

    def closeEvent(self, event):
        """Clean up detector thread on close"""
        if self.detector_thread and self.detector_thread.running:
            self.detector_thread.running = False
            self.detector_thread.wait(1000)
        event.accept()
