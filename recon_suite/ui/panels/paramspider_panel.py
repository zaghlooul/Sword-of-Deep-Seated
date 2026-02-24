"""
SwordSuite — ParamSpider Panel
GUI for extracting parameterised URLs from web archives.
"""
from __future__ import annotations

from typing import Callable, List, Optional
from urllib.parse import urlparse, parse_qs

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QSpinBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from recon_suite.core.tool_runner import (
    TOOL_PATHS, ProcessRunner, build_paramspider_cmd,
)
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.terminal    import TerminalWidget
from recon_suite.ui.widgets.form_widgets import (
    FormRow, RunStopBar, SectionHeader,
)


class ParamSpiderPanel(QWidget):
    send_to_sqlmap = pyqtSignal(list)

    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate  = navigate_cb
        self._results: List[dict] = []
        self._runner:  Optional[ProcessRunner] = None
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_config())
        splitter.addWidget(self._build_results())
        splitter.setSizes([300, 900])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        icon = QLabel("P")
        icon.setStyleSheet(f"font-size:20px; font-weight:700; color:{P['pink']};")
        title = QLabel("ParamSpider")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        subtitle = QLabel("Extract parameterised URLs from web archives")
        subtitle.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        hl.addStretch()

        status_color = P["green"] if TOOL_PATHS.get("paramspider") else P["red"]
        status_txt   = "● Installed" if TOOL_PATHS.get("paramspider") else "● Not Found"
        status_lbl   = QLabel(status_txt)
        status_lbl.setStyleSheet(f"color:{status_color}; font-size:11px; font-weight:600;")
        hl.addWidget(status_lbl)
        return bar

    # ------------------------------------------------------------------
    def _build_config(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumWidth(310)

        w = QWidget()
        w.setStyleSheet(f"background:{P['bg0']}; border-right:1px solid {P['border']};")
        scroll.setWidget(w)

        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 14, 14, 14)
        vl.setSpacing(12)

        # Target domain
        vl.addWidget(SectionHeader("Target Domain", P["pink"]))
        self._domain_input = QLineEdit()
        self._domain_input.setPlaceholderText("example.com")
        vl.addWidget(FormRow("Domain:", self._domain_input, "Target domain to mine from web archives"))

        # Options
        vl.addWidget(SectionHeader("Options", P["pink"]))

        self._exclude = QLineEdit()
        self._exclude.setText("png,jpg,gif,jpeg,swf,woff,svg,pdf,css")
        self._exclude.setPlaceholderText("Extensions to exclude")
        vl.addWidget(FormRow("Exclude ext:", self._exclude, "Comma-separated file extensions to skip"))

        self._placeholder = QLineEdit()
        self._placeholder.setText("FUZZ")
        self._placeholder.setPlaceholderText("FUZZ")
        vl.addWidget(FormRow("Placeholder:", self._placeholder, "Placeholder value for parameters"))

        self._subs = QCheckBox("Include subdomains  (-s)")
        vl.addWidget(self._subs)

        self._workers = QSpinBox()
        self._workers.setRange(0, 50)
        self._workers.setValue(0)
        self._workers.setSpecialValueText("Default")
        vl.addWidget(FormRow("Workers:", self._workers, "Number of parallel workers (0 = default)"))

        # Output
        vl.addWidget(SectionHeader("Output", P["pink"]))
        self._output_file = QLineEdit()
        self._output_file.setPlaceholderText("paramspider_output.txt  (optional)")
        vl.addWidget(FormRow("Output file:", self._output_file))

        # Run bar
        self._run_bar = RunStopBar("Run ParamSpider", "BtnWarning")
        self._run_bar.run_clicked.connect(self._start)
        self._run_bar.stop_clicked.connect(self._stop)
        vl.addWidget(self._run_bar)

        # Command preview
        vl.addWidget(SectionHeader("Command Preview", P["text_muted"]))
        self._cmd_preview = QTextEdit()
        self._cmd_preview.setReadOnly(True)
        self._cmd_preview.setFixedHeight(56)
        self._cmd_preview.setStyleSheet(f"font-family:monospace; font-size:11px; color:{P['orange']};")
        vl.addWidget(self._cmd_preview)

        # Update preview on change
        self._domain_input.textChanged.connect(self._update_cmd_preview)
        self._exclude.textChanged.connect(self._update_cmd_preview)
        self._subs.toggled.connect(self._update_cmd_preview)
        self._update_cmd_preview()

        vl.addStretch()
        return scroll

    # ------------------------------------------------------------------
    def _build_results(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{P['bg1']};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Toolbar
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{P['bg2']}; border-bottom:1px solid {P['border']};")
        bar_hl = QHBoxLayout(bar)
        bar_hl.setContentsMargins(12, 0, 12, 0)
        bar_hl.setSpacing(8)

        self._url_count = QLabel("0 parameterised URLs")
        self._url_count.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        bar_hl.addWidget(self._url_count)
        bar_hl.addStretch()

        self._url_filter = QLineEdit()
        self._url_filter.setPlaceholderText("Filter…")
        self._url_filter.setFixedWidth(180)
        self._url_filter.textChanged.connect(self._apply_filter)
        bar_hl.addWidget(self._url_filter)

        for text, cb in [("→ SQLMap", self._send_sqlmap), ("Export", self._export), ("Clear", self._clear_results)]:
            btn = QPushButton(text)
            btn.setObjectName("BtnSmall")
            btn.clicked.connect(cb)
            bar_hl.addWidget(btn)

        vl.addWidget(bar)

        # Results table + terminal
        split = QSplitter(Qt.Orientation.Vertical)
        split.setChildrenCollapsible(False)

        self._table = self._build_table()
        split.addWidget(self._table)

        self._terminal = TerminalWidget()
        self._terminal.setMinimumHeight(120)
        split.addWidget(self._terminal)
        split.setSizes([450, 200])

        vl.addWidget(split, 1)
        return w

    def _build_table(self) -> QTableWidget:
        tbl = QTableWidget(0, 3)
        tbl.setHorizontalHeaderLabels(["URL", "Parameter", "Domain"])
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)

        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        send_act = QAction("Send to SQLMap", tbl)
        send_act.triggered.connect(self._send_sqlmap)
        tbl.addAction(send_act)
        return tbl

    # ------------------------------------------------------------------
    def _start(self) -> None:
        domain = self._domain_input.text().strip()
        if not domain:
            self._terminal.warning("No target domain specified.")
            return

        if not TOOL_PATHS.get("paramspider"):
            self._terminal.error(
                "paramspider not found in PATH.\n"
                "Install: pip install paramspider"
            )
            return

        cmd, args = build_paramspider_cmd(
            domain       = domain,
            exclude      = self._exclude.text().strip(),
            placeholder  = self._placeholder.text().strip(),
            subs         = self._subs.isChecked(),
            workers      = self._workers.value(),
            output_file  = self._output_file.text().strip(),
        )

        self._terminal.clear()
        self._terminal.cmd(f"{cmd} {' '.join(args)}")
        self._clear_results()

        self._runner = ProcessRunner()
        self._runner.stdout_line.connect(self._handle_output)
        self._runner.stderr_line.connect(lambda l: self._terminal.append_line(l, P["red"]))
        self._runner.finished_sig.connect(self._done)
        self._runner.error_sig.connect(self._terminal.error)
        self._runner.run(cmd, args)
        self._run_bar.set_running(True)

    def _stop(self) -> None:
        if self._runner:
            self._runner.kill()
        self._terminal.warning("Stopped by user.")
        self._run_bar.set_running(False)

    def _done(self, code: int) -> None:
        msg = "ParamSpider complete." if code == 0 else f"Finished with exit code {code}."
        self._terminal.success(msg)
        self._run_bar.set_status(f"{len(self._results)} parameterised URLs found.", P["green"])
        self._run_bar.set_running(False)

    # ------------------------------------------------------------------
    def _handle_output(self, line: str) -> None:
        self._terminal.append_line(line)
        result = self._parse_line(line)
        if result:
            self._results.append(result)
            self._insert_row(result)
            self._url_count.setText(f"{len(self._results)} parameterised URLs")

    def _parse_line(self, line: str) -> Optional[dict]:
        line = line.strip()
        if not line or not line.startswith("http"):
            return None
        url = line.split()[0]
        # Extract parameter names and domain
        try:
            parsed = urlparse(url)
            params = list(parse_qs(parsed.query).keys())
            return {
                "url": url,
                "param": ", ".join(params) if params else "",
                "domain": parsed.netloc,
            }
        except Exception:
            return {"url": url, "param": "", "domain": ""}

    def _insert_row(self, result: dict) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)

        for col, key in enumerate(["url", "param", "domain"]):
            item = QTableWidgetItem(str(result.get(key, "")))
            item.setData(Qt.ItemDataRole.UserRole, result)
            if col == 0:
                item.setForeground(QColor(P["pink"]))
            elif col == 1:
                item.setForeground(QColor(P["orange"]))
            self._table.setItem(row, col, item)

    def _apply_filter(self) -> None:
        text = self._url_filter.text().lower()
        for row in range(self._table.rowCount()):
            url_item = self._table.item(row, 0)
            if not url_item:
                continue
            visible = (not text) or (text in url_item.text().lower())
            self._table.setRowHidden(row, not visible)

    def _clear_results(self) -> None:
        self._table.setRowCount(0)
        self._results.clear()
        self._url_count.setText("0 parameterised URLs")

    def _send_sqlmap(self) -> None:
        urls = self._selected_urls()
        if not urls:
            urls = [r["url"] for r in self._results if r.get("url")]
        if urls:
            self.send_to_sqlmap.emit(urls)
            self._navigate("sqlmap")
            self._terminal.success(f"Sent {len(urls)} URL(s) to SQLMap.")

    def _selected_urls(self) -> List[str]:
        seen: set = set()
        urls = []
        for item in self._table.selectedItems():
            r = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(r, dict) and r.get("url") not in seen:
                seen.add(r["url"])
                urls.append(r["url"])
        return urls

    def _export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export URLs", "paramspider_results.txt", "Text (*.txt)")
        if path:
            with open(path, "w") as f:
                for r in self._results:
                    f.write(f"{r.get('url', '')}\n")
            self._terminal.success(f"Exported to {path}")

    def _update_cmd_preview(self) -> None:
        domain = self._domain_input.text().strip() or "example.com"
        cmd, args = build_paramspider_cmd(
            domain=domain,
            exclude=self._exclude.text().strip(),
            subs=self._subs.isChecked(),
        )
        self._cmd_preview.setPlainText(f"{cmd} {' '.join(args)}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_domain(self, domain: str) -> None:
        self._domain_input.setText(domain)

    def set_domains(self, domains: List[str]) -> None:
        if domains:
            self._domain_input.setText(domains[0])

    def get_urls(self) -> List[str]:
        return [r["url"] for r in self._results if r.get("url")]
