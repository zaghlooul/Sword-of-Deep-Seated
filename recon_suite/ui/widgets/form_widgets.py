"""
SwordSuite — Shared Form Widgets
Reusable building blocks for the scan configuration panels.
"""
from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QPainter, QBrush, QPen
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QGridLayout, QGroupBox,
    QHBoxLayout, QLabel, QPushButton, QSizePolicy,
    QSlider, QSpinBox, QTextEdit, QVBoxLayout, QWidget,
    QLineEdit,
)

from recon_suite.styles.theme import P


# ---------------------------------------------------------------------------
# Helper: create a styled label
# ---------------------------------------------------------------------------
def _lbl(text: str, color: str = P["text_sec"], size: int = 12) -> QLabel:
    l = QLabel(text)
    l.setStyleSheet(f"color:{color}; font-size:{size}px;")
    return l


# ---------------------------------------------------------------------------
# FormRow — label + widget pair
# ---------------------------------------------------------------------------
class FormRow(QWidget):
    def __init__(
        self,
        label: str,
        widget: QWidget,
        tooltip: str = "",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 2, 0, 2)
        hl.setSpacing(10)

        lbl = QLabel(label)
        lbl.setFixedWidth(140)
        lbl.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        if tooltip:
            lbl.setToolTip(tooltip)
        hl.addWidget(lbl)
        hl.addWidget(widget, 1)


