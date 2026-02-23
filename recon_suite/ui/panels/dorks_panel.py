"""
SwordSuite — Dork's Eye Panel
Google-dork query builder, DuckDuckGo search runner, results table.
"""
from __future__ import annotations

import threading
import webbrowser
from typing import Callable, List, Optional

from PyQt6.QtCore    import Qt, QThread, QTimer, pyqtSignal, QObject
from PyQt6.QtGui     import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QFrame,
    QHBoxLayout, QHeaderView, QLabel, QLineEdit,
    QPushButton, QSizePolicy, QSplitter, QTableWidget,
    QTableWidgetItem, QTreeWidget, QTreeWidgetItem,
    QVBoxLayout, QWidget, QTextEdit,
)

from recon_suite.core.dork_engine import (
    DORK_DB, SearchResult, build_google_url, build_bing_url,
    dork_for_target, search_ddg,
)
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.terminal    import TerminalWidget
from recon_suite.ui.widgets.form_widgets import RunStopBar, SectionHeader


# ---------------------------------------------------------------------------
# Worker thread for DuckDuckGo searches
# ---------------------------------------------------------------------------
class _SearchWorker(QObject):
    result_ready = pyqtSignal(list)    # List[SearchResult]
    log_line     = pyqtSignal(str)
    finished     = pyqtSignal()

    def __init__(self, queries: List[tuple[str, str]], max_per_query: int = 20):
        super().__init__()
        self._queries  = queries  # (dork_label, query_string)
        self._max      = max_per_query
        self._stop     = False

    def start_search(self) -> None:
        all_results: List[SearchResult] = []
        for label, query in self._queries:
            if self._stop:
                break
            self.log_line.emit(f"[DDG] [{label}] {query}")
            found = search_ddg(query, self._max, delay=1.5, progress_cb=self.log_line.emit)
            for r in found:
                r.dork = query
            all_results.extend(found)
            self.result_ready.emit(found)

        self.log_line.emit(f"[+] Search complete — {len(all_results)} total results.")
        self.finished.emit()

    def stop(self) -> None:
        self._stop = True


