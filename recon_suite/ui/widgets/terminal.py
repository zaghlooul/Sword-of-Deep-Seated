"""
SwordSuite — Terminal Widget
Scrolling output with ANSI colour support, copy, clear, and find.
"""
from __future__ import annotations

import re
from typing import Optional

from PyQt6.QtCore    import Qt, QTimer
from PyQt6.QtGui     import (
    QColor, QFont, QTextCharFormat, QTextCursor, QAction, QKeySequence
)
from PyQt6.QtWidgets import (
    QPlainTextEdit, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QSizePolicy
)

from recon_suite.styles.theme import P


# ---------------------------------------------------------------------------
# Minimal ANSI → Qt colour mapping
# ---------------------------------------------------------------------------
_ANSI_RE = re.compile(r'\x1b\[([0-9;]*)m')

_FG = {
    "30": P["text_muted"],
    "31": P["red"],
    "32": P["green"],
    "33": P["orange"],
    "34": P["blue"],
    "35": P["purple"],
    "36": P["cyan"],
    "37": P["text"],
    "90": P["text_muted"],
    "91": P["red"],
    "92": P["green"],
    "93": P["orange"],
    "94": P["blue"],
    "95": P["purple"],
    "96": P["cyan"],
    "97": P["text"],
}


def _parse_ansi(text: str):
    """Yield (plain_text, QTextCharFormat | None) chunks."""
    current_fmt  = QTextCharFormat()
    pos, results = 0, []

    for m in _ANSI_RE.finditer(text):
        # Emit plain text before this escape
        if m.start() > pos:
            results.append((text[pos:m.start()], QTextCharFormat(current_fmt)))

        codes = m.group(1).split(";") if m.group(1) else ["0"]
        for code in codes:
            if code in ("0", ""):
                current_fmt = QTextCharFormat()
            elif code == "1":
                current_fmt.setFontWeight(700)
            elif code == "3":
                current_fmt.setFontItalic(True)
            elif code in _FG:
                current_fmt.setForeground(QColor(_FG[code]))

        pos = m.end()

    if pos < len(text):
        results.append((text[pos:], QTextCharFormat(current_fmt)))

    return results


