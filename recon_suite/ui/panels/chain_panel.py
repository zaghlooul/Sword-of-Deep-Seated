"""
SwordSuite — Chain Panel
Visual pipeline: Dork's Eye → Katana → SQLMap in one automated flow.
"""
from __future__ import annotations

from enum import Enum
from typing import Callable, List, Optional

from PyQt6.QtCore    import Qt, QThread, pyqtSignal, QObject, QTimer
from PyQt6.QtGui     import QColor, QFont
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QFrame, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QScrollArea, QSizePolicy,
    QSplitter, QTextEdit, QVBoxLayout, QWidget,
)

from recon_suite.core.dork_engine  import DORK_DB, dork_for_target, search_ddg
from recon_suite.core.session      import Session
from recon_suite.core.tool_runner  import TOOL_PATHS, ProcessRunner, build_katana_cmd, build_paramspider_cmd, build_sqlmap_cmd
from recon_suite.styles.theme      import P
from recon_suite.ui.widgets.terminal     import TerminalWidget
from recon_suite.ui.widgets.form_widgets import LabeledSlider, RunStopBar, SectionHeader


# ---------------------------------------------------------------------------
# Step state
# ---------------------------------------------------------------------------
class StepState(Enum):
    IDLE    = "idle"
    RUNNING = "running"
    DONE    = "done"
    ERROR   = "error"
    SKIPPED = "skipped"


_STATE_COLORS = {
    StepState.IDLE:    P["text_muted"],
    StepState.RUNNING: P["orange"],
    StepState.DONE:    P["green"],
    StepState.ERROR:   P["red"],
    StepState.SKIPPED: P["text_muted"],
}

_STATE_ICONS = {
    StepState.IDLE:    "○",
    StepState.RUNNING: "◉",
    StepState.DONE:    "●",
    StepState.ERROR:   "✕",
    StepState.SKIPPED: "—",
}