# ---------------------------------------------------------------------------
# SectionHeader — coloured bar with title
# ---------------------------------------------------------------------------
class SectionHeader(QLabel):
    def __init__(
        self,
        title: str,
        color: str = P["cyan"],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(title, parent)
        self.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 11px;
                font-weight: 700;
                letter-spacing: 1.2px;
                text-transform: uppercase;
                padding: 4px 0 4px 0;
                border-bottom: 1px solid {color}44;
            }}
        """)


# ---------------------------------------------------------------------------
# StatusIndicator — coloured dot with label
# ---------------------------------------------------------------------------
class StatusDot(QWidget):
    def __init__(
        self,
        label: str,
        ok: bool = True,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        dot = QLabel("●")
        color = P["green"] if ok else P["red"]
        dot.setStyleSheet(f"color:{color}; font-size:10px;")
        hl.addWidget(dot)

        lbl = QLabel(label)
        lbl.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hl.addWidget(lbl)
        hl.addStretch()


# ---------------------------------------------------------------------------
# LabeledSlider — slider + value display
# ---------------------------------------------------------------------------
class LabeledSlider(QWidget):
    valueChanged = pyqtSignal(int)

    def __init__(
        self,
        minimum: int,
        maximum: int,
        value: int   = 1,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        self._slider = QSlider(Qt.Orientation.Horizontal)
        self._slider.setMinimum(minimum)
        self._slider.setMaximum(maximum)
        self._slider.setValue(value)
        self._slider.setTickPosition(QSlider.TickPosition.NoTicks)

        self._val_lbl = QLabel(str(value))
        self._val_lbl.setFixedWidth(28)
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._val_lbl.setStyleSheet(
            f"color:{P['cyan']}; font-weight:600; font-family:monospace;"
        )

        self._slider.valueChanged.connect(self._on_change)
        hl.addWidget(self._slider, 1)
        hl.addWidget(self._val_lbl)

    def _on_change(self, v: int) -> None:
        self._val_lbl.setText(str(v))
        self.valueChanged.emit(v)

    @property
    def value(self) -> int:
        return self._slider.value()

    @value.setter
    def value(self, v: int) -> None:
        self._slider.setValue(v)


# ---------------------------------------------------------------------------
# MultiCheck — horizontal row of checkboxes for technique selection etc.
# ---------------------------------------------------------------------------
class MultiCheck(QWidget):
    def __init__(
        self,
        items: List[Tuple[str, str, bool]],  # (code, label, default)
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(6)

        self._boxes: dict[str, QCheckBox] = {}
        for code, label, checked in items:
            cb = QCheckBox(label)
            cb.setChecked(checked)
            cb.setToolTip(f"Code: {code}")
            hl.addWidget(cb)
            self._boxes[code] = cb
        hl.addStretch()

    def checked_codes(self) -> List[str]:
        return [code for code, cb in self._boxes.items() if cb.isChecked()]

    def set_checked(self, codes: List[str]) -> None:
        for code, cb in self._boxes.items():
            cb.setChecked(code in codes)


# ---------------------------------------------------------------------------
# TagInput — text + "Add" button → list of removable tags
# ---------------------------------------------------------------------------
class TagInput(QWidget):
    tagsChanged = pyqtSignal(list)

    def __init__(
        self,
        placeholder: str = "Add item…",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._tags: List[str] = []

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(4)

        # Input row
        hl = QHBoxLayout()
        hl.setSpacing(6)
        self._input = QLineEdit()
        self._input.setPlaceholderText(placeholder)
        self._input.returnPressed.connect(self._add)
        add_btn = QPushButton("Add")
        add_btn.setObjectName("BtnSmall")
        add_btn.clicked.connect(self._add)
        hl.addWidget(self._input, 1)
        hl.addWidget(add_btn)
        vl.addLayout(hl)

        # Tags area
        self._tags_widget = QWidget()
        self._tags_layout = QHBoxLayout(self._tags_widget)
        self._tags_layout.setContentsMargins(0, 0, 0, 0)
        self._tags_layout.setSpacing(4)
        self._tags_layout.addStretch()
        vl.addWidget(self._tags_widget)

    def _add(self) -> None:
        text = self._input.text().strip()
        if text and text not in self._tags:
            self._tags.append(text)
            self._rebuild()
            self._input.clear()
            self.tagsChanged.emit(self._tags)

    def _rebuild(self) -> None:
        # Clear layout
        while self._tags_layout.count() > 1:
            item = self._tags_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for tag in self._tags:
            chip = self._make_chip(tag)
            self._tags_layout.insertWidget(self._tags_layout.count() - 1, chip)

    def _make_chip(self, tag: str) -> QWidget:
        w = QWidget()
        hl = QHBoxLayout(w)
        hl.setContentsMargins(6, 2, 4, 2)
        hl.setSpacing(4)
        w.setStyleSheet(f"""
            QWidget {{
                background:{P['cyan']}22;
                border:1px solid {P['cyan']}55;
                border-radius:10px;
            }}
        """)
        lbl = QLabel(tag)
        lbl.setStyleSheet(f"color:{P['cyan']}; font-size:11px; background:transparent; border:none;")
        rm  = QPushButton("×")
        rm.setFixedSize(14, 14)
        rm.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{P['text_muted']};
                border:none; font-size:13px; padding:0;
            }}
            QPushButton:hover {{ color:{P['red']}; }}
        """)
        rm.clicked.connect(lambda: self._remove(tag))
        hl.addWidget(lbl)
        hl.addWidget(rm)
        return w

    def _remove(self, tag: str) -> None:
        if tag in self._tags:
            self._tags.remove(tag)
            self._rebuild()
            self.tagsChanged.emit(self._tags)

    @property
    def tags(self) -> List[str]:
        return list(self._tags)

    def set_tags(self, tags: List[str]) -> None:
        self._tags = list(tags)
        self._rebuild()


