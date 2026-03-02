"""
SwordSuite — SQLMap Panel
Full GUI covering sqlmap's most useful parameters.

Improvements over v1:
- Batch URL queue: test multiple URLs sequentially with progress tracking
- Improved output parser: catches technique, type, title, payload details
- Better DB tree: parses [*] database/table/column listings from sqlmap
- Structured dump viewer: renders sqlmap's ASCII tables properly
- Progress tracking: shows current URL index, test progress, ETA
- Queue management: add/remove/reorder URLs, skip current
"""
from __future__ import annotations

import re
from typing import Callable, List, Optional

from PyQt6.QtCore    import Qt, pyqtSignal
from PyQt6.QtGui     import QColor, QAction
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QTableWidget, QTableWidgetItem, QTabWidget, QTextEdit,
    QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from recon_suite.core.tool_runner import (
    TOOL_PATHS, ProcessRunner, build_sqlmap_cmd,
)
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.terminal    import TerminalWidget
from recon_suite.ui.widgets.form_widgets import (
    FormRow, LabeledSlider, MultiCheck, RunStopBar, SectionHeader,
)


# ---------------------------------------------------------------------------
# Regex patterns for sqlmap output parsing
# ---------------------------------------------------------------------------
_RE_PARAM_INJECTABLE = re.compile(
    r"Parameter:\s+(.+?)\s+\((.+?)\)"
)
_RE_TECHNIQUE = re.compile(
    r"Type:\s+(.+?)$", re.MULTILINE
)
_RE_TITLE = re.compile(
    r"Title:\s+(.+?)$", re.MULTILINE
)
_RE_PAYLOAD = re.compile(
    r"Payload:\s+(.+?)$", re.MULTILINE
)
_RE_DB_LISTING = re.compile(
    r"^\[\*\]\s+(.+)$", re.MULTILINE
)
_RE_PROGRESS = re.compile(
    r"\[INFO\]\s+testing\s+'(.+?)'",
)
_RE_PROGRESS_PCT = re.compile(
    r"(\d+)/(\d+)",
)
_RE_DBMS_BACKEND = re.compile(
    r"back-end DBMS:\s+(.+?)$", re.MULTILINE
)
_RE_TABLE_HEADER = re.compile(
    r"Database:\s+(.+?)$", re.MULTILINE
)
_RE_TABLE_LISTING = re.compile(
    r"^\[\d+\s+tables?\]$", re.MULTILINE
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
        # Batch queue state
        self._url_queue: List[str] = []
        self._queue_idx: int = -1
        self._current_url: str = ""
        # Parser state for multi-line injection blocks
        self._parse_buf: dict = {}
        self._in_injection_block: bool = False
        # DB tree tracking
        self._current_db_node: Optional[QTreeWidgetItem] = None
        self._current_tbl_node: Optional[QTreeWidgetItem] = None
        self._db_context: str = ""  # which db we're listing tables for
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

        # Target — single URL for manual entry
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

        # URL Queue
        vl.addWidget(SectionHeader("URL Queue (Batch)", P["purple"]))

        self._queue_list = QListWidget()
        self._queue_list.setMaximumHeight(120)
        self._queue_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self._queue_list.setStyleSheet(f"font-family:monospace; font-size:11px;")
        vl.addWidget(self._queue_list)

        q_btns = QHBoxLayout()
        q_btns.setSpacing(4)
        add_btn = QPushButton("Add URL")
        add_btn.setObjectName("BtnSmall")
        add_btn.clicked.connect(self._queue_add_url)
        remove_btn = QPushButton("Remove")
        remove_btn.setObjectName("BtnSmall")
        remove_btn.clicked.connect(self._queue_remove)
        clear_q_btn = QPushButton("Clear")
        clear_q_btn.setObjectName("BtnSmall")
        clear_q_btn.clicked.connect(self._queue_clear)
        q_btns.addWidget(add_btn)
        q_btns.addWidget(remove_btn)
        q_btns.addWidget(clear_q_btn)
        q_btns.addStretch()
        vl.addLayout(q_btns)

        self._queue_status = QLabel("Queue empty — single URL mode")
        self._queue_status.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
        vl.addWidget(self._queue_status)

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
            "Custom...",
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
        self._forms_cb   = QCheckBox("Parse forms  (--forms)")
        self._crawl_cb   = QCheckBox("Crawl site  (--crawl=2)")
        self._file_read  = QLineEdit()
        self._file_read.setPlaceholderText("/etc/passwd")
        self._file_write = QLineEdit()
        self._file_write.setPlaceholderText("/var/www/html/shell.php")
        self._file_dest  = QLineEdit()
        self._file_dest.setPlaceholderText("Remote file destination path")
        self._batch      = QCheckBox("Batch mode  (--batch)  -- non-interactive")
        self._fresh_queries=QCheckBox("Fresh queries  (--fresh-queries)")
        self._flush_session=QCheckBox("Flush session  (--flush-session)")

        self._batch.setChecked(True)
        for cb in (self._os_shell, self._sql_shell, self._forms_cb, self._crawl_cb,
                   self._batch, self._fresh_queries, self._flush_session):
            vl.addWidget(cb)
        vl.addWidget(FormRow("File read:", self._file_read))
        vl.addWidget(FormRow("File write:", self._file_write))
        vl.addWidget(FormRow("File dest:", self._file_dest))

        # Extra args
        vl.addWidget(SectionHeader("Extra Arguments", P["text_muted"]))
        self._extra_args = QLineEdit()
        self._extra_args.setPlaceholderText("--second-url=... --skip=...")
        vl.addWidget(self._extra_args)

        # Run bar
        self._run_bar = RunStopBar("Run SQLMap", "BtnPurple")
        self._run_bar.run_clicked.connect(self._start)
        self._run_bar.stop_clicked.connect(self._stop)
        vl.addWidget(self._run_bar)

        self._skip_btn = QPushButton("Skip Current URL →")
        self._skip_btn.setObjectName("BtnWarning")
        self._skip_btn.clicked.connect(self._skip_current)
        self._skip_btn.setVisible(False)
        vl.addWidget(self._skip_btn)

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

        # Queue progress bar
        self._queue_progress = QWidget()
        self._queue_progress.setFixedHeight(32)
        self._queue_progress.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        qp_hl = QHBoxLayout(self._queue_progress)
        qp_hl.setContentsMargins(12, 0, 12, 0)
        qp_hl.setSpacing(16)

        self._qp_label = QLabel("Queue: idle")
        self._qp_label.setStyleSheet(f"color:{P['purple']}; font-size:11px; font-weight:600;")
        self._qp_current = QLabel("")
        self._qp_current.setStyleSheet(f"color:{P['text_sec']}; font-size:11px; font-family:monospace;")
        self._qp_stats = QLabel("")
        self._qp_stats.setStyleSheet(f"color:{P['green']}; font-size:11px; font-weight:600;")

        qp_hl.addWidget(self._qp_label)
        qp_hl.addWidget(self._qp_current, 1)
        qp_hl.addWidget(self._qp_stats)
        self._queue_progress.setVisible(False)
        vl.addWidget(self._queue_progress)

        # Tabs: findings | output | dump
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

        export_btn = QPushButton("Export")
        export_btn.setObjectName("BtnSmall")
        export_btn.clicked.connect(self._export_findings)
        hdr.addWidget(export_btn)

        clear_btn = QPushButton("Clear")
        clear_btn.setObjectName("BtnSmall")
        clear_btn.clicked.connect(self._clear_findings)
        hdr.addWidget(clear_btn)
        vl.addLayout(hdr)

        self._findings_table = QTableWidget(0, 6)
        self._findings_table.setHorizontalHeaderLabels(
            ["URL", "Parameter", "Type", "Technique", "Payload", "DBMS"]
        )
        self._findings_table.setAlternatingRowColors(True)
        self._findings_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._findings_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hdr_view = self._findings_table.horizontalHeader()
        hdr_view.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        hdr_view.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        hdr_view.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        vl.addWidget(self._findings_table)

        # DB structure
        vl.addWidget(SectionHeader("Discovered Databases / Tables / Columns", P["purple"]))
        self._db_tree = QTreeWidget()
        self._db_tree.setHeaderLabels(["Name", "Type"])
        self._db_tree.setMaximumHeight(200)
        self._db_tree.setColumnWidth(0, 300)
        vl.addWidget(self._db_tree)
        return w

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

        hdr = QHBoxLayout()
        lbl = QLabel("Dumped table data appears here during --dump runs.")
        lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:12px;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        copy_btn = QPushButton("Copy All")
        copy_btn.setObjectName("BtnSmall")
        copy_btn.clicked.connect(self._copy_dump)
        clear_dump_btn = QPushButton("Clear")
        clear_dump_btn.setObjectName("BtnSmall")
        clear_dump_btn.clicked.connect(lambda: self._dump_table.setRowCount(0))
        hdr.addWidget(copy_btn)
        hdr.addWidget(clear_dump_btn)
        vl.addLayout(hdr)

        # Structured dump table instead of raw text
        self._dump_table = QTableWidget(0, 0)
        self._dump_table.setAlternatingRowColors(True)
        self._dump_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._dump_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._dump_table.setStyleSheet(f"font-family:monospace; font-size:12px;")
        vl.addWidget(self._dump_table)

        # Raw dump text below
        self._dump_raw = QTextEdit()
        self._dump_raw.setReadOnly(True)
        self._dump_raw.setMaximumHeight(150)
        self._dump_raw.setStyleSheet(f"font-family:monospace; font-size:11px; color:{P['text_sec']};")
        self._dump_raw.setPlaceholderText("Raw sqlmap dump output...")
        vl.addWidget(self._dump_raw)
        return w

    # ------------------------------------------------------------------
    # Queue management
    # ------------------------------------------------------------------
    def _queue_add_url(self) -> None:
        url = self._url_input.text().strip()
        if url:
            self._queue_list.addItem(url)
            self._url_input.clear()
            self._update_queue_status()

    def _queue_remove(self) -> None:
        for item in self._queue_list.selectedItems():
            self._queue_list.takeItem(self._queue_list.row(item))
        self._update_queue_status()

    def _queue_clear(self) -> None:
        self._queue_list.clear()
        self._update_queue_status()

    def _update_queue_status(self) -> None:
        count = self._queue_list.count()
        if count == 0:
            self._queue_status.setText("Queue empty -- single URL mode")
            self._queue_status.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
        else:
            self._queue_status.setText(f"{count} URL(s) queued for batch testing")
            self._queue_status.setStyleSheet(f"color:{P['purple']}; font-size:11px; font-weight:600;")

    def _get_queue_urls(self) -> List[str]:
        return [self._queue_list.item(i).text() for i in range(self._queue_list.count())]

    # ------------------------------------------------------------------
    # Start / stop / queue runner
    # ------------------------------------------------------------------
    def _build_extra_args(self) -> str:
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
        if self._forms_cb.isChecked():
            extra += " --forms"
        if self._crawl_cb.isChecked():
            extra += " --crawl=2"
        return extra

    def _build_cmd_for_url(self, url: str) -> tuple:
        technique_codes = self._techniques.checked_codes()
        dbms = self._dbms.currentText()
        if dbms == "Auto-detect":
            dbms = ""

        tamper = [t.strip() for t in self._tamper.currentText().split(",") if t.strip()]
        user_agent_choice = self._user_agent.currentText()
        random_agent = "Random" in user_agent_choice

        return build_sqlmap_cmd(
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
            extra_args   = self._build_extra_args(),
        )

    def _start(self) -> None:
        # Determine URL list: queue or single URL
        queue_urls = self._get_queue_urls()
        single_url = self._url_input.text().strip()

        if queue_urls:
            self._url_queue = list(queue_urls)
        elif single_url:
            self._url_queue = [single_url]
        else:
            self._terminal.warning("No target URL specified.")
            return

        if not TOOL_PATHS.get("sqlmap"):
            self._terminal.error(
                "sqlmap not found in PATH.\n"
                "Install: apt install sqlmap  OR  pip install sqlmap"
            )
            return

        self._terminal.clear()
        self._queue_idx = -1
        self._run_bar.set_running(True)
        self._skip_btn.setVisible(len(self._url_queue) > 1)
        self._queue_progress.setVisible(True)

        if len(self._url_queue) > 1:
            self._terminal.info(f"Batch mode: testing {len(self._url_queue)} URL(s) sequentially.")
            self._terminal.separator()

        self._run_next_in_queue()

    def _run_next_in_queue(self) -> None:
        self._queue_idx += 1

        if self._queue_idx >= len(self._url_queue):
            self._batch_complete()
            return

        url = self._url_queue[self._queue_idx]
        self._current_url = url
        total = len(self._url_queue)
        idx = self._queue_idx + 1

        # Reset parser state
        self._parse_buf = {}
        self._in_injection_block = False

        self._qp_label.setText(f"URL {idx}/{total}")
        self._qp_current.setText(url[:80])
        self._qp_stats.setText(f"{len(self._findings)} injection(s) so far")

        # Highlight current in queue list
        for i in range(self._queue_list.count()):
            item = self._queue_list.item(i)
            if i == self._queue_idx:
                item.setForeground(QColor(P["orange"]))
            elif i < self._queue_idx:
                item.setForeground(QColor(P["text_muted"]))
            else:
                item.setForeground(QColor(P["text"]))

        if len(self._url_queue) > 1:
            self._terminal.info(f"[{idx}/{total}] Testing: {url}")
            self._terminal.separator()

        cmd, args = self._build_cmd_for_url(url)
        self._terminal.cmd(f"{cmd} {' '.join(args)}")

        self._runner = ProcessRunner()
        self._runner.stdout_line.connect(self._handle_output)
        self._runner.stderr_line.connect(lambda l: self._terminal.append_line(l, P["text_sec"]))
        self._runner.finished_sig.connect(self._on_single_done)
        self._runner.error_sig.connect(self._terminal.error)
        self._runner.run(cmd, args)

    def _on_single_done(self, code: int) -> None:
        # Flush any pending injection block
        self._flush_injection_block()

        url = self._current_url
        if code == 0:
            self._terminal.success(f"Completed: {url}")
        else:
            self._terminal.warning(f"Finished with exit code {code}: {url}")

        self._qp_stats.setText(f"{len(self._findings)} injection(s) so far")

        # Continue to next URL in queue
        self._run_next_in_queue()

    def _batch_complete(self) -> None:
        total = len(self._url_queue)
        found = len(self._findings)

        self._terminal.separator()
        self._terminal.success(
            f"Batch complete: {total} URL(s) tested, {found} injection(s) found."
        )
        self._run_bar.set_status(f"{found} injection(s) across {total} URL(s).", P["green"])
        self._run_bar.set_running(False)
        self._skip_btn.setVisible(False)
        self._qp_label.setText(f"Done: {total} URLs")
        self._qp_stats.setText(f"{found} injection(s)")

    def _stop(self) -> None:
        self._url_queue = []  # Clear remaining queue
        if self._runner:
            self._runner.kill()
        self._terminal.warning("Stopped by user.")
        self._run_bar.set_running(False)
        self._skip_btn.setVisible(False)

    def _skip_current(self) -> None:
        """Kill current URL's sqlmap process and advance to next in queue."""
        if self._runner:
            self._runner.kill()
        self._terminal.warning(f"Skipped: {self._current_url}")

    # ------------------------------------------------------------------
    # Output parsing — much improved
    # ------------------------------------------------------------------
    def _handle_output(self, line: str) -> None:
        # Colourize and route to parsers
        if "injectable" in line or "identified the following" in line:
            self._terminal.append_line(line, P["green"])
            self._parse_injection_start(line)
        elif line.strip().startswith("Type:"):
            self._terminal.append_line(line, P["green"])
            self._parse_buf["type"] = line.strip().replace("Type: ", "", 1)
        elif line.strip().startswith("Title:"):
            self._terminal.append_line(line, P["green"])
            self._parse_buf["title"] = line.strip().replace("Title: ", "", 1)
        elif line.strip().startswith("Payload:"):
            self._terminal.append_line(line, P["green"])
            self._parse_buf["payload"] = line.strip().replace("Payload: ", "", 1)
            # Payload is typically the last field in an injection block
            self._flush_injection_block()
        elif line.strip().startswith("Parameter:"):
            self._terminal.append_line(line, P["green"])
            self._parse_param_line(line)
        elif "back-end DBMS:" in line:
            self._terminal.append_line(line, P["purple"])
            m = _RE_DBMS_BACKEND.search(line)
            if m:
                self._parse_buf["dbms"] = m.group(1).strip()
        elif any(k in line for k in ("[WARNING]", "[ERROR]")):
            color = P["orange"] if "[WARNING]" in line else P["red"]
            self._terminal.append_line(line, color)
        elif "[INFO]" in line:
            self._terminal.append_line(line, P["cyan"])
            self._parse_info_line(line)
        elif line.startswith("[*]"):
            self._terminal.append_line(line, P["purple"])
            self._parse_listing(line)
        elif "---" in line and line.strip().startswith("+"):
            # Table border: +---+---+
            self._terminal.append_line(line, P["text_muted"])
            self._dump_raw.append(line)
        elif "|" in line and line.strip().startswith("|"):
            # Table data row
            self._terminal.append_line(line, P["text_sec"])
            self._parse_dump_row(line)
        elif "Database:" in line:
            self._terminal.append_line(line, P["purple"])
            m = _RE_TABLE_HEADER.search(line)
            if m:
                self._db_context = m.group(1).strip()
        else:
            self._terminal.append_line(line)

    def _parse_param_line(self, line: str) -> None:
        m = _RE_PARAM_INJECTABLE.search(line)
        if m:
            self._parse_buf["param"] = m.group(1).strip()
            self._parse_buf["method"] = m.group(2).strip()
            self._in_injection_block = True

    def _parse_injection_start(self, line: str) -> None:
        self._in_injection_block = True

    def _flush_injection_block(self) -> None:
        """Commit accumulated injection details as a finding row."""
        buf = self._parse_buf
        if not buf.get("param") and not buf.get("type"):
            return

        param    = buf.get("param", "?")
        inj_type = buf.get("type", "")
        title    = buf.get("title", "")
        payload  = buf.get("payload", "")
        dbms     = buf.get("dbms", "")
        method   = buf.get("method", "")

        # Add to findings
        finding = {
            "url":     self._current_url,
            "param":   param,
            "type":    inj_type,
            "title":   title,
            "payload": payload,
            "dbms":    dbms,
            "method":  method,
        }
        self._findings.append(finding)

        # Insert table row
        row = self._findings_table.rowCount()
        self._findings_table.insertRow(row)
        for col, val in enumerate([
            self._current_url, param, inj_type, title, payload, dbms
        ]):
            item = QTableWidgetItem(val)
            if col == 0:
                item.setForeground(QColor(P["cyan"]))
                item.setToolTip(self._current_url)
            elif col in (2, 3):
                item.setForeground(QColor(P["green"]))
            elif col == 4:
                item.setForeground(QColor(P["orange"]))
            self._findings_table.setItem(row, col, item)

        self._finding_count.setText(f"{len(self._findings)} injection(s) found")
        self._qp_stats.setText(f"{len(self._findings)} injection(s) so far")

        # Keep param/dbms for subsequent type/title/payload in same parameter block
        # but clear the per-technique fields
        self._parse_buf = {
            "param": buf.get("param", ""),
            "method": buf.get("method", ""),
            "dbms": buf.get("dbms", ""),
        }

    def _parse_info_line(self, line: str) -> None:
        """Parse [INFO] lines for DB/table/column discovery."""
        lower = line.lower()
        if "available databases" in lower:
            self._db_context = "__dbs__"
        elif "fetched tables" in lower or "tables found" in lower:
            pass  # tables will come as [*] listings

    def _parse_listing(self, line: str) -> None:
        """Parse [*] lines — database names, table names, column names."""
        text = line.replace("[*]", "").strip()
        if not text:
            return

        # Add to DB tree
        if self._db_context == "__dbs__":
            # This is a database name
            node = self._find_or_add_db_node(text)
            self._current_db_node = node
            self._current_tbl_node = None
        elif self._db_context:
            # Could be a table under current DB context
            if self._current_db_node is None:
                self._current_db_node = self._find_or_add_db_node(self._db_context)
            # Check if it's a table name
            tbl_node = QTreeWidgetItem([text, "table"])
            tbl_node.setForeground(0, QColor(P["cyan"]))
            tbl_node.setForeground(1, QColor(P["text_muted"]))
            self._current_db_node.addChild(tbl_node)
            self._current_tbl_node = tbl_node
            self._db_tree.expandItem(self._current_db_node)

    def _find_or_add_db_node(self, db_name: str) -> QTreeWidgetItem:
        for i in range(self._db_tree.topLevelItemCount()):
            node = self._db_tree.topLevelItem(i)
            if node.text(0) == db_name:
                return node
        node = QTreeWidgetItem([db_name, "database"])
        node.setForeground(0, QColor(P["purple"]))
        node.setForeground(1, QColor(P["text_muted"]))
        self._db_tree.addTopLevelItem(node)
        return node

    # ------------------------------------------------------------------
    # Dump parser — structured table rendering
    # ------------------------------------------------------------------
    def _parse_dump_row(self, line: str) -> None:
        self._dump_raw.append(line)
        # Parse pipe-delimited row: | col1 | col2 | col3 |
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if not cells:
            return

        # If table has no columns yet, treat this as header
        if self._dump_table.columnCount() == 0 or self._dump_table.rowCount() == 0:
            # Check if this looks like a header (no previous data rows)
            if self._dump_table.columnCount() != len(cells):
                self._dump_table.setColumnCount(len(cells))
                self._dump_table.setHorizontalHeaderLabels(cells)
                for i in range(len(cells)):
                    self._dump_table.horizontalHeader().setSectionResizeMode(
                        i, QHeaderView.ResizeMode.Stretch
                    )
                return

        # Data row
        row = self._dump_table.rowCount()
        self._dump_table.insertRow(row)
        for col, val in enumerate(cells):
            if col < self._dump_table.columnCount():
                self._dump_table.setItem(row, col, QTableWidgetItem(val))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _clear_findings(self) -> None:
        self._findings_table.setRowCount(0)
        self._findings.clear()
        self._db_tree.clear()
        self._dump_table.setRowCount(0)
        self._dump_table.setColumnCount(0)
        self._dump_raw.clear()
        self._finding_count.setText("0 injections found")
        self._current_db_node = None
        self._current_tbl_node = None
        self._db_context = ""

    def _export_findings(self) -> None:
        if not self._findings:
            self._terminal.warning("No findings to export.")
            return
        from PyQt6.QtWidgets import QFileDialog
        import json
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Findings", "sqlmap_findings.json",
            "JSON (*.json);;CSV (*.csv)"
        )
        if not path:
            return
        if path.endswith(".csv"):
            import csv
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["url", "param", "type", "title", "payload", "dbms", "method"])
                writer.writeheader()
                writer.writerows(self._findings)
        else:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._findings, f, indent=2)
        self._terminal.success(f"Exported {len(self._findings)} finding(s) to {path}")

    def _copy_dump(self) -> None:
        from PyQt6.QtWidgets import QApplication
        text = self._dump_raw.toPlainText()
        if text:
            QApplication.clipboard().setText(text)
            self._terminal.info("Dump data copied to clipboard.")

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
        """Populate the batch queue with URLs from other panels."""
        if not urls:
            return
        # Put first URL in the input field
        self._url_input.setText(urls[0])
        # If multiple, populate the queue
        if len(urls) > 1:
            self._queue_list.clear()
            for url in urls:
                self._queue_list.addItem(url)
            self._update_queue_status()
            self._terminal.info(f"Received {len(urls)} URL(s) — added to batch queue.")
