"""
SwordSuite — SQLMap Panel
Full GUI covering sqlmap's most useful parameters.
"""
from __future__ import annotations

from typing import Callable, List, Optional

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QVBoxLayout, QWidget,
)

from recon_suite.core.tool_runner import (
    TOOL_PATHS, ProcessRunner, build_sqlmap_cmd,
)
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.terminal    import TerminalWidget
from recon_suite.ui.widgets.form_widgets import (
    FormRow, LabeledSlider, MultiCheck, RunStopBar, SectionHeader,
)


class SqlmapPanel(QWidget):
    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate  = navigate_cb
        self._findings: List[dict] = []
        self._runner:   Optional[ProcessRunner] = None
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
        splitter.setSizes([340, 860])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        icon = QLabel("💉")
        icon.setStyleSheet("font-size:20px;")
        title = QLabel("SQLMap")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        sub = QLabel("Automated SQL injection detection and exploitation")
        sub.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch()

        color = P["green"] if TOOL_PATHS.get("sqlmap") else P["red"]
        txt   = "● Installed" if TOOL_PATHS.get("sqlmap") else "● Not Found"
        s_lbl = QLabel(txt)
        s_lbl.setStyleSheet(f"color:{color}; font-size:11px; font-weight:600;")
        hl.addWidget(s_lbl)
        return bar

    # ------------------------------------------------------------------
    def _build_config(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumWidth(360)

        w = QWidget()
        w.setStyleSheet(f"background:{P['bg0']}; border-right:1px solid {P['border']};")
        scroll.setWidget(w)

        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 14, 14, 14)
        vl.setSpacing(12)

        # Target
        vl.addWidget(SectionHeader("Target", P["purple"]))

        self._url_input = QLineEdit()
        self._url_input.setPlaceholderText("http://example.com/page?id=1")
        vl.addWidget(FormRow("URL:", self._url_input, "Target URL with injectable parameter"))

        self._method = QComboBox()
        self._method.addItems(["GET", "POST", "PUT", "DELETE"])
        vl.addWidget(FormRow("Method:", self._method))

        self._data = QLineEdit()
        self._data.setPlaceholderText("id=1&name=test  (POST body data)")
        vl.addWidget(FormRow("Data:", self._data))

        self._cookie = QLineEdit()
        self._cookie.setPlaceholderText("PHPSESSID=abc123; auth=xyz")
        vl.addWidget(FormRow("Cookies:", self._cookie))

        self._param = QLineEdit()
        self._param.setPlaceholderText("id  (leave blank to test all)")
        vl.addWidget(FormRow("Parameter:", self._param, "Specific parameter to test"))

        # Request options
        vl.addWidget(SectionHeader("Request Options", P["purple"]))

        self._headers = QTextEdit()
        self._headers.setPlaceholderText("X-Forwarded-For: 127.0.0.1\nReferer: https://example.com")
        self._headers.setFixedHeight(56)
        vl.addWidget(FormRow("Headers:", self._headers))

        self._user_agent = QComboBox()
        self._user_agent.addItems([
            "Random (--random-agent)",
            "Default sqlmap",
            "Chrome",
            "Firefox",
            "Custom…",
        ])
        vl.addWidget(FormRow("User-Agent:", self._user_agent))

        self._proxy = QLineEdit()
        self._proxy.setPlaceholderText("http://127.0.0.1:8080")
        vl.addWidget(FormRow("Proxy:", self._proxy))

        self._tor_cb = QCheckBox("Route through Tor  (--tor)")
        vl.addWidget(self._tor_cb)

        self._delay = LabeledSlider(0, 10, 0)
        vl.addWidget(FormRow("Delay (s):", self._delay, "Delay between requests"))

        self._threads = LabeledSlider(1, 10, 5)
        vl.addWidget(FormRow("Threads:", self._threads))

        # Detection
        vl.addWidget(SectionHeader("Detection Tuning", P["purple"]))

        self._level = LabeledSlider(1, 5, 1)
        vl.addWidget(FormRow("Level:", self._level, "Tests to perform (1=fast, 5=thorough)"))

        self._risk = LabeledSlider(1, 3, 1)
        vl.addWidget(FormRow("Risk:", self._risk, "Chance of corrupting data (1=safe, 3=aggressive)"))

        vl.addWidget(QLabel("Techniques:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        self._techniques = MultiCheck([
            ("B", "Boolean", True),
            ("E", "Error",   True),
            ("U", "Union",   True),
            ("S", "Stacked", True),
            ("T", "Time",    False),
            ("Q", "Inline",  False),
        ])
        vl.addWidget(self._techniques)

        self._dbms = QComboBox()
        self._dbms.addItems([
            "Auto-detect", "MySQL", "PostgreSQL", "Microsoft SQL Server",
            "Oracle", "SQLite", "Access", "Firebird", "SAP MaxDB",
            "Sybase", "IBM DB2",
        ])
        vl.addWidget(FormRow("DBMS:", self._dbms))

        # WAF bypass
        vl.addWidget(SectionHeader("WAF / Evasion", P["purple"]))

        self._tamper = QComboBox()
        self._tamper.setEditable(True)
        self._tamper.addItems([
            "",
            "space2comment",
            "between",
            "charencode",
            "charunicodeencode",
            "equaltolike",
            "greatest",
            "ifnull2ifisnull",
            "modsecurityzeroversioned",
            "percentage",
            "randomcase",
            "space2hash",
            "unionalltounion",
            "unmagicquotes",
        ])
        self._tamper.setPlaceholderText("Tamper script(s)")
        vl.addWidget(FormRow("Tamper:", self._tamper))

        self._prefix = QLineEdit()
        self._prefix.setPlaceholderText("Custom payload prefix")
        vl.addWidget(FormRow("Prefix:", self._prefix))

        self._suffix = QLineEdit()
        self._suffix.setPlaceholderText("Custom payload suffix")
        vl.addWidget(FormRow("Suffix:", self._suffix))

        # Enumeration actions
        vl.addWidget(SectionHeader("Enumeration", P["purple"]))

        self._get_dbs    = QCheckBox("Enumerate databases  (--dbs)")
        self._get_tables = QCheckBox("Enumerate tables  (--tables)")
        self._get_cols   = QCheckBox("Enumerate columns  (--columns)")
        self._dump       = QCheckBox("Dump data  (--dump)")
        self._current_db = QCheckBox("Current database  (--current-db)")
        self._current_user=QCheckBox("Current user  (--current-user)")
        self._is_dba     = QCheckBox("Check DBA  (--is-dba)")

        for cb in (self._get_dbs, self._get_tables, self._get_cols,
                   self._dump, self._current_db, self._current_user, self._is_dba):
            vl.addWidget(cb)

        # Specific DB/table
        self._db_name    = QLineEdit()
        self._db_name.setPlaceholderText("Schema name (for --tables)")
        vl.addWidget(FormRow("Database:", self._db_name))

        self._tbl_name   = QLineEdit()
        self._tbl_name.setPlaceholderText("Table name (for --dump)")
        vl.addWidget(FormRow("Table:", self._tbl_name))

        # Advanced
        vl.addWidget(SectionHeader("Advanced", P["purple"]))

        self._os_shell   = QCheckBox("OS shell  (--os-shell)")
        self._sql_shell  = QCheckBox("SQL shell  (--sql-shell)")
        self._file_read  = QLineEdit()
        self._file_read.setPlaceholderText("/etc/passwd")
        self._file_write = QLineEdit()
        self._file_write.setPlaceholderText("/var/www/html/shell.php")
        self._file_dest  = QLineEdit()
        self._file_dest.setPlaceholderText("Remote file destination path")
        self._batch      = QCheckBox("Batch mode  (--batch)  — non-interactive")
        self._fresh_queries=QCheckBox("Fresh queries  (--fresh-queries)")
        self._flush_session=QCheckBox("Flush session  (--flush-session)")

        self._batch.setChecked(True)
        for cb in (self._os_shell, self._sql_shell, self._batch, self._fresh_queries, self._flush_session):
            vl.addWidget(cb)
        vl.addWidget(FormRow("File read:", self._file_read))
        vl.addWidget(FormRow("File write:", self._file_write))
        vl.addWidget(FormRow("File dest:", self._file_dest))

        # Extra args
        vl.addWidget(SectionHeader("Extra Arguments", P["text_muted"]))
        self._extra_args = QLineEdit()
        self._extra_args.setPlaceholderText("--forms --crawl=2 ...")
        vl.addWidget(self._extra_args)

        # Run bar
        self._run_bar = RunStopBar("Run SQLMap", "BtnPurple")
        self._run_bar.run_clicked.connect(self._start)
        self._run_bar.stop_clicked.connect(self._stop)
        vl.addWidget(self._run_bar)

        # Command preview
        vl.addWidget(SectionHeader("Command Preview", P["text_muted"]))
        self._cmd_preview = QTextEdit()
        self._cmd_preview.setReadOnly(True)
        self._cmd_preview.setFixedHeight(72)
        self._cmd_preview.setStyleSheet(f"font-family:monospace; font-size:11px; color:{P['orange']};")
        vl.addWidget(self._cmd_preview)

        # Hook up preview
        for sig in (self._url_input.textChanged, self._level.valueChanged,
                    self._risk.valueChanged, self._get_dbs.toggled):
            sig.connect(self._update_preview)
        self._update_preview()

        vl.addStretch()
        return scroll

    # ------------------------------------------------------------------
    def _build_results(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{P['bg1']};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Tabs: findings | output
        tabs = QTabWidget()
        tabs.setStyleSheet(f"background:{P['bg1']};")
        tabs.addTab(self._build_findings_tab(), "Findings")
        tabs.addTab(self._build_output_tab(),   "Live Output")
        tabs.addTab(self._build_dump_tab(),      "Dump Viewer")
        vl.addWidget(tabs, 1)
        return w

    def _build_findings_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(8)

        hdr = QHBoxLayout()
        self._finding_count = QLabel("0 injections found")
        self._finding_count.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hdr.addWidget(self._finding_count)
        hdr.addStretch()
        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("BtnSmall")
        clear_btn.clicked.connect(self._clear_findings)
        hdr.addWidget(clear_btn)
        vl.addLayout(hdr)

        self._findings_table = QTableWidget(0, 5)
        self._findings_table.setHorizontalHeaderLabels(
            ["Parameter", "Technique", "Payload", "URL", "Confidence"]
        )
        self._findings_table.setAlternatingRowColors(True)
        self._findings_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._findings_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr_view = self._findings_table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        vl.addWidget(self._findings_table)

        # DB structure
        vl.addWidget(SectionHeader("Discovered Databases / Tables", P["purple"]))
        self._db_tree = self._build_db_tree()
        vl.addWidget(self._db_tree)
        return w

    def _build_db_tree(self):
        from PyQt6.QtWidgets import QTreeWidget
        tree = QTreeWidget()
        tree.setHeaderLabels(["Database / Table / Column"])
        tree.setMaximumHeight(160)
        return tree

    def _build_output_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        self._terminal = TerminalWidget()
        vl.addWidget(self._terminal)
        return w

    def _build_dump_tab(self) -> QWidget:
        w = QWidget()
        vl = QVBoxLayout(w)
        vl.setContentsMargins(8, 8, 8, 8)
        vl.setSpacing(6)

        lbl = QLabel("Dumped table data will appear here during / after a --dump run.")
        lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:12px;")
        vl.addWidget(lbl)

        self._dump_view = QTextEdit()
        self._dump_view.setReadOnly(True)
        self._dump_view.setStyleSheet(f"font-family:monospace; font-size:12px;")
        vl.addWidget(self._dump_view)
        return w

    # ------------------------------------------------------------------
    def _start(self) -> None:
        url = self._url_input.text().strip()
        if not url:
            self._terminal.warning("No target URL specified.")
            return

        if not TOOL_PATHS.get("sqlmap"):
            self._terminal.error(
                "sqlmap not found in PATH.\n"
                "Install: apt install sqlmap  OR  pip install sqlmap"
            )
            return

        technique_codes = self._techniques.checked_codes()
        dbms = self._dbms.currentText()
        if dbms == "Auto-detect":
            dbms = ""

        tamper = [t.strip() for t in self._tamper.currentText().split(",") if t.strip()]

        extra = self._extra_args.text().strip()
        if self._file_read.text().strip():
            extra += f" --file-read={self._file_read.text().strip()}"
        if self._file_write.text().strip() and self._file_dest.text().strip():
            extra += f" --file-write={self._file_write.text().strip()} --file-dest={self._file_dest.text().strip()}"
        if self._db_name.text().strip():
            extra += f" -D {self._db_name.text().strip()}"
        if self._tbl_name.text().strip():
            extra += f" -T {self._tbl_name.text().strip()}"
        if self._param.text().strip():
            extra += f" -p {self._param.text().strip()}"
        if self._prefix.text().strip():
            extra += f" --prefix={self._prefix.text().strip()}"
        if self._suffix.text().strip():
            extra += f" --suffix={self._suffix.text().strip()}"
        if self._current_db.isChecked():
            extra += " --current-db"
        if self._current_user.isChecked():
            extra += " --current-user"
        if self._is_dba.isChecked():
            extra += " --is-dba"
        if self._get_cols.isChecked():
            extra += " --columns"
        if self._fresh_queries.isChecked():
            extra += " --fresh-queries"
        if self._flush_session.isChecked():
            extra += " --flush-session"

        user_agent_choice = self._user_agent.currentText()
        random_agent = "Random" in user_agent_choice

        cmd, args = build_sqlmap_cmd(
            url          = url,
            method       = self._method.currentText(),
            data         = self._data.text().strip(),
            cookie       = self._cookie.text().strip(),
            random_agent = random_agent,
            level        = self._level.value,
            risk         = self._risk.value,
            techniques   = technique_codes,
            dbms         = dbms,
            proxy        = self._proxy.text().strip(),
            tor          = self._tor_cb.isChecked(),
            tamper       = tamper or None,
            get_dbs      = self._get_dbs.isChecked(),
            get_tables   = self._get_tables.isChecked(),
            dump         = self._dump.isChecked(),
            os_shell     = self._os_shell.isChecked(),
            sql_shell    = self._sql_shell.isChecked(),
            batch        = self._batch.isChecked(),
            threads      = self._threads.value,
            extra_args   = extra,
        )

        self._terminal.clear()
        self._terminal.cmd(f"{cmd} {' '.join(args)}")
        self._run_bar.set_running(True)

        self._runner = ProcessRunner()
        self._runner.stdout_line.connect(self._handle_output)
        self._runner.stderr_line.connect(lambda l: self._terminal.append_line(l, P["text_sec"]))
        self._runner.finished_sig.connect(self._done)
        self._runner.error_sig.connect(self._terminal.error)
        self._runner.run(cmd, args)

    def _stop(self) -> None:
        if self._runner:
            self._runner.kill()
        self._terminal.warning("Stopped by user.")
        self._run_bar.set_running(False)

    def _done(self, code: int) -> None:
        msg = f"SQLMap finished (exit={code})."
        color = P["green"] if code == 0 else P["orange"]
        self._terminal.append_line(f"[+] {msg}", color)
        self._run_bar.set_status(f"{len(self._findings)} injection(s) found.", color)
        self._run_bar.set_running(False)

    # ------------------------------------------------------------------
    def _handle_output(self, line: str) -> None:
        # Colourize based on sqlmap keywords
        if any(k in line for k in ("injectable", "identified the following", "Parameter")):
            self._terminal.append_line(line, P["green"])
            self._parse_injection(line)
        elif any(k in line for k in ("[WARNING]", "[ERROR]")):
            color = P["orange"] if "[WARNING]" in line else P["red"]
            self._terminal.append_line(line, color)
        elif "[INFO]" in line:
            self._terminal.append_line(line, P["cyan"])
        elif "available databases" in line.lower() or "database:" in line.lower():
            self._terminal.append_line(line, P["purple"])
            self._parse_db_info(line)
        elif "|" in line and len(line) > 10:
            # Table dump row
            self._terminal.append_line(line, P["text_sec"])
            self._dump_view.append(line)
        else:
            self._terminal.append_line(line)

    def _parse_injection(self, line: str) -> None:
        import re
        # Look for "Parameter: X (GET)" style
        m = re.search(r"Parameter: (.+?) \((.+?)\)", line)
        if m:
            row = self._findings_table.rowCount()
            self._findings_table.insertRow(row)
            self._findings_table.setItem(row, 0, QTableWidgetItem(m.group(1)))
            self._findings_table.setItem(row, 1, QTableWidgetItem(""))
            self._findings_table.setItem(row, 2, QTableWidgetItem(""))
            self._findings_table.setItem(row, 3, QTableWidgetItem(self._url_input.text()))
            self._findings_table.setItem(row, 4, QTableWidgetItem("Confirmed"))
            for c in range(5):
                if self._findings_table.item(row, c):
                    self._findings_table.item(row, c).setForeground(QColor(P["green"]))
            self._findings.append({"param": m.group(1), "url": self._url_input.text()})
            self._finding_count.setText(f"{len(self._findings)} injection(s) found")

    def _parse_db_info(self, line: str) -> None:
        import re
        m = re.search(r"\[.*?\] \[INFO\] .*?'(.+?)'", line)
        if m:
            db_name = m.group(1)
            # Check if already exists in tree
            for i in range(self._db_tree.topLevelItemCount()):
                if self._db_tree.topLevelItem(i).text(0) == db_name:
                    return
            from PyQt6.QtWidgets import QTreeWidgetItem
            item = QTreeWidgetItem([db_name])
            item.setForeground(0, QColor(P["purple"]))
            self._db_tree.addTopLevelItem(item)

    def _clear_findings(self) -> None:
        self._findings_table.setRowCount(0)
        self._findings.clear()
        self._db_tree.clear()
        self._dump_view.clear()
        self._finding_count.setText("0 injections found")

    def _update_preview(self) -> None:
        url = self._url_input.text().strip() or "http://target.com/page?id=1"
        cmd, args = build_sqlmap_cmd(
            url=url,
            level=self._level.value,
            risk=self._risk.value,
            get_dbs=self._get_dbs.isChecked(),
            batch=True,
        )
        self._cmd_preview.setPlainText(f"{cmd} {' '.join(args)}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def set_target(self, url: str) -> None:
        self._url_input.setText(url)

    def set_targets(self, urls: List[str]) -> None:
        """Set the first URL; store the rest as extra info."""
        if urls:
            self._url_input.setText(urls[0])