# ---------------------------------------------------------------------------
# Step card widget
# ---------------------------------------------------------------------------
class StepCard(QFrame):
    def __init__(
        self,
        number: int,
        title: str,
        description: str,
        accent: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._accent = accent
        self.setObjectName("Card")
        self.setFixedWidth(200)

        vl = QVBoxLayout(self)
        vl.setContentsMargins(14, 12, 14, 12)
        vl.setSpacing(6)

        # Number badge + state
        hdr = QHBoxLayout()
        num_lbl = QLabel(str(number))
        num_lbl.setStyleSheet(f"""
            background:{accent}33; color:{accent}; border:1px solid {accent}88;
            border-radius:10px; font-size:11px; font-weight:700;
            padding:1px 7px;
        """)
        num_lbl.setFixedSize(26, 20)
        num_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.addWidget(num_lbl)
        hdr.addStretch()

        self._state_lbl = QLabel("○")
        self._state_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:16px;")
        hdr.addWidget(self._state_lbl)
        vl.addLayout(hdr)

        # Title
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{accent}; font-size:13px; font-weight:700;")
        vl.addWidget(title_lbl)

        # Description
        desc_lbl = QLabel(description)
        desc_lbl.setStyleSheet(f"color:{P['text_sec']}; font-size:11px;")
        desc_lbl.setWordWrap(True)
        vl.addWidget(desc_lbl)

        # Result count
        self._count_lbl = QLabel("—")
        self._count_lbl.setStyleSheet(f"color:{accent}; font-size:18px; font-weight:700; font-family:monospace;")
        vl.addWidget(self._count_lbl)

    def set_state(self, state: StepState, count: int = -1) -> None:
        color = _STATE_COLORS[state]
        icon  = _STATE_ICONS[state]
        self._state_lbl.setText(icon)
        self._state_lbl.setStyleSheet(f"color:{color}; font-size:16px;")
        self.setStyleSheet(f"""
            QFrame {{
                background:{P['bg2']};
                border:1px solid {color if state != StepState.IDLE else P['border']};
                border-radius:8px;
            }}
        """)
        if count >= 0:
            self._count_lbl.setText(str(count))


# ---------------------------------------------------------------------------
# Arrow widget
# ---------------------------------------------------------------------------
class _Arrow(QLabel):
    def __init__(self, parent=None):
        super().__init__("→", parent)
        self.setStyleSheet(f"color:{P['border']}; font-size:22px; font-weight:300;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


# ---------------------------------------------------------------------------
# Chain Worker
# ---------------------------------------------------------------------------
class ChainWorker(QObject):
    log        = pyqtSignal(str, str)   # (message, color)
    step_done  = pyqtSignal(int, int)   # (step_index, result_count)
    step_error = pyqtSignal(int, str)
    chain_done = pyqtSignal()

    def __init__(
        self,
        target: str,
        config: dict,
    ) -> None:
        super().__init__()
        self._target    = target
        self._cfg       = config
        self._stop_flag = False
        self._dork_urls: List[str]     = []
        self._endpoints: List[str]     = []
        self._param_urls: List[str]    = []
        self._injections: List[str]    = []

    def run(self) -> None:
        try:
            if not self._stop_flag and self._cfg.get("run_dorks"):
                self._step_dorks()
            if not self._stop_flag and self._cfg.get("run_katana"):
                self._step_katana()
            if not self._stop_flag and self._cfg.get("run_paramspider"):
                self._step_paramspider()
            if not self._stop_flag and self._cfg.get("run_sqlmap"):
                self._step_sqlmap()
        except Exception as e:
            self.log.emit(f"[CHAIN ERROR] {e}", P["red"])
        finally:
            self.chain_done.emit()

    # ---- Dorks ---------------------------------------------------
    def _step_dorks(self) -> None:
        self.log.emit(f"[Chain] Step 1: Dork's Eye — target: {self._target}", P["blue"])
        categories = self._cfg.get("dork_categories", [])
        queries = []
        for cat in categories:
            for label, tmpl in DORK_DB.get(cat, []):
                if tmpl:
                    queries.append((label, dork_for_target(tmpl, self._target)))

        custom = self._cfg.get("dork_custom", "").strip()
        if custom:
            for line in custom.splitlines():
                if line.strip():
                    queries.append(("Custom", dork_for_target(line.strip(), self._target)))

        if not queries:
            self.log.emit("[!] No dork queries configured — skipping.", P["orange"])
            self.step_done.emit(0, 0)
            return

        results = []
        max_r = self._cfg.get("dork_max_per_query", 10)
        for label, q in queries:
            if self._stop_flag:
                break
            self.log.emit(f"  [DDG] {label}: {q[:80]}", P["text_sec"])
            found = search_ddg(q, max_r, delay=1.5, progress_cb=lambda m: self.log.emit(m, P["text_muted"]))
            results.extend(found)

        self._dork_urls = list({r.url for r in results})
        self.log.emit(f"[+] Dork step complete — {len(self._dork_urls)} unique URLs.", P["green"])
        self.step_done.emit(0, len(self._dork_urls))

    # ---- Katana --------------------------------------------------
    def _step_katana(self) -> None:
        urls = self._dork_urls or [self._target]
        self.log.emit(f"[Chain] Step 2: Katana — crawling {len(urls)} URL(s)", P["cyan"])

        if not TOOL_PATHS.get("katana"):
            self.log.emit("[!] katana not installed — skipping crawl.", P["orange"])
            self._endpoints = urls
            self.step_done.emit(1, len(urls))
            return

        from PyQt6.QtCore import QEventLoop, QTimer
        import json

        collected: List[str] = []
        loop = QEventLoop()

        cmd, args = build_katana_cmd(
            urls        = urls[:50],   # limit to 50 in chain mode
            depth       = self._cfg.get("katana_depth", 2),
            concurrency = self._cfg.get("katana_concurrency", 5),
            js_crawl    = self._cfg.get("katana_js", False),
            form_extract= self._cfg.get("katana_forms", True),
            known_files = True,
        )

        runner = ProcessRunner()

        def on_line(line: str) -> None:
            self.log.emit(f"  {line}", P["text_sec"])
            if line.startswith("http"):
                url = line.split()[0]
                collected.append(url)
            elif line.startswith("{"):
                try:
                    d = json.loads(line)
                    if d.get("endpoint"):
                        collected.append(d["endpoint"])
                except Exception:
                    pass

        runner.stdout_line.connect(on_line)
        runner.finished_sig.connect(lambda _: loop.quit())
        runner.run(cmd, args)
        loop.exec()

        self._endpoints = list(set(collected)) or urls
        self.log.emit(f"[+] Katana step complete — {len(self._endpoints)} endpoints.", P["green"])
        self.step_done.emit(1, len(self._endpoints))

    # ---- ParamSpider ---------------------------------------------
    def _step_paramspider(self) -> None:
        from urllib.parse import urlparse
        # Extract unique domains from endpoints, or fall back to target
        domains: List[str] = []
        for url in (self._endpoints or [self._target]):
            try:
                host = urlparse(url).netloc or url
                if host not in domains:
                    domains.append(host)
            except Exception:
                pass
        if not domains:
            domains = [self._target]

        self.log.emit(f"[Chain] Step 3: ParamSpider — mining {len(domains)} domain(s)", P["pink"])

        if not TOOL_PATHS.get("paramspider"):
            self.log.emit("[!] paramspider not installed — skipping.", P["orange"])
            self._param_urls = [u for u in self._endpoints if "?" in u]
            self.step_done.emit(2, len(self._param_urls))
            return

        from PyQt6.QtCore import QEventLoop
        collected: List[str] = []

        for domain in domains[:20]:
            if self._stop_flag:
                break
            self.log.emit(f"  Mining: {domain}", P["text_sec"])
            loop = QEventLoop()

            cmd, args = build_paramspider_cmd(
                domain  = domain,
                exclude = self._cfg.get("paramspider_exclude", "png,jpg,gif,jpeg,swf,woff,svg,pdf,css"),
                subs    = self._cfg.get("paramspider_subs", False),
            )

            runner = ProcessRunner()

            def on_line(line: str) -> None:
                self.log.emit(f"  {line}", P["text_sec"])
                line = line.strip()
                if line.startswith("http"):
                    url = line.split()[0]
                    collected.append(url)

            runner.stdout_line.connect(on_line)
            runner.finished_sig.connect(lambda _: loop.quit())
            runner.run(cmd, args)
            loop.exec()

        self._param_urls = list(set(collected))
        # Also keep any parameterised URLs from Katana that ParamSpider didn't find
        for url in self._endpoints:
            if "?" in url and url not in self._param_urls:
                self._param_urls.append(url)

        self.log.emit(f"[+] ParamSpider step complete — {len(self._param_urls)} parameterised URLs.", P["green"])
        self.step_done.emit(2, len(self._param_urls))

    # ---- SQLMap --------------------------------------------------
    def _step_sqlmap(self) -> None:
        endpoints = self._param_urls or self._endpoints or [self._target]
        self.log.emit(f"[Chain] Step 4: SQLMap — testing {len(endpoints)} endpoint(s)", P["purple"])

        if not TOOL_PATHS.get("sqlmap"):
            self.log.emit("[!] sqlmap not installed — skipping.", P["orange"])
            self.step_done.emit(3, 0)
            return

        from PyQt6.QtCore import QEventLoop
        injections = []

        # Filter to likely-injectable (have params)
        targets = [u for u in endpoints if "?" in u][:self._cfg.get("sqlmap_max_targets", 20)]
        if not targets:
            self.log.emit("[!] No parameterised URLs found for SQLMap.", P["orange"])
            self.step_done.emit(3, 0)
            return

        for url in targets:
            if self._stop_flag:
                break
            self.log.emit(f"  Testing: {url}", P["text_sec"])
            loop = QEventLoop()

            cmd, args = build_sqlmap_cmd(
                url     = url,
                level   = self._cfg.get("sqlmap_level", 1),
                risk    = self._cfg.get("sqlmap_risk", 1),
                get_dbs = self._cfg.get("sqlmap_dbs", True),
                batch   = True,
            )

            runner = ProcessRunner()

            def on_line(line: str, u=url) -> None:
                self.log.emit(f"  {line}", P["text_sec"])
                if any(k in line for k in ("injectable", "identified the following")):
                    injections.append(u)
                    self.log.emit(f"  [VULN] {u}", P["green"])

            runner.stdout_line.connect(on_line)
            runner.finished_sig.connect(lambda _: loop.quit())
            runner.run(cmd, args)
            loop.exec()

        self._injections = list(set(injections))
        self.log.emit(f"[+] SQLMap step complete — {len(self._injections)} injection(s) found.", P["green"])
        self.step_done.emit(3, len(self._injections))

    def stop(self) -> None:
        self._stop_flag = True


# ---------------------------------------------------------------------------
# Chain Panel
# ---------------------------------------------------------------------------
class ChainPanel(QWidget):
    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate = navigate_cb
        self._worker:  Optional[ChainWorker] = None
        self._thread:  Optional[QThread]     = None
        self._setup_ui()

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        split = QSplitter(Qt.Orientation.Horizontal)
        split.setChildrenCollapsible(False)
        split.addWidget(self._build_config())
        split.addWidget(self._build_pipeline())
        split.setSizes([310, 890])
        root.addWidget(split, 1)

    # ------------------------------------------------------------------
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(56)
        bar.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        hl = QHBoxLayout(bar)
        hl.setContentsMargins(24, 0, 24, 0)
        hl.setSpacing(16)

        icon = QLabel("⛓")
        icon.setStyleSheet("font-size:20px;")
        title = QLabel("Recon Chain")
        title.setStyleSheet(f"color:{P['text']}; font-size:16px; font-weight:700;")
        sub = QLabel("Automated Dork's Eye → Katana → ParamSpider → SQLMap pipeline")
        sub.setStyleSheet(f"color:{P['text_sec']}; font-size:12px;")
        hl.addWidget(icon)
        hl.addWidget(title)
        hl.addWidget(sub)
        hl.addStretch()
        return bar

    # ------------------------------------------------------------------
    def _build_config(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMaximumWidth(320)

        w = QWidget()
        w.setStyleSheet(f"background:{P['bg0']}; border-right:1px solid {P['border']};")
        scroll.setWidget(w)

        vl = QVBoxLayout(w)
        vl.setContentsMargins(14, 14, 14, 14)
        vl.setSpacing(12)

        # Target
        vl.addWidget(SectionHeader("Target", P["green"]))
        self._target = QLineEdit()
        self._target.setPlaceholderText("example.com")
        vl.addWidget(self._target)

        # Step toggles
        vl.addWidget(SectionHeader("Pipeline Steps", P["green"]))
        self._do_dorks       = QCheckBox("Step 1: Dork's Eye")
        self._do_katana      = QCheckBox("Step 2: Katana Crawler")
        self._do_paramspider = QCheckBox("Step 3: ParamSpider")
        self._do_sqlmap      = QCheckBox("Step 4: SQLMap")
        self._do_dorks.setChecked(True)
        self._do_katana.setChecked(True)
        self._do_paramspider.setChecked(True)
        self._do_sqlmap.setChecked(True)
        for cb in (self._do_dorks, self._do_katana, self._do_paramspider, self._do_sqlmap):
            cb.setStyleSheet(f"font-weight:600; color:{P['text']};")
            vl.addWidget(cb)

        # Dork settings
        vl.addWidget(SectionHeader("Dork Settings", P["blue"]))
        dork_cats = list(DORK_DB.keys())
        self._dork_cat_checks = {}
        for cat in dork_cats:
            cb = QCheckBox(cat)
            cb.setChecked(cat in ("SQL Injection", "Login Pages"))
            self._dork_cat_checks[cat] = cb
            vl.addWidget(cb)

        self._dork_custom = QTextEdit()
        self._dork_custom.setPlaceholderText("Additional custom dorks…")
        self._dork_custom.setFixedHeight(56)
        vl.addWidget(self._dork_custom)

        self._dork_max = QComboBox()
        self._dork_max.addItems(["5", "10", "20"])
        self._dork_max.setCurrentIndex(1)
        vl.addWidget(QLabel("Max results per dork:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._dork_max)

        # Katana settings
        vl.addWidget(SectionHeader("Katana Settings", P["cyan"]))
        self._k_depth = LabeledSlider(1, 5, 2)
        vl.addWidget(QLabel("Crawl depth:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._k_depth)

        self._k_concur = LabeledSlider(1, 20, 5)
        vl.addWidget(QLabel("Concurrency:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._k_concur)

        self._k_js    = QCheckBox("JavaScript crawling  (-jc)")
        self._k_forms = QCheckBox("Form extraction  (-form-extraction)")
        self._k_forms.setChecked(True)
        vl.addWidget(self._k_js)
        vl.addWidget(self._k_forms)

        # ParamSpider settings
        vl.addWidget(SectionHeader("ParamSpider Settings", P["pink"]))
        self._ps_exclude = QLineEdit()
        self._ps_exclude.setText("png,jpg,gif,jpeg,swf,woff,svg,pdf,css")
        self._ps_exclude.setPlaceholderText("Extensions to exclude")
        vl.addWidget(QLabel("Exclude ext:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._ps_exclude)

        self._ps_subs = QCheckBox("Include subdomains  (-s)")
        vl.addWidget(self._ps_subs)

        # SQLMap settings
        vl.addWidget(SectionHeader("SQLMap Settings", P["purple"]))
        self._sq_level = LabeledSlider(1, 5, 1)
        vl.addWidget(QLabel("Level:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._sq_level)

        self._sq_risk  = LabeledSlider(1, 3, 1)
        vl.addWidget(QLabel("Risk:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._sq_risk)

        self._sq_dbs   = QCheckBox("Enumerate databases  (--dbs)")
        self._sq_dbs.setChecked(True)
        vl.addWidget(self._sq_dbs)

        self._sq_max_targets = QComboBox()
        self._sq_max_targets.addItems(["5", "10", "20", "50"])
        self._sq_max_targets.setCurrentIndex(0)
        vl.addWidget(QLabel("Max SQLMap targets:", styleSheet=f"color:{P['text_sec']}; font-size:12px;"))
        vl.addWidget(self._sq_max_targets)

        # Run bar
        self._run_bar = RunStopBar("Run Full Chain", "BtnSuccess")
        self._run_bar.run_clicked.connect(self._start)
        self._run_bar.stop_clicked.connect(self._stop)
        vl.addWidget(self._run_bar)

        vl.addStretch()
        return scroll

    # ------------------------------------------------------------------
    def _build_pipeline(self) -> QWidget:
        w = QWidget()
        w.setStyleSheet(f"background:{P['bg1']};")
        vl = QVBoxLayout(w)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Pipeline visualisation
        pipeline_frame = QFrame()
        pipeline_frame.setFixedHeight(160)
        pipeline_frame.setStyleSheet(f"background:{P['bg0']}; border-bottom:1px solid {P['border']};")
        pipe_hl = QHBoxLayout(pipeline_frame)
        pipe_hl.setContentsMargins(24, 16, 24, 16)
        pipe_hl.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        self._card_dorks       = StepCard(1, "Dork's Eye",
                                          "Discover URLs via Google dork queries",
                                          P["blue"])
        self._card_katana      = StepCard(2, "Katana",
                                          "Crawl URLs, extract endpoints & forms",
                                          P["cyan"])
        self._card_paramspider = StepCard(3, "ParamSpider",
                                          "Mine parameterised URLs from web archives",
                                          P["pink"])
        self._card_sqlmap      = StepCard(4, "SQLMap",
                                          "Test parameterised endpoints for SQLi",
                                          P["purple"])

        pipe_hl.addWidget(self._card_dorks)
        pipe_hl.addWidget(_Arrow())
        pipe_hl.addWidget(self._card_katana)
        pipe_hl.addWidget(_Arrow())
        pipe_hl.addWidget(self._card_paramspider)
        pipe_hl.addWidget(_Arrow())
        pipe_hl.addWidget(self._card_sqlmap)
        pipe_hl.addStretch()

        vl.addWidget(pipeline_frame)

        # Summary bar
        self._summary = QLabel("Configure the chain on the left and press Run.")
        self._summary.setStyleSheet(
            f"color:{P['text_sec']}; font-size:12px; padding:10px 20px;"
            f"background:{P['bg2']}; border-bottom:1px solid {P['border']};"
        )
        vl.addWidget(self._summary)

        # Terminal
        self._terminal = TerminalWidget()
        vl.addWidget(self._terminal, 1)
        return w

    # ------------------------------------------------------------------
    def _start(self) -> None:
        target = self._target.text().strip()
        if not target:
            self._terminal.warning("Enter a target domain first.")
            return

        dork_cats = [cat for cat, cb in self._dork_cat_checks.items() if cb.isChecked()]

        config = {
            "run_dorks":         self._do_dorks.isChecked(),
            "run_katana":        self._do_katana.isChecked(),
            "run_paramspider":   self._do_paramspider.isChecked(),
            "run_sqlmap":        self._do_sqlmap.isChecked(),
            "dork_categories":   dork_cats,
            "dork_custom":       self._dork_custom.toPlainText(),
            "dork_max_per_query":int(self._dork_max.currentText()),
            "katana_depth":      self._k_depth.value,
            "katana_concurrency":self._k_concur.value,
            "katana_js":         self._k_js.isChecked(),
            "katana_forms":      self._k_forms.isChecked(),
            "paramspider_exclude":self._ps_exclude.text().strip(),
            "paramspider_subs":  self._ps_subs.isChecked(),
            "sqlmap_level":      self._sq_level.value,
            "sqlmap_risk":       self._sq_risk.value,
            "sqlmap_dbs":        self._sq_dbs.isChecked(),
            "sqlmap_max_targets":int(self._sq_max_targets.currentText()),
        }

        for card in (self._card_dorks, self._card_katana, self._card_paramspider, self._card_sqlmap):
            card.set_state(StepState.IDLE)

        self._terminal.clear()
        self._terminal.info(f"Starting chain for target: {target}")
        self._run_bar.set_running(True)

        self._worker = ChainWorker(target, config)
        self._thread = QThread()
        self._worker.moveToThread(self._thread)

        self._worker.log.connect(lambda msg, col: self._terminal.append_line(msg, col))
        self._worker.step_done.connect(self._on_step_done)
        self._worker.step_error.connect(self._on_step_error)
        self._worker.chain_done.connect(self._on_chain_done)
        self._thread.started.connect(self._worker.run)
        self._thread.start()

        # Mark first active step as running
        if config["run_dorks"]:
            self._card_dorks.set_state(StepState.RUNNING)

    def _stop(self) -> None:
        if self._worker:
            self._worker.stop()
        self._terminal.warning("Chain stopped by user.")
        self._run_bar.set_running(False)

    def _on_step_done(self, step: int, count: int) -> None:
        cards = [self._card_dorks, self._card_katana, self._card_paramspider, self._card_sqlmap]
        cards[step].set_state(StepState.DONE, count)
        # Advance next step indicator
        if step + 1 < len(cards):
            cards[step + 1].set_state(StepState.RUNNING)

    def _on_step_error(self, step: int, msg: str) -> None:
        cards = [self._card_dorks, self._card_katana, self._card_paramspider, self._card_sqlmap]
        cards[step].set_state(StepState.ERROR)
        self._terminal.error(msg)

    def _on_chain_done(self) -> None:
        self._run_bar.set_running(False)
        self._terminal.success("Chain complete.")
        self._summary.setText("Chain complete — check individual tool panels for detailed results.")
        if self._thread:
            self._thread.quit()

    # ------------------------------------------------------------------
    def set_target(self, target: str) -> None:
        self._target.setText(target)
