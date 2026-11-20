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
                             QGroupBox, QInputDialog, QMessageBox)

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
    def __init__(self, xml_path_provider: Callable[[], Optional[str]], profile_label: str, parent=None,
                 apply_fixes: Optional[Callable] = None):
        """``xml_path_provider`` returns the XML file to check (the main
        window writes unsaved edits to a temp file first).

        ``apply_fixes(xml_path, fixes, choices) -> [str]`` applies fixes and
        reloads the profile in the main window; without it the dialog only
        reports."""
        super().__init__(parent)
        self._xml_path_provider = xml_path_provider
        self._apply_fixes = apply_fixes
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
        self.findings_view.setOpenLinks(False)
        self.findings_view.anchorClicked.connect(self._on_fix_link)
        layout.addWidget(self.findings_view, 3)

        self.fix_note = QLabel()
        self.fix_note.setProperty("role", "secondary")
        self.fix_note.setWordWrap(True)
        self.fix_note.setVisible(False)
        layout.addWidget(self.fix_note)

        buttons = QHBoxLayout()
        self.fix_all_btn = QPushButton("Fix all safe ones")
        self.fix_all_btn.setToolTip("Apply every fix that needs no choices from you. Your file isn't "
                                    "changed until you Save Profile.")
        self.fix_all_btn.clicked.connect(self._fix_all_safe)
        self.fix_all_btn.setVisible(apply_fixes is not None)
        buttons.addWidget(self.fix_all_btn)
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
        for i, f in enumerate(report.findings):
            link = ""
            if f.fix and self._apply_fixes:
                link = f"<br><a href='fix:{i}'>🔧 {html.escape(f.fix.get('label', 'Fix'))}</a>"
            chunks.append(
                f"<p style='margin: 0 0 10px 0;'>"
                f"{_SEVERITY_ICON.get(f.severity, '')} <b>{html.escape(f.title)}</b>"
                f" <span style='opacity:0.7'>({_SEVERITY_LABEL.get(f.severity, f.severity)})</span><br>"
                f"{html.escape(f.detail)}{link}</p>")
        self.findings_view.setHtml("".join(chunks) or "<p>Nothing to report.</p>")
        n_safe = len(self._safe_fixes())
        self.fix_all_btn.setEnabled(n_safe > 0)
        self.fix_all_btn.setText(f"Fix all safe ones ({n_safe})" if n_safe else "Fix all safe ones")

    # -- fixing -----------------------------------------------------------

    def _safe_fixes(self):
        if not self.report:
            return []
        out, seen_renumber = [], False
        for f in self.report.findings:
            if not f.fix or not f.fix.get("safe"):
                continue
            if f.fix["kind"] == "renumber":
                if seen_renumber:
                    continue
                seen_renumber = True
            out.append(f.fix)
        return out

    def _on_fix_link(self, url):
        text = url.toString()
        if not text.startswith("fix:") or not self.report:
            return
        try:
            finding = self.report.findings[int(text[4:])]
        except (ValueError, IndexError):
            return
        fix = finding.fix
        choices = {}
        if fix["kind"] == "keep_one":
            actions = [b["action"] for b in fix["bindings"]]
            keep, ok = QInputDialog.getItem(
                self, "Keep one", f"Which action should {fix['input']} keep? The others are unbound.",
                actions, 0, False)
            if not ok:
                return
            choices[0] = keep
        elif fix.get("confirm"):
            if QMessageBox.question(self, "Fix", fix["confirm"]) != QMessageBox.StandardButton.Yes:
                return
        self._run_fixes([fix], choices)

    def _fix_all_safe(self):
        fixes = self._safe_fixes()
        if not fixes:
            return
        extra = [f["confirm"] for f in fixes if f.get("confirm")]
        msg = f"Apply {len(fixes)} fix{'es' if len(fixes) != 1 else ''}?"
        if extra:
            msg += "\n\nThis includes:\n• " + "\n• ".join(extra)
        msg += "\n\nNothing is written to your file until you Save Profile."
        if QMessageBox.question(self, "Fix all safe ones", msg) != QMessageBox.StandardButton.Yes:
            return
        self._run_fixes(fixes, {})

    def _run_fixes(self, fixes, choices):
        try:
            path = self._xml_path_provider()
            changes = self._apply_fixes(path, fixes, choices)
        except Exception as e:
            logger.error(f"Applying fixes failed: {e}", exc_info=True)
            QMessageBox.warning(self, "Fix", f"Couldn't apply the fix:\n{e}")
            return
        self.fix_note.setText("Fixed: " + "; ".join(changes) + ". Save Profile to keep the changes.")
        self.fix_note.setVisible(True)
        self.run_check()