# ---------------------------------------------------------------------------
# Dork's Eye Panel
# ---------------------------------------------------------------------------
class DorksPanel(QWidget):
    # Signal: list of URLs to send to next tool
    send_to_katana = pyqtSignal(list)
    send_to_sqlmap = pyqtSignal(list)

    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate      = navigate_cb
        self._results:  List[SearchResult] = []
        self._worker:   Optional[_SearchWorker] = None
        self._thread:   Optional[QThread]       = None
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Top bar
        root.addWidget(self._build_topbar())

        # Main splitter: left config | right results
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        splitter.addWidget(self._build_left())
        splitter.addWidget(self._build_right())
        splitter.setSizes([320, 800])
        root.addWidget(splitter, 1)

    # ------------------------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        icon = QLabel("👁")
        icon.setStyleSheet(f"font-size:20px; color:{P['blue']};")
        title = QLabel("Dork's Eye")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        subtitle = QLabel("Google-dork query builder and search runner")
        subtitle.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")

        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(subtitle)
        hl.addStretch()

        # Target input in top bar
        hl.addWidget(QLabel("Target:"))
        self._target_input = QLineEdit()
        self._target_input.setPlaceholderText("example.com")
        self._target_input.setFixedWidth(220)
        hl.addWidget(self._target_input)

        return bar

    # ------------------------------------------------------------------
    def _build_left(self) -> QWidget:
        w = QWidget()
        w.setMaximumWidth(340)
        w.setStyleSheet(f"background:{P['bg0']}; border-right:1px solid {P['border']};")

        vl = QVBoxLayout(w)
        vl.setContentsMargins(12, 12, 12, 12)
        vl.setSpacing(10)

        # Search engine
        vl.addWidget(SectionHeader("Search Engine", P["blue"]))
        self._engine_combo = QComboBox()
        self._engine_combo.addItems(["DuckDuckGo (auto)", "Google (browser)", "Bing (browser)"])
        vl.addWidget(self._engine_combo)

        # Results per dork
        rl = QHBoxLayout()
        rl.addWidget(QLabel("Max results per dork:"))
        self._max_results = QComboBox()
        self._max_results.addItems(["10", "20", "30", "50"])
        self._max_results.setCurrentIndex(1)
        rl.addWidget(self._max_results)
        vl.addLayout(rl)

        # Dork category tree
        vl.addWidget(SectionHeader("Dork Categories", P["blue"]))

        self._dork_tree = QTreeWidget()
        self._dork_tree.setHeaderHidden(True)
        self._dork_tree.setRootIsDecorated(True)
        self._dork_tree.setMinimumHeight(260)

        for category, dorks in DORK_DB.items():
            cat_item = QTreeWidgetItem([category])
            cat_item.setFlags(cat_item.flags() | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsAutoTristate)
            cat_item.setCheckState(0, Qt.CheckState.Unchecked)
            for label, query in dorks:
                dork_item = QTreeWidgetItem([label])
                dork_item.setData(0, Qt.ItemDataRole.UserRole, query)
                dork_item.setFlags(dork_item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                dork_item.setCheckState(0, Qt.CheckState.Unchecked)
                dork_item.setToolTip(0, query)
                cat_item.addChild(dork_item)
            self._dork_tree.addTopLevelItem(cat_item)

        self._dork_tree.itemDoubleClicked.connect(self._preview_dork)
        vl.addWidget(self._dork_tree)

        # Select all / none
        sel_row = QHBoxLayout()
        all_btn  = QPushButton("Select All")
        none_btn = QPushButton("None")
        for b in (all_btn, none_btn):
            b.setObjectName("BtnSmall")
        all_btn.clicked.connect(lambda: self._set_all_checked(True))
        none_btn.clicked.connect(lambda: self._set_all_checked(False))
        sel_row.addWidget(all_btn)
        sel_row.addWidget(none_btn)
        sel_row.addStretch()
        vl.addLayout(sel_row)

        # Custom dork
        vl.addWidget(SectionHeader("Custom Dork", P["blue"]))
        self._custom_dork = QTextEdit()
        self._custom_dork.setPlaceholderText('inurl:login.php site:example.com\ninurl:admin intext:"password"')
        self._custom_dork.setFixedHeight(70)
        vl.addWidget(self._custom_dork)

        # Run / stop
        self._run_bar = RunStopBar("Search", "BtnPrimary")
        self._run_bar.run_clicked.connect(self._start_search)
        self._run_bar.stop_clicked.connect(self._stop_search)
        vl.addWidget(self._run_bar)

        vl.addStretch()
        return w

    # ------------------------------------------------------------------
    def _build_right(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{P['bg1']};")

        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Results toolbar
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet(f"background:{P['bg2']}; border-bottom:1px solid {P['border']};")
        bar_hl = QHBoxLayout(bar)
        bar_hl.setContentsMargins(12, 0, 12, 0)
        bar_hl.setSpacing(8)

        self._result_count = QLabel("0 results")
        self._result_count.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        bar_hl.addWidget(self._result_count)
        bar_hl.addStretch()

        # Filter
        self._filter_input = QLineEdit()
        self._filter_input.setPlaceholderText("Filter results…")
        self._filter_input.setFixedWidth(200)
        self._filter_input.textChanged.connect(self._apply_filter)
        bar_hl.addWidget(self._filter_input)

        # Actions
        for text, cb, obj in [
            ("Open Selected",  self._open_selected, "BtnSmall"),
            ("→ Katana",       self._send_katana,   "BtnSmall"),
            ("→ SQLMap",       self._send_sqlmap,   "BtnSmall"),
            ("Export",         self._export,        "BtnSmall"),
        ]:
            btn = QPushButton(text)
            btn.setObjectName(obj)
            btn.clicked.connect(cb)
            bar_hl.addWidget(btn)
        vl.addWidget(bar)

        # Split: table + terminal
        split2 = QSplitter(Qt.Orientation.Vertical)
        split2.setChildrenCollapsible(False)

        self._table = self._build_results_table()
        split2.addWidget(self._table)

        self._terminal = TerminalWidget(show_toolbar=True)
        self._terminal.setMinimumHeight(120)
        split2.addWidget(self._terminal)
        split2.setSizes([450, 180])

        vl.addWidget(split2, 1)
        return w

    def _build_results_table(self) -> QTableWidget:
        tbl = QTableWidget(0, 4)
        tbl.setHorizontalHeaderLabels(["URL", "Title", "Snippet", "Dork"])
        tbl.setAlternatingRowColors(True)
        tbl.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        tbl.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        tbl.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        tbl.setContextMenuPolicy(Qt.ContextMenuPolicy.ActionsContextMenu)

        from PyQt6.QtGui import QAction
        open_act = QAction("Open in Browser", tbl)
        open_act.triggered.connect(self._open_selected)
        katana_act = QAction("Send to Katana", tbl)
        katana_act.triggered.connect(self._send_katana)
        sqlmap_act = QAction("Send to SQLMap", tbl)
        sqlmap_act.triggered.connect(self._send_sqlmap)
        tbl.addAction(open_act)
        tbl.addAction(katana_act)
        tbl.addAction(sqlmap_act)
        return tbl

    # ------------------------------------------------------------------
    # Search logic
    # ------------------------------------------------------------------
    def _collect_queries(self) -> List[tuple[str, str]]:
        target = self._target_input.text().strip()
        queries: List[tuple[str, str]] = []

        # From tree
        root = self._dork_tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            for j in range(cat.childCount()):
                item = cat.child(j)
                if item.checkState(0) == Qt.CheckState.Checked:
                    raw = item.data(0, Qt.ItemDataRole.UserRole)
                    if raw:
                        queries.append((item.text(0), dork_for_target(raw, target)))

        # Custom dorks
        custom_text = self._custom_dork.toPlainText().strip()
        if custom_text:
            for line in custom_text.splitlines():
                line = line.strip()
                if line:
                    queries.append(("Custom", dork_for_target(line, target)))

        return queries

    def _start_search(self) -> None:
        queries = self._collect_queries()
        if not queries:
            self._terminal.warning("No dorks selected. Tick some categories or enter a custom dork.")
            return

        engine = self._engine_combo.currentText()
        max_r  = int(self._max_results.currentText())

        self._terminal.clear()
        self._terminal.info(f"Starting search: {len(queries)} dork(s) via {engine}")
        self._run_bar.set_running(True)

        if "Google" in engine:
            for label, q in queries:
                url = build_google_url(q)
                self._terminal.cmd(url)
                webbrowser.open(url)
            self._run_bar.set_running(False)
            return
        if "Bing" in engine:
            for label, q in queries:
                url = build_bing_url(q)
                self._terminal.cmd(url)
                webbrowser.open(url)
            self._run_bar.set_running(False)
            return

        # DuckDuckGo auto-search
        self._worker = _SearchWorker(queries, max_r)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._worker.log_line.connect(self._terminal.append_line)
        self._worker.result_ready.connect(self._add_results)
        self._worker.finished.connect(self._search_done)
        self._thread.started.connect(self._worker.start_search)
        self._thread.start()

    def _stop_search(self) -> None:
        if self._worker:
            self._worker.stop()
        self._terminal.warning("Search stopped by user.")
        self._run_bar.set_running(False)

    def _search_done(self) -> None:
        self._run_bar.set_running(False)
        self._terminal.success(f"Done — {len(self._results)} results total.")
        if self._thread:
            self._thread.quit()

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------
    def _add_results(self, results: List[SearchResult]) -> None:
        for r in results:
            self._results.append(r)
            self._insert_row(r)
        self._result_count.setText(f"{len(self._results)} results")

    def _insert_row(self, r: SearchResult) -> None:
        row = self._table.rowCount()
        self._table.insertRow(row)
        for col, text in enumerate([r.url, r.title, r.snippet, r.dork]):
            item = QTableWidgetItem(text)
            item.setData(Qt.ItemDataRole.UserRole, r)
            if col == 0:
                item.setForeground(QColor(P["cyan"]))
            self._table.setItem(row, col, item)

    def _apply_filter(self, text: str) -> None:
        text = text.lower()
        for row in range(self._table.rowCount()):
            url_item = self._table.item(row, 0)
            visible  = text in (url_item.text().lower() if url_item else "")
            self._table.setRowHidden(row, not visible and bool(text))

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _selected_urls(self) -> List[str]:
        seen: set[str] = set()
        urls = []
        for item in self._table.selectedItems():
            r = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(r, SearchResult) and r.url not in seen:
                seen.add(r.url)
                urls.append(r.url)
        return urls

    def _open_selected(self) -> None:
        for url in self._selected_urls():
            webbrowser.open(url)

    def _send_katana(self) -> None:
        urls = self._selected_urls() or [r.url for r in self._results]
        if urls:
            self.send_to_katana.emit(urls)
            self._navigate("katana")
            self._terminal.success(f"Sent {len(urls)} URL(s) to Katana.")

    def _send_sqlmap(self) -> None:
        urls = self._selected_urls() or [r.url for r in self._results]
        if urls:
            self.send_to_sqlmap.emit(urls)
            self._navigate("sqlmap")
            self._terminal.success(f"Sent {len(urls)} URL(s) to SQLMap.")

    def _export(self) -> None:
        from PyQt6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Export Dork Results", "dork_results.txt", "Text (*.txt);;JSON (*.json)")
        if not path:
            return
        with open(path, "w", encoding="utf-8") as f:
            if path.endswith(".json"):
                import json
                json.dump([{"url": r.url, "title": r.title, "snippet": r.snippet, "dork": r.dork} for r in self._results], f, indent=2)
            else:
                for r in self._results:
                    f.write(f"{r.url}\t{r.title}\t{r.dork}\n")
        self._terminal.success(f"Exported to {path}")

    def _preview_dork(self, item: QTreeWidgetItem, col: int) -> None:
        query = item.data(0, Qt.ItemDataRole.UserRole)
        if query:
            target = self._target_input.text().strip()
            self._terminal.info(f"Dork preview: {dork_for_target(query, target)}")

    def _set_all_checked(self, checked: bool) -> None:
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        root = self._dork_tree.invisibleRootItem()
        for i in range(root.childCount()):
            cat = root.child(i)
            cat.setCheckState(0, state)
            for j in range(cat.childCount()):
                cat.child(j).setCheckState(0, state)

    # ------------------------------------------------------------------
    # Public API (called from other panels / chain)
    # ------------------------------------------------------------------
    def set_target(self, target: str) -> None:
        self._target_input.setText(target)

    def get_result_urls(self) -> List[str]:
        return [r.url for r in self._results]
