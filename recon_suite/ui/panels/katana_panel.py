"""
SwordSuite — Katana Crawler Panel
Full GUI for ProjectDiscovery's Katana web crawler.

Improvements over v1:
- Timeout, exclude-ext, match-regex, proxy all wired to command builder
- Scope control: include/exclude domain fields
- Endpoint deduplication with counter
- Parameter extraction + highlighting for injectable URLs
- Progress indicator (unique URLs found, dupes skipped)
- JSON/CSV/TXT export
- JSON output mode (-jsonl) for richer endpoint parsing
- "Has params" filter to quickly find injectable endpoints
"""
from __future__ import annotations

import json
import csv
import io
from typing import Callable, List, Optional
from urllib.parse import urlparse, parse_qs

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame,
    QGroupBox, QHBoxLayout, QHeaderView, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QSpinBox, QTableWidget, QTableWidgetItem,
    QTextEdit, QVBoxLayout, QWidget,
)

from recon_suite.core.tool_runner import (
    TOOL_PATHS, ProcessRunner, build_katana_cmd,
)
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.terminal    import TerminalWidget
from recon_suite.ui.widgets.form_widgets import (
    FormRow, LabeledSlider, RunStopBar, SectionHeader,
)


# Endpoint type colours
_TYPE_COLORS = {
    "endpoint": P["cyan"],
    "form":     P["orange"],
    "js":       P["yellow"] if "yellow" in P else "#ffd740",
    "file":     P["purple"],
    "redirect": P["text_sec"],
}