# ---------------------------------------------------------------------------
# CollapsibleSection
# ---------------------------------------------------------------------------
class CollapsibleSection(QWidget):
    def __init__(
        self,
        title: str,
        color: str = P["cyan"],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._collapsed = False

        vl = QVBoxLayout(self)
        vl.setContentsMargins(0, 0, 0, 4)
        vl.setSpacing(0)

        # Toggle header
        self._header = QPushButton(f"▾  {title}")
        self._header.setStyleSheet(f"""
            QPushButton {{
                background:{P['bg2']};
                color:{color};
                border:none;
                border-bottom:1px solid {P['border']};
                padding:6px 8px;
                text-align:left;
                font-size:11px;
                font-weight:700;
                letter-spacing:0.8px;
                text-transform:uppercase;
            }}
            QPushButton:hover {{ background:{P['bg3']}; }}
        """)
        self._header.clicked.connect(self._toggle)
        vl.addWidget(self._header)

        # Content wrapper
        self._content = QWidget()
        self._content.setStyleSheet(f"background:{P['bg2']};")
        vl.addWidget(self._content)

        self._inner = QVBoxLayout(self._content)
        self._inner.setContentsMargins(8, 6, 8, 6)
        self._inner.setSpacing(6)

    def add_widget(self, w: QWidget) -> None:
        self._inner.addWidget(w)

    def add_layout(self, l) -> None:
        self._inner.addLayout(l)

    def _toggle(self) -> None:
        self._collapsed = not self._collapsed
        self._content.setVisible(not self._collapsed)
        arrow = "▸" if self._collapsed else "▾"
        txt = self._header.text()
        self._header.setText(f"{arrow}  {txt[3:]}")


# ---------------------------------------------------------------------------
# RunStopBar — reusable Run / Stop / Status bar
# ---------------------------------------------------------------------------
class RunStopBar(QWidget):
    run_clicked  = pyqtSignal()
    stop_clicked = pyqtSignal()

    def __init__(
        self,
        run_label:  str = "Run",
        run_color:  str = "BtnSuccess",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        hl = QHBoxLayout(self)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(8)

        self._run_btn = QPushButton(f"▶  {run_label}")
        self._run_btn.setObjectName(run_color)
        self._run_btn.clicked.connect(self.run_clicked)
        self._run_btn.setMinimumWidth(120)

        self._stop_btn = QPushButton("■  Stop")
        self._stop_btn.setObjectName("BtnDanger")
        self._stop_btn.clicked.connect(self.stop_clicked)
        self._stop_btn.setEnabled(False)
        self._stop_btn.setMinimumWidth(90)

        self._status = QLabel("Idle")
        self._status.setStyleSheet(f"color:{P['text_muted']}; font-size:12px;")

        hl.addWidget(self._run_btn)
        hl.addWidget(self._stop_btn)
        hl.addStretch()
        hl.addWidget(self._status)

    def set_running(self, running: bool) -> None:
        self._run_btn.setEnabled(not running)
        self._stop_btn.setEnabled(running)
        self._status.setText("Running…" if running else "Idle")
        color = P["orange"] if running else P["text_muted"]
        self._status.setStyleSheet(f"color:{color}; font-size:12px;")

    def set_status(self, text: str, color: str = "") -> None:
        self._status.setText(text)
        c = color or P["text_sec"]
        self._status.setStyleSheet(f"color:{c}; font-size:12px;")


# ---------------------------------------------------------------------------
# ToolStatusCard — shows if a tool is installed
# ---------------------------------------------------------------------------
class ToolStatusCard(QFrame):
    def __init__(
        self,
        tool_name: str,
        path: Optional[str],
        description: str,
        install_hint: str,
        accent: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setFrameShape(QFrame.Shape.NoFrame)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(16, 14, 16, 14)
        vl.setSpacing(6)

        # Header row
        hl = QHBoxLayout()
        name_lbl = QLabel(tool_name)
        name_lbl.setStyleSheet(f"color:{accent}; font-size:15px; font-weight:700;")
        hl.addWidget(name_lbl)
        hl.addStretch()

        status_lbl = QLabel("● INSTALLED" if path else "● NOT FOUND")
        color = P["green"] if path else P["red"]
        status_lbl.setStyleSheet(f"color:{color}; font-size:10px; font-weight:700;")
        hl.addWidget(status_lbl)
        vl.addLayout(hl)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        desc_lbl.setWordWrap(True)
        vl.addWidget(desc_lbl)

        # Path or install hint
        if path:
            path_lbl = QLabel(f"Path: {path}")
            path_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px; font-family:monospace;")
            vl.addWidget(path_lbl)
        else:
            hint_lbl = QLabel(f"Install: {install_hint}")
            hint_lbl.setStyleSheet(
                f"color:{P['orange']}; font-size:11px; font-family:monospace;"
            )
            hint_lbl.setWordWrap(True)
            vl.addWidget(hint_lbl)