# ---------------------------------------------------------------------------
# TerminalWidget
# ---------------------------------------------------------------------------
class TerminalWidget(QWidget):
    """
    A styled read-only terminal output widget with:
    - ANSI colour support
    - Auto-scroll (toggleable)
    - Copy / Clear toolbar
    - Optional inline search
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        show_toolbar: bool = True,
        max_lines: int = 5000,
    ) -> None:
        super().__init__(parent)
        self._max_lines  = max_lines
        self._auto_scroll = True
        self._line_count  = 0
        self._setup_ui(show_toolbar)

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------
    def _setup_ui(self, show_toolbar: bool) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if show_toolbar:
            toolbar = self._build_toolbar()
            layout.addWidget(toolbar)

        self._edit = QPlainTextEdit()
        self._edit.setReadOnly(True)
        self._edit.setMaximumBlockCount(self._max_lines)
        font = QFont("Cascadia Code", 11)
        font.setStyleHint(QFont.StyleHint.Monospace)
        self._edit.setFont(font)
        self._edit.setStyleSheet(f"""
            QPlainTextEdit {{
                background-color: {P['bg0']};
                color: {P['text']};
                border: none;
                padding: 6px;
                selection-background-color: {P['cyan']}44;
            }}
        """)
        self._edit.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self._edit)

        # Context menu
        self._edit.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        copy_act  = QAction("Copy",  self._edit)
        clear_act = QAction("Clear", self._edit)
        copy_act.triggered.connect(self._edit.copy)
        clear_act.triggered.connect(self.clear)
        self._edit.addAction(copy_act)
        self._edit.addAction(clear_act)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(34)
        bar.setStyleSheet(f"background-color:{P['bg2']}; border-bottom:1px solid {P['border']};")

        hl = QHBoxLayout(bar)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(6)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
        hl.addWidget(self._status_lbl)
        hl.addStretch()

        # Scroll lock
        self._scroll_btn = QPushButton("⬇ Auto-scroll ON")
        self._scroll_btn.setCheckable(True)
        self._scroll_btn.setChecked(True)
        self._scroll_btn.setObjectName("BtnSmall")
        self._scroll_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{P['cyan']};
                border:1px solid {P['cyan']}55; border-radius:3px;
                padding:2px 8px; font-size:10px;
            }}
            QPushButton:checked {{
                background:{P['cyan']}22;
            }}
        """)
        self._scroll_btn.toggled.connect(self._toggle_autoscroll)
        hl.addWidget(self._scroll_btn)

        # Copy all
        copy_btn = QPushButton("Copy All")
        copy_btn.setObjectName("BtnSmall")
        copy_btn.clicked.connect(self._copy_all)
        copy_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{P['text_sec']};
                border:1px solid {P['border']}; border-radius:3px;
                padding:2px 8px; font-size:10px;
            }}
            QPushButton:hover {{ color:{P['text']}; }}
        """)
        hl.addWidget(copy_btn)

        # Clear
        clr_btn = QPushButton("Clear")
        clr_btn.setObjectName("BtnSmall")
        clr_btn.clicked.connect(self.clear)
        clr_btn.setStyleSheet(f"""
            QPushButton {{
                background:transparent; color:{P['text_muted']};
                border:1px solid {P['border']}; border-radius:3px;
                padding:2px 8px; font-size:10px;
            }}
            QPushButton:hover {{ color:{P['red']}; border-color:{P['red']}55; }}
        """)
        hl.addWidget(clr_btn)
        return bar

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def append_line(self, text: str, color: Optional[str] = None) -> None:
        """Append a single line. Supports raw ANSI or explicit color."""
        cursor = self._edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)

        if color:
            fmt = QTextCharFormat()
            fmt.setForeground(QColor(color))
            chunks = [(text, fmt)]
        else:
            chunks = _parse_ansi(text)

        for plain, fmt in chunks:
            cursor.insertText(plain, fmt)

        # Newline
        nl_fmt = QTextCharFormat()
        cursor.insertText("\n", nl_fmt)

        self._line_count += 1
        if self._auto_scroll:
            self._edit.setTextCursor(cursor)
            self._edit.ensureCursorVisible()

    def append_html(self, html: str) -> None:
        cursor = self._edit.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertHtml(html + "<br/>")
        if self._auto_scroll:
            self._edit.setTextCursor(cursor)
            self._edit.ensureCursorVisible()

    def set_status(self, text: str) -> None:
        if hasattr(self, "_status_lbl"):
            self._status_lbl.setText(text)

    def clear(self) -> None:
        self._edit.clear()
        self._line_count = 0
        self.set_status("Cleared")

    def get_text(self) -> str:
        return self._edit.toPlainText()

    # ------------------------------------------------------------------
    # Convenience colour shortcuts
    # ------------------------------------------------------------------
    def info(self, msg: str)    -> None: self.append_line(f"[INFO] {msg}",    P["cyan"])
    def success(self, msg: str) -> None: self.append_line(f"[+] {msg}",       P["green"])
    def warning(self, msg: str) -> None: self.append_line(f"[!] {msg}",       P["orange"])
    def error(self, msg: str)   -> None: self.append_line(f"[ERROR] {msg}",   P["red"])
    def cmd(self, msg: str)     -> None: self.append_line(f"$ {msg}",         P["purple"])
    def separator(self)         -> None: self.append_line("─" * 60,            P["border"])

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _toggle_autoscroll(self, checked: bool) -> None:
        self._auto_scroll = checked
        label = "⬇ Auto-scroll ON" if checked else "⬇ Auto-scroll OFF"
        self._scroll_btn.setText(label)

    def _copy_all(self) -> None:
        from PyQt6.QtWidgets import QApplication
        QApplication.clipboard().setText(self._edit.toPlainText())
        self.set_status("Copied to clipboard")