def _extract_params(url: str) -> str:
    """Extract query parameter names from a URL."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        return ", ".join(sorted(params.keys())) if params else ""
    except Exception:
        return ""


def _normalize_url(url: str) -> str:
    """Normalize URL for dedup: strip fragment, sort params."""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        sorted_query = "&".join(
            f"{k}={','.join(sorted(v))}"
            for k, v in sorted(params.items())
        )
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{sorted_query}" if sorted_query else f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    except Exception:
        return url


class KatanaPanel(QWidget):
    send_to_sqlmap = pyqtSignal(list)

    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate  = navigate_cb
        self._endpoints: List[dict] = []
        self._seen_urls: set[str] = set()
        self._dupes_skipped: int = 0
        self._runner:    Optional[ProcessRunner] = None
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

        icon = QLabel("⚔")
        icon.setStyleSheet(f"font-size:20px; color:{P['cyan']};")
        title = QLabel("Katana")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        subtitle = QLabel("High-performance web crawler and spider")
        subtitle.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        hl.addStretch()

        status_color = P["green"] if TOOL_PATHS.get("katana") else P["red"]
        status_txt   = "● Installed" if TOOL_PATHS.get("katana") else "● Not Found"
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

        # Targets
        vl.addWidget(SectionHeader("Target URLs", P["cyan"]))
        self._urls_input = QTextEdit()
        self._urls_input.setPlaceholderText("https://example.com\nhttps://target.com/app")
        self._urls_input.setFixedHeight(80)
        vl.addWidget(self._urls_input)

        # Crawl settings
        vl.addWidget(SectionHeader("Crawl Settings", P["cyan"]))

        self._depth = LabeledSlider(1, 10, 3)
        vl.addWidget(FormRow("Depth:", self._depth, "How deep to follow links"))

        self._concurrency = LabeledSlider(1, 50, 10)
        vl.addWidget(FormRow("Concurrency:", self._concurrency, "Parallel requests"))

        self._rate_limit  = QSpinBox()
        self._rate_limit.setRange(10, 1000)
        self._rate_limit.setValue(150)
        self._rate_limit.setSuffix(" req/s")
        vl.addWidget(FormRow("Rate Limit:", self._rate_limit, "Max requests per second"))

        self._timeout = QSpinBox()
        self._timeout.setRange(5, 120)
        self._timeout.setValue(15)
        self._timeout.setSuffix(" s")
        vl.addWidget(FormRow("Timeout:", self._timeout, "Per-request timeout"))

        # Options
        vl.addWidget(SectionHeader("Options", P["cyan"]))

        self._js_crawl    = QCheckBox("JavaScript crawling  (-jc)")
        self._headless    = QCheckBox("Headless browser  (-headless)")
        self._form_extract= QCheckBox("Form extraction  (-form-extraction)")
        self._known_files = QCheckBox("Known files  (-kf all)")
        self._passive     = QCheckBox("Passive mode  (-ps)")

        self._js_crawl.setChecked(True)
        self._form_extract.setChecked(True)
        self._known_files.setChecked(True)

        for cb in (self._js_crawl, self._headless, self._form_extract,
                   self._known_files, self._passive):
            vl.addWidget(cb)

        # Scope control
        vl.addWidget(SectionHeader("Scope Control", P["cyan"]))

        self._scope_in = QLineEdit()
        self._scope_in.setPlaceholderText("example.com, sub.example.com")
        self._scope_in.setToolTip("Crawl-scope: only follow links matching these domains (comma-separated)")
        vl.addWidget(FormRow("In scope:", self._scope_in, "Only crawl these domains (-cs)"))

        self._scope_out = QLineEdit()
        self._scope_out.setPlaceholderText("logout.example.com, cdn.example.com")
        self._scope_out.setToolTip("Out-of-scope: never follow links to these domains")
        vl.addWidget(FormRow("Exclude:", self._scope_out, "Never crawl these domains (-cos)"))

        # HTTP
        vl.addWidget(SectionHeader("HTTP Options", P["cyan"]))

        self._cookie = QLineEdit()
        self._cookie.setPlaceholderText("name=value; session=abc")
        vl.addWidget(FormRow("Cookies:", self._cookie))

        self._headers = QTextEdit()
        self._headers.setPlaceholderText("X-Custom-Header: value\nAuthorization: Bearer token")
        self._headers.setFixedHeight(60)
        vl.addWidget(FormRow("Headers:", self._headers))

        self._proxy = QLineEdit()
        self._proxy.setPlaceholderText("http://127.0.0.1:8080")
        vl.addWidget(FormRow("Proxy:", self._proxy))

        # Filters
        vl.addWidget(SectionHeader("Output Filters", P["cyan"]))

        self._filter_ext = QLineEdit()
        self._filter_ext.setPlaceholderText("png,jpg,css,ico (exclude)")
        vl.addWidget(FormRow("Exclude ext:", self._filter_ext, "File extensions to exclude (-extension-filter)"))

        self._match_regex = QLineEdit()
        self._match_regex.setPlaceholderText(".*\\.php\\?.*  (regex)")
        vl.addWidget(FormRow("Match regex:", self._match_regex, "Only include URLs matching regex (-match-regex)"))

        # Output file
        vl.addWidget(SectionHeader("Output", P["cyan"]))
        self._output_file = QLineEdit()
        self._output_file.setPlaceholderText("katana_output.txt  (optional)")
        vl.addWidget(FormRow("Output file:", self._output_file))

        # Run bar
        self._run_bar = RunStopBar("Start Crawl", "BtnPrimary")
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
        for sig in (self._urls_input.textChanged, self._depth.valueChanged,
                    self._js_crawl.toggled, self._form_extract.toggled,
                    self._known_files.toggled, self._headless.toggled,
                    self._passive.toggled):
            sig.connect(self._update_cmd_preview)
        self._filter_ext.textChanged.connect(self._update_cmd_preview)
        self._match_regex.textChanged.connect(self._update_cmd_preview)
        self._scope_in.textChanged.connect(self._update_cmd_preview)
        self._scope_out.textChanged.connect(self._update_cmd_preview)
        self._proxy.textChanged.connect(self._update_cmd_preview)
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

        # Progress bar
        self._progress_bar = QWidget()
        self._progress_bar.setFixedHeight(32)
        self._progress_bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        prog_hl = QHBoxLayout(self._progress_bar)
        prog_hl.setContentsMargins(12, 0, 12, 0)
        prog_hl.setSpacing(16)

        self._prog_unique = QLabel("0 unique")
        self._prog_unique.setStyleSheet(f"color:{P['cyan']}; font-size:11px; font-weight:600;")
        self._prog_dupes = QLabel("0 dupes skipped")
        self._prog_dupes.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
        self._prog_params = QLabel("0 with params")
        self._prog_params.setStyleSheet(f"color:{P['orange']}; font-size:11px; font-weight:600;")
        self._prog_forms = QLabel("0 forms")
        self._prog_forms.setStyleSheet(f"color:{P['green']}; font-size:11px; font-weight:600;")

        prog_hl.addWidget(self._prog_unique)
        prog_hl.addWidget(self._prog_dupes)
        prog_hl.addWidget(self._prog_params)
        prog_hl.addWidget(self._prog_forms)
        prog_hl.addStretch()

        self._progress_bar.setVisible(False)
        vl.addWidget(self._progress_bar)

        # Toolbar
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{P['bg2']}; border-bottom:1px solid {P['border']};")
        bar_hl = QHBoxLayout(bar)
        bar_hl.setContentsMargins(12, 0, 12, 0)
        bar_hl.setSpacing(8)

        self._ep_count = QLabel("0 endpoints")
        self._ep_count.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        bar_hl.addWidget(self._ep_count)
        bar_hl.addStretch()

        # Type filter
        self._type_filter = QComboBox()
        self._type_filter.addItems(["All types", "endpoint", "form", "js", "file", "Has params"])
        self._type_filter.currentTextChanged.connect(self._apply_filter)
        bar_hl.addWidget(QLabel("Show:"))
        bar_hl.addWidget(self._type_filter)

        self._url_filter = QLineEdit()
        self._url_filter.setPlaceholderText("Filter...")
        self._url_filter.setFixedWidth(180)
        self._url_filter.textChanged.connect(self._apply_filter)
        bar_hl.addWidget(self._url_filter)

        for text, cb, obj_name in [
            ("→ SQLMap (params)", self._send_sqlmap_params, "BtnSmall"),
            ("→ SQLMap (all)",    self._send_sqlmap,        "BtnSmall"),
            ("Export",            self._export,             "BtnSmall"),
            ("Clear",             self._clear_results,      "BtnSmall"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(obj_name)
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
        tbl = QTableWidget(0, 5)
        tbl.setHorizontalHeaderLabels(["Type", "Method", "URL", "Params", "Domain"])
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        tbl.setSortingEnabled(True)

        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)
        send_act = QAction("Send to SQLMap", tbl)
        send_act.triggered.connect(self._send_sqlmap)
        send_params_act = QAction("Send parameterised to SQLMap", tbl)
        send_params_act.triggered.connect(self._send_sqlmap_params)
        copy_act = QAction("Copy URL", tbl)
        copy_act.triggered.connect(self._copy_selected_urls)
        tbl.addAction(send_act)
        tbl.addAction(send_params_act)
        tbl.addAction(copy_act)
        return tbl

    # ------------------------------------------------------------------
    def _get_cmd_kwargs(self) -> dict:
        """Build the kwargs dict from current UI state — used by both _start and _update_cmd_preview."""
        urls = [u.strip() for u in self._urls_input.toPlainText().splitlines() if u.strip()]

        extra_headers: dict = {}
        for line in self._headers.toPlainText().strip().splitlines():
            if ":" in line:
                k, _, v = line.partition(":")
                extra_headers[k.strip()] = v.strip()

        scope_in_text = self._scope_in.text().strip()
        scope_in = [d.strip() for d in scope_in_text.split(",") if d.strip()] if scope_in_text else None

        scope_out_text = self._scope_out.text().strip()
        scope_out = [d.strip() for d in scope_out_text.split(",") if d.strip()] if scope_out_text else None

        return dict(
            urls           = urls,
            depth          = self._depth.value,
            concurrency    = self._concurrency.value,
            rate_limit     = self._rate_limit.value(),
            js_crawl       = self._js_crawl.isChecked(),
            headless       = self._headless.isChecked(),
            form_extract   = self._form_extract.isChecked(),
            known_files    = self._known_files.isChecked(),
            output_file    = self._output_file.text().strip(),
            extra_headers  = extra_headers or None,
            cookies        = self._cookie.text().strip(),
            passive        = self._passive.isChecked(),
            timeout        = self._timeout.value(),
            exclude_ext    = self._filter_ext.text().strip(),
            match_regex    = self._match_regex.text().strip(),
            scope_domains      = scope_in,
            out_scope_domains  = scope_out,
            proxy          = self._proxy.text().strip(),
            json_output    = True,
        )

    def _start(self) -> None:
        kwargs = self._get_cmd_kwargs()
        if not kwargs["urls"]:
            self._terminal.warning("No target URLs specified.")
            return

        if not TOOL_PATHS.get("katana"):
            self._terminal.error(
                "katana not found in PATH.\n"
                "Install: go install github.com/projectdiscovery/katana/cmd/katana@latest"
            )
            return

        cmd, args = build_katana_cmd(**kwargs)

        self._terminal.clear()
        self._terminal.cmd(f"{cmd} {' '.join(args)}")
        self._clear_results()
        self._progress_bar.setVisible(True)

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
        msg = "Crawl complete." if code == 0 else f"Finished with exit code {code}."
        self._terminal.success(msg)
        param_count = sum(1 for ep in self._endpoints if ep.get("params"))
        summary = (
            f"{len(self._endpoints)} unique endpoints, "
            f"{param_count} with params, "
            f"{self._dupes_skipped} dupes skipped."
        )
        self._terminal.info(summary)
        self._run_bar.set_status(summary, P["green"])
        self._run_bar.set_running(False)

    # ------------------------------------------------------------------
    def _handle_output(self, line: str) -> None:
        self._terminal.append_line(line)
        ep = self._parse_endpoint(line)
        if ep:
            # Deduplication
            norm = _normalize_url(ep["url"])
            if norm in self._seen_urls:
                self._dupes_skipped += 1
                self._prog_dupes.setText(f"{self._dupes_skipped} dupes skipped")
                return

            self._seen_urls.add(norm)
            self._endpoints.append(ep)
            self._insert_row(ep)
            self._update_progress()

    def _parse_endpoint(self, line: str) -> Optional[dict]:
        """Parse katana output lines — prefers JSON, falls back to plain URL."""
        line = line.strip()
        if not line:
            return None

        # Katana JSONL output: {"timestamp":"...", "request":{...}, "response":{...}, ...}
        if line.startswith("{"):
            try:
                d = json.loads(line)
                url = d.get("request", {}).get("endpoint", "") or d.get("endpoint", "")
                if not url:
                    return None
                method = d.get("request", {}).get("method", "GET") or d.get("method", "GET")
                tag = d.get("request", {}).get("tag", "") or d.get("tag", "endpoint")
                kind = tag if tag else "endpoint"
                params = _extract_params(url)
                domain = urlparse(url).netloc if url.startswith("http") else ""
                return {
                    "url":    url,
                    "method": method,
                    "kind":   kind,
                    "params": params,
                    "domain": domain,
                }
            except (json.JSONDecodeError, AttributeError):
                pass

        # Plain URL output (non-JSON mode or fallback)
        if line.startswith("http"):
            url = line.split()[0]
            kind = "endpoint"
            if url.endswith((".js", ".mjs")):
                kind = "js"
            elif any(url.endswith(e) for e in (".pdf", ".zip", ".tar", ".gz", ".sql", ".bak")):
                kind = "file"
            params = _extract_params(url)
            domain = urlparse(url).netloc if url.startswith("http") else ""
            return {"url": url, "method": "GET", "kind": kind, "params": params, "domain": domain}

        return None

    def _insert_row(self, ep: dict) -> None:
        self._table.setSortingEnabled(False)
        row = self._table.rowCount()
        self._table.insertRow(row)
        color = _TYPE_COLORS.get(ep.get("kind", "endpoint"), P["text"])

        for col, key in enumerate(["kind", "method", "url", "params", "domain"]):
            val = str(ep.get(key, ""))
            item = QTableWidgetItem(val)
            item.setData(Qt.ItemDataRole.UserRole, ep)
            if col == 0:
                item.setForeground(QColor(color))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            elif col == 2:
                item.setForeground(QColor(P["cyan"]))
            elif col == 3 and val:
                # Highlight parameterised URLs in orange
                item.setForeground(QColor(P["orange"]))
                item.setToolTip(f"Parameters: {val}")
            elif col == 4:
                item.setForeground(QColor(P["text_muted"]))
            self._table.setItem(row, col, item)
        self._table.setSortingEnabled(True)

    def _update_progress(self) -> None:
        total = len(self._endpoints)
        param_count = sum(1 for ep in self._endpoints if ep.get("params"))
        form_count = sum(1 for ep in self._endpoints if ep.get("kind") == "form")

        self._ep_count.setText(f"{total} endpoints")
        self._prog_unique.setText(f"{total} unique")
        self._prog_params.setText(f"{param_count} with params")
        self._prog_forms.setText(f"{form_count} forms")

    def _apply_filter(self) -> None:
        text      = self._url_filter.text().lower()
        type_filt = self._type_filter.currentText()

        for row in range(self._table.rowCount()):
            url_item = self._table.item(row, 2)
            if not url_item:
                continue
            kind_item   = self._table.item(row, 0)
            params_item = self._table.item(row, 3)
            domain_item = self._table.item(row, 4)
            url  = url_item.text().lower()

            # Type filter
            if type_filt == "Has params":
                type_ok = bool(params_item and params_item.text())
            elif type_filt == "All types":
                type_ok = True
            else:
                type_ok = kind_item and kind_item.text() == type_filt

            # Text filter — searches URL, params, and domain
            if text:
                text_ok = (
                    text in url
                    or (params_item and text in params_item.text().lower())
                    or (domain_item and text in domain_item.text().lower())
                )
            else:
                text_ok = True

            self._table.setRowHidden(row, not (type_ok and text_ok))

    def _clear_results(self) -> None:
        self._table.setRowCount(0)
        self._endpoints.clear()
        self._seen_urls.clear()
        self._dupes_skipped = 0
        self._ep_count.setText("0 endpoints")
        self._prog_unique.setText("0 unique")
        self._prog_dupes.setText("0 dupes skipped")
        self._prog_params.setText("0 with params")
        self._prog_forms.setText("0 forms")

    def _send_sqlmap(self) -> None:
        urls = self._selected_urls()
        if not urls:
            urls = [ep["url"] for ep in self._endpoints if ep.get("url")]
        if urls:
            self.send_to_sqlmap.emit(urls)
            self._navigate("sqlmap")
            self._terminal.success(f"Sent {len(urls)} URL(s) to SQLMap.")

    def _send_sqlmap_params(self) -> None:
        """Send only parameterised URLs to SQLMap — the ones most likely injectable."""
        urls = self._selected_urls()
        if urls:
            # From selection, filter to only those with params
            urls = [u for u in urls if "?" in u]
        if not urls:
            urls = [ep["url"] for ep in self._endpoints if ep.get("params")]
        if urls:
            self.send_to_sqlmap.emit(urls)
            self._navigate("sqlmap")
            self._terminal.success(f"Sent {len(urls)} parameterised URL(s) to SQLMap.")
        else:
            self._terminal.warning("No parameterised URLs found to send.")

    def _selected_urls(self) -> List[str]:
        seen: set = set()
        urls = []
        for item in self._table.selectedItems():
            ep = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(ep, dict) and ep.get("url") not in seen:
                seen.add(ep["url"])
                urls.append(ep["url"])
        return urls

    def _copy_selected_urls(self) -> None:
        urls = self._selected_urls()
        if urls:
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText("\n".join(urls))
            self._terminal.info(f"Copied {len(urls)} URL(s) to clipboard.")

    def _export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Endpoints", "katana_results.json",
            "JSON (*.json);;CSV (*.csv);;Text (*.txt)"
        )
        if not path:
            return

        if path.endswith(".json"):
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._endpoints, f, indent=2)
        elif path.endswith(".csv"):
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["url", "method", "kind", "params", "domain"])
                writer.writeheader()
                writer.writerows(self._endpoints)
        else:
            with open(path, "w", encoding="utf-8") as f:
                for ep in self._endpoints:
                    f.write(f"{ep.get('method','GET')} {ep.get('url','')}\n")

        self._terminal.success(f"Exported {len(self._endpoints)} endpoints to {path}")

    def _update_cmd_preview(self) -> None:
        kwargs = self._get_cmd_kwargs()
        if not kwargs["urls"]:
            self._cmd_preview.setPlainText("katana -u <URL> ...")
            return
        # Limit URL count in preview for readability
        kwargs["urls"] = kwargs["urls"][:2]
        cmd, args = build_katana_cmd(**kwargs)
        self._cmd_preview.setPlainText(f"{cmd} {' '.join(args)}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_targets(self, urls: List[str]) -> None:
        self._urls_input.setPlainText("\n".join(urls))

    def get_endpoints(self) -> List[str]:
        return [ep["url"] for ep in self._endpoints if ep.get("url")]

    def get_parameterised_endpoints(self) -> List[str]:
        return [ep["url"] for ep in self._endpoints if ep.get("params")]
