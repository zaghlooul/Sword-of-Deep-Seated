"""
SwordSuite — Sessions Panel
Browse, load, and manage saved scan sessions.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Callable, Optional

from PyQt6.QtCore    import Qt
from PyQt6.QtGui     import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QFileDialog, QFrame, QGridLayout,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QMessageBox, QPushButton, QSizePolicy, QTableWidget,
    QTableWidgetItem, QVBoxLayout, QWidget,
)

from recon_suite.core.session import (
    Session, delete_session, list_sessions, SESSIONS_DIR,
)
from recon_suite.styles.theme import P
from recon_suite.ui.widgets.form_widgets import SectionHeader


class SessionsPanel(QWidget):
    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate = navigate_cb
        self._sessions: list[Path] = []
        self._setup_ui()
        self.refresh()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        bar_hl = QHBoxLayout(bar)
        bar_hl.setContentsMargins(24, 0, 24, 0)
        bar_hl.setSpacing(16)

        icon = QLabel("💾")
        icon.setStyleSheet("font-size:20px;")
        title = QLabel("Sessions")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        sub = QLabel("Saved scan sessions — load or export past results")
        sub.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        bar_hl.addWidget(icon)
        bar_hl.addWidget(title)
        bar_hl.addWidget(sub)
        bar_hl.addStretch()
        root.addWidget(bar)

        # Body
        body = QWidget()
        body.setStyleSheet(f"background:{P['bg1']};")
        root.addWidget(body, 1)

        vl = QVBoxLayout(body)
        vl.setContentsMargins(24, 20, 24, 20)
        vl.setSpacing(16)

        # Toolbar
        tb = QHBoxLayout()
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search sessions…")
        self._search.setFixedWidth(240)
        self._search.textChanged.connect(self._apply_filter)
        tb.addWidget(self._search)
        tb.addStretch()

        self._count_lbl = QLabel("0 sessions")
        self._count_lbl.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        tb.addWidget(self._count_lbl)

        for text, cb in [
            ("New Session", self._new_session),
            ("Refresh",     self.refresh),
            ("Export",      self._export_selected),
            ("Delete",      self._delete_selected),
        ]:
            btn = QPushButton(text)
            btn.setObjectName("BtnSmall")
            btn.clicked.connect(cb)
            tb.addWidget(btn)
        vl.addLayout(tb)

        # Table
        self._table = QTableWidget(0, 7)
        self._table.setHorizontalHeaderLabels(
            ["Name", "Target", "Dorks", "Endpoints", "Injections", "Updated", "Path"]
        )
        self._table.setAlternatingRowColors(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.doubleClicked.connect(self._load_selected)

        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(6, QHeaderView.ResizeMode.Stretch)

        vl.addWidget(self._table, 1)

        # Detail card
        self._detail = QWidget()
        self._detail.setStyleSheet(
            f"background:{P['bg2']}; border:1px solid {P['border']}; border-radius:8px;"
        )
        self._detail.setFixedHeight(120)
        detail_hl = QHBoxLayout(self._detail)
        detail_hl.setContentsMargins(20, 12, 20, 12)
        detail_hl.setSpacing(30)

        self._d_name  = self._detail_stat("—", "Session")
        self._d_dorks = self._detail_stat("0", "Dork Results", P["blue"])
        self._d_ep    = self._detail_stat("0", "Endpoints",    P["cyan"])
        self._d_inj   = self._detail_stat("0", "Injections",   P["purple"])
        self._d_date  = self._detail_stat("—", "Last Updated")

        for w in (self._d_name, self._d_dorks, self._d_ep, self._d_inj, self._d_date):
            detail_hl.addWidget(w)

        detail_hl.addStretch()

        open_btn = QPushButton("Open Session")
        open_btn.setObjectName("BtnPrimary")
        open_btn.clicked.connect(self._load_selected)
        detail_hl.addWidget(open_btn)

        vl.addWidget(self._detail)
        self._table.itemSelectionChanged.connect(self._on_selection)

    def _detail_stat(self, value: str, label: str, color: str = "") -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(2)

        val_lbl = QLabel(value)
        c = color or P["text"]
        val_lbl.setStyleSheet(f"color:{c}; font-size:22px; font-weight:700; font-family:monospace;")
        lbl_lbl = QLabel(label)
        lbl_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:10px; font-weight:600; letter-spacing:1px;")
        vl.addWidget(val_lbl)
        vl.addWidget(lbl_lbl)

        # Store refs
        setattr(self, f"_dv_{label.replace(' ','_').lower()}", val_lbl)
        return w

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        self._sessions = list_sessions()
        self._table.setRowCount(0)

        for path in self._sessions:
            try:
                s = Session.load(path)
                self._insert_row(s, path)
            except Exception:
                continue

        self._count_lbl.setText(f"{len(self._sessions)} session(s)")

    def _insert_row(self, s: Session, path: Path) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(s.updated_at))

        for col, text in enumerate([
            s.name,
            s.target or "—",
            str(len(s.dork_results)),
            str(len(s.katana_results)),
            str(len(s.sqlmap_results)),
            date_str,
            str(path),
        ]):
            item = QTableWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, (s, path))
            if col in (2, 3, 4):
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if text != "0":
                    colors = {2: P["blue"], 3: P["cyan"], 4: P["purple"]}
                    item.setForeground(QColor(colors[col]))
            self._table.setItem(row, col, item)

    def _apply_filter(self, text: str) -> None:
        text = text.lower()
        for row in range(self._table.rowCount()):
            item = self._table.item(row, 0)
            self._table.setRowHidden(row, bool(text) and text not in (item.text().lower() if item else ""))

    def _on_selection(self) -> None:
        rows = list({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            return
        item = self._table.item(rows[0], 0)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        s, _ = data
        date_str = time.strftime("%Y-%m-%d %H:%M", time.localtime(s.updated_at))
        try:
            self._dv_session.setText(s.name or "—")
            self._dv_dork_results.setText(str(len(s.dork_results)))
            self._dv_endpoints.setText(str(len(s.katana_results)))
            self._dv_injections.setText(str(len(s.sqlmap_results)))
            self._dv_last_updated.setText(date_str)
        except AttributeError:
            pass

    # ------------------------------------------------------------------
    def _load_selected(self) -> None:
        rows = list({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            return
        item = self._table.item(rows[0], 0)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        s, path = data
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self, "Session Loaded",
            f"Session '{s.name}' loaded.\n"
            f"  Dork results : {len(s.dork_results)}\n"
            f"  Endpoints    : {len(s.katana_results)}\n"
            f"  Injections   : {len(s.sqlmap_results)}\n\n"
            f"Navigate to individual tool panels to view details.",
        )

    def _new_session(self) -> None:
        from PyQt6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "New Session", "Session name:")
        if ok and name.strip():
            s = Session(name=name.strip())
            path = s.save()
            self.refresh()

    def _export_selected(self) -> None:
        rows = list({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            return
        item = self._table.item(rows[0], 0)
        if not item:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        s, _ = data
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Session", f"{s.name}.txt", "Text (*.txt);;JSON (*.json)"
        )
        if path:
            from pathlib import Path as _P
            p = _P(path)
            if path.endswith(".json"):
                p.write_text(
                    __import__("json").dumps(
                        __import__("dataclasses").asdict(s), indent=2
                    ), encoding="utf-8"
                )
            else:
                s.export_txt(p)

    def _delete_selected(self) -> None:
        rows = list({idx.row() for idx in self._table.selectedIndexes()})
        if not rows:
            return
        ret = QMessageBox.question(
            self, "Delete Session",
            "Delete the selected session(s)? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if ret != QMessageBox.StandardButton.Yes:
            return
        for row in sorted(rows, reverse=True):
            item = self._table.item(row, 0)
            if item:
                data = item.data(Qt.ItemDataRole.UserRole)
                if data:
                    _, path = data
                    delete_session(path)
        self.refresh()
