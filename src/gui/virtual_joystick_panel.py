"""
Virtual Joystick panel — clickable stand-ins for the mock joysticks.

Shown only when the app runs with ``--mock-joysticks`` (or the
``SCPE_MOCK_JOYSTICKS`` env var). Each mock device gets its buttons, hats
and axes as widgets; using them injects events into the mock backend, so
the Remap Dialog's "Detect Input" sees them exactly as it would see a
real stick. Nothing here runs in a normal (hardware) session.
"""

import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                             QPushButton, QScrollArea, QSlider, QVBoxLayout,
                             QWidget)

from utils.joystick_backend import AXIS_NAMES, JoyEvent, MockBackend

logger = logging.getLogger(__name__)

BUTTONS_PER_ROW = 8


class VirtualJoystickPanel(QWidget):

    def __init__(self, backend: MockBackend, parent=None):
        super().__init__(parent, Qt.WindowType.Tool)
        self.backend = backend
        self.setWindowTitle("Virtual Joysticks (mock mode)")
        self.resize(460, 640)

        outer = QVBoxLayout(self)
        self.status = QLabel()
        self.status.setWordWrap(True)
        outer.addWidget(self.status)

        source = QLabel(f"Devices from: {backend.source or '(in memory)'}")
        source.setProperty("role", "secondary")
        source.setWordWrap(True)
        outer.addWidget(source)

        body = QWidget()
        body_layout = QVBoxLayout(body)
        for joy_index, info in enumerate(backend.devices):
            body_layout.addWidget(self._device_box(joy_index, info))
        body_layout.addStretch(1)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(body)
        outer.addWidget(scroll, 1)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_status)
        self._timer.start(250)
        self._refresh_status()

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
