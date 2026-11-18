"""Check Profile dialog: shows what ``utils.profile_checker`` found.

The device table compares the profile's js1/js2/... with the order this PC
numbers its sticks right now; the list below it explains each problem.
"Check again" re-reads the connected sticks, so the user can re-plug a
stick and confirm the order is fixed without closing the dialog.
"""
import html
import logging
from typing import Callable, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
                             QTableWidget, QTableWidgetItem, QTextBrowser, QHeaderView,
                             QGroupBox)

from utils.profile_checker import CheckReport, check_profile, ERROR, WARNING, INFO
from utils.system_devices import list_system_joysticks

logger = logging.getLogger(__name__)

_SEVERITY_LABEL = {ERROR: "Fix before playing", WARNING: "Problem", INFO: "Worth a look"}
_SEVERITY_ICON = {ERROR: "⛔", WARNING: "⚠️", INFO: "ℹ️"}
_STATUS_TEXT = {
    "ok": "✓ Matches",
    "swapped": "✗ Different stick in this slot",
    "missing": "✗ Not connected",
    "extra": "Not in profile",
    "unknown": "? Can't tell",
}
_STATUS_COLOR = {"ok": "#2E7D32", "swapped": "#C62828", "missing": "#C62828"}


def _fmt_id(vid_pid) -> str:
    return f"  ({vid_pid[0]:04X}:{vid_pid[1]:04X})" if vid_pid else ""


class ProfileCheckDialog(QDialog):
    def __init__(self, xml_path_provider: Callable[[], Optional[str]], profile_label: str, parent=None):
        """``xml_path_provider`` returns the XML file to check (the main
        window writes unsaved edits to a temp file first)."""
        super().__init__(parent)
        self._xml_path_provider = xml_path_provider
        self.setWindowTitle(f"Check Profile — {profile_label}")
        self.resize(900, 680)

        layout = QVBoxLayout(self)

        self.summary_label = QLabel()
        self.summary_label.setStyleSheet("font-size: 15px; font-weight: bold; margin: 4px 0;")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        devices_box = QGroupBox("Device numbering: profile vs this PC")
        devices_layout = QVBoxLayout(devices_box)
        self.devices_table = QTableWidget(0, 4)
        self.devices_table.setHorizontalHeaderLabels(["Slot", "In the profile", "On this PC now", "Status"])
        self.devices_table.verticalHeader().setVisible(False)
        self.devices_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.devices_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        header = self.devices_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        devices_layout.addWidget(self.devices_table)
        self.source_label = QLabel()
        self.source_label.setProperty("role", "secondary")
        self.source_label.setWordWrap(True)
        devices_layout.addWidget(self.source_label)
        layout.addWidget(devices_box, 2)

        self.findings_view = QTextBrowser()
        self.findings_view.setOpenExternalLinks(False)
        layout.addWidget(self.findings_view, 3)

        buttons = QHBoxLayout()
        buttons.addStretch()
        recheck_btn = QPushButton("Check again")
        recheck_btn.setToolTip("Re-read the connected joysticks and the profile, e.g. after re-plugging a stick")
        recheck_btn.clicked.connect(self.run_check)
        buttons.addWidget(recheck_btn)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        buttons.addWidget(close_btn)
        layout.addLayout(buttons)

        self.report: Optional[CheckReport] = None
        self.run_check()

    def run_check(self):
        try:
            path = self._xml_path_provider()
            if not path:
                raise ValueError("There is no profile file to check.")
            system = list_system_joysticks()
            self.report = check_profile(path, system.devices)
        except Exception as e:
            logger.error(f"Profile check failed: {e}", exc_info=True)
            self.summary_label.setText(f"Couldn't check this profile: {e}")
            self.devices_table.setRowCount(0)
            self.findings_view.clear()
            return

        self._show_devices(self.report)
        note = f"This PC's order comes from {system.source_label}."
        if not system.exact_order:
            note += (" That can list sticks in a different order than the game does, so treat a"
                     " numbering mismatch here as a hint and confirm it in game.")
        if not system.devices:
            note = "No joysticks are connected right now, so the numbering couldn't be compared."
        self.source_label.setText(note)
        self._show_findings(self.report)

    def _show_devices(self, report: CheckReport):
        self.devices_table.setRowCount(len(report.devices))
        for r, row in enumerate(report.devices):
            cells = [row.slot,
                     (row.profile_name or "—") + _fmt_id(row.profile_vid_pid),
                     (row.system_name or "—") + _fmt_id(row.system_vid_pid),
                     _STATUS_TEXT.get(row.status, row.status)]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                if c == 3 and row.status in _STATUS_COLOR:
                    item.setForeground(QBrush(QColor(_STATUS_COLOR[row.status])))
                self.devices_table.setItem(r, c, item)

    def _show_findings(self, report: CheckReport):
        errors, warnings, infos = report.count(ERROR), report.count(WARNING), report.count(INFO)
        if not report.findings:
            self.summary_label.setText("✓ No problems found.")
        else:
            parts = []
            if errors:
                parts.append(f"{errors} to fix before playing")
            if warnings:
                parts.append(f"{warnings} problem{'s' if warnings != 1 else ''}")
            if infos:
                parts.append(f"{infos} worth a look")
            self.summary_label.setText("Found " + ", ".join(parts) + ".")

        chunks = []
        for f in report.findings:
            chunks.append(
                f"<p style='margin: 0 0 10px 0;'>"
                f"{_SEVERITY_ICON.get(f.severity, '')} <b>{html.escape(f.title)}</b>"
                f" <span style='opacity:0.7'>({_SEVERITY_LABEL.get(f.severity, f.severity)})</span><br>"
                f"{html.escape(f.detail)}</p>")
        self.findings_view.setHtml("".join(chunks) or "<p>Nothing to report.</p>")
