"""
Virtual Joystick panel — clickable stand-ins for the mock joysticks.

Shown only when the app runs with ``--mock-joysticks`` (or the
``SCPE_MOCK_JOYSTICKS`` env var). Each mock device gets its buttons, hats
and axes as widgets; using them injects events into the mock backend, so
the Remap Dialog's "Detect Input" sees them exactly as it would see a
real stick. The sticks can be rebuilt from any SC profile, either by
following each profile the main window opens or via "Load setup…".
Nothing here runs in a normal (hardware) session.
"""

import logging
import os
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QCheckBox, QFileDialog, QGridLayout, QGroupBox,
                             QHBoxLayout, QLabel, QMessageBox, QPushButton,
                             QScrollArea, QSlider, QVBoxLayout, QWidget)

from utils.joystick_backend import AXIS_NAMES, JoyEvent, MockBackend, devices_from_profile

logger = logging.getLogger(__name__)

BUTTONS_PER_ROW = 8


class VirtualJoystickPanel(QWidget):
    """Floating window of virtual stick controls.

    ``follow_profiles``: rebuild the sticks to match each profile the main
    window opens (connect ``attach_to_main_window``).
    ``on_devices_changed``: called after the sticks change, so the app can
    re-scan devices (Config tab, Device View).
    """

    def __init__(self, backend: MockBackend, parent=None, follow_profiles: bool = True,
                 on_devices_changed: Optional[Callable[[], None]] = None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.backend = backend
        self.on_devices_changed = on_devices_changed
        self.setWindowTitle("Virtual Joysticks (mock mode)")
        self.resize(460, 640)

        outer = QVBoxLayout(self)
        self.status = QLabel()
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        controls = QHBoxLayout()
        self.follow_checkbox = QCheckBox("Match the profile I open")
        self.follow_checkbox.setToolTip(
            "Rebuild the virtual sticks from each profile you load, so its js1, js2… "
            "devices are 'connected'.")
        self.follow_checkbox.setChecked(follow_profiles)
        controls.addWidget(self.follow_checkbox)
        controls.addStretch(1)
        load_btn = QPushButton("Load setup…")
        load_btn.setToolTip("Build the virtual sticks from any SC profile (.xml) or devices file (.json)")
        load_btn.clicked.connect(self._choose_setup_file)
        controls.addWidget(load_btn)
        outer.addLayout(controls)

        self.source_label = QLabel()
        self.source_label.setProperty("role", "secondary")
        self.source_label.setWordWrap(True)
        outer.addWidget(self.source_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        outer.addWidget(self.scroll, 1)
        self._rebuild()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(250)
        self._refresh_status()

    # -- switching setups -------------------------------------------------

    def attach_to_main_window(self, main_window) -> None:
        """Follow profiles the main window loads (when the box is ticked)."""
        main_window.profile_loaded.connect(self._on_profile_loaded)

    def _on_profile_loaded(self, path: str) -> None:
        if self.follow_checkbox.isChecked():
            self.load_setup(path)

    def _choose_setup_file(self) -> None:
        start = os.path.dirname(self.backend.source) if self.backend.source else ""
        path, _ = QFileDialog.getOpenFileName(
            self, "Load virtual joystick setup", start,
            "SC profiles or device files (*.xml *.json);;All Files (*)")
        if path:
            # Picking a setup by hand means "keep this one".
            self.follow_checkbox.setChecked(False)
            self.load_setup(path)

    def load_setup(self, path: str) -> bool:
        """Replace the virtual sticks with the ones described by ``path``."""
        try:
            if path.lower().endswith(".xml"):
                devices = devices_from_profile(path)
            else:
                devices = MockBackend.from_file(path).devices
        except Exception as e:
            logger.error(f"Could not load virtual joystick setup from {path}: {e}", exc_info=True)
            QMessageBox.warning(self, "Virtual Joysticks", f"Could not load a setup from:\n{path}\n\n{e}")
            return False

        self.backend.set_devices(devices, source=path)
        logger.info(f"Virtual joysticks now mirror {path}: {[d.name for d in devices]}")
        self._rebuild()
        if self.on_devices_changed:
            try:
                self.on_devices_changed()
            except Exception as e:
                logger.error(f"Refreshing devices after setup change failed: {e}", exc_info=True)
        return True

    def _rebuild(self) -> None:
        self.source_label.setText(f"Sticks from: {self.backend.source or '(in memory)'}")
        body = QWidget()
        body_layout = QVBoxLayout(body)
        if not self.backend.devices:
            body_layout.addWidget(QLabel("This setup has no joysticks."))
        for joy_index, info in enumerate(self.backend.devices):
            body_layout.addWidget(self._device_box(joy_index, info))
        body_layout.addStretch(1)
        self.scroll.setWidget(body)  # deletes the previous body

    # -- layout -----------------------------------------------------------

    def _device_box(self, joy, info) -> QGroupBox:
        title = f"js{joy + 1}  {info.name.strip()}"
        if info.vid_pid:
            title += f"  (VID {info.vid_pid[0]:04X} / PID {info.vid_pid[1]:04X})"
        box = QGroupBox(title)
        layout = QVBoxLayout(box)

        if info.buttons:
            grid = QGridLayout()
            for b in range(info.buttons):
                btn = QPushButton(str(b + 1))
                btn.setFixedWidth(40)
                btn.setToolTip(f"js{joy + 1}_button{b + 1}")
                btn.pressed.connect(lambda j=joy, b=b: self._send(JoyEvent("button", j, b, 1)))
                btn.released.connect(lambda j=joy, b=b: self._send(JoyEvent("button", j, b, 0)))
                grid.addWidget(btn, b // BUTTONS_PER_ROW, b % BUTTONS_PER_ROW)
            layout.addLayout(grid)

        if info.hats:
            hats_row = QHBoxLayout()
            for h in range(info.hats):
                hats_row.addWidget(self._hat_widget(joy, h))
            hats_row.addStretch(1)
            layout.addLayout(hats_row)

        for a in range(info.axes):
            layout.addLayout(self._axis_row(joy, a))
        return box

    def _hat_widget(self, joy, hat) -> QWidget:
        w = QWidget()
        grid = QGridLayout(w)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(QLabel(f"Hat {hat + 1}"), 1, 1, Qt.AlignmentFlag.AlignCenter)
        for label, value, row, col in (("▲", (0, 1), 0, 1), ("▼", (0, -1), 2, 1),
                                       ("◀", (-1, 0), 1, 0), ("▶", (1, 0), 1, 2)):
            btn = QPushButton(label)
            btn.setFixedWidth(34)
            btn.pressed.connect(lambda v=value: self._send(JoyEvent("hat", joy, hat, v)))
            btn.released.connect(lambda: self._send(JoyEvent("hat", joy, hat, (0, 0))))
            grid.addWidget(btn, row, col)
        return w

    def _axis_row(self, joy, axis) -> QHBoxLayout:
        row = QHBoxLayout()
        name = AXIS_NAMES.get(axis, f"axis{axis}")
        row.addWidget(QLabel(name))
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(-100, 100)
        slider.setToolTip(f"js{joy + 1}_{name} — drag past halfway to trigger; snaps back on release")
        slider.valueChanged.connect(lambda v: self._send(JoyEvent("axis", joy, axis, v / 100.0)))
        slider.sliderReleased.connect(lambda s=slider: s.setValue(0))
        row.addWidget(slider, 1)
        return row

    # -- behaviour --------------------------------------------------------

    def _send(self, event: JoyEvent):
        try:
            self.backend.inject(event)
        except ValueError as e:
            logger.warning(f"Virtual joystick: {e}")

    def _refresh_status(self):
        if self.backend.listening:
            self.status.setText("● Listening — click a control to send it to Detect Input.")
        else:
            self.status.setText("Not listening. Open a binding and press Detect Input, "
                                "then use a control below.")
