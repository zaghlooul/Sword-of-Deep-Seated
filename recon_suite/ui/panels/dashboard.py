"""
SwordSuite — Dashboard Panel
Overview: tool health, session stats, quick-start actions.
"""
from __future__ import annotations

import time
from typing import Callable, Optional

from PyQt6.QtCore    import Qt, QTimer
from PyQt6.QtWidgets import (
    QFrame, QGridLayout, QHBoxLayout, QLabel,
    QPushButton, QScrollArea, QSizePolicy,
    QVBoxLayout, QWidget,
)

from recon_suite.core.tool_runner import TOOL_PATHS, detect_tools
from recon_suite.core.session     import list_sessions, Session
from recon_suite.styles.theme     import P
from recon_suite.ui.widgets.form_widgets import ToolStatusCard


# ---------------------------------------------------------------------------
# Stat tile
# ---------------------------------------------------------------------------
class _StatTile(QFrame):
    def __init__(
        self,
        value: str,
        label: str,
        accent: str,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        vl = QVBoxLayout(self)
        vl.setContentsMargins(20, 16, 20, 16)
        vl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._val_lbl = QLabel(value)
        self._val_lbl.setObjectName("StatValue")
        self._val_lbl.setStyleSheet(f"color:{accent}; font-size:32px; font-weight:700; font-family:monospace;")
        self._val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self._lbl = QLabel(label)
        self._lbl.setObjectName("StatLabel")
        self._lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:10px; font-weight:700; letter-spacing:1px;")
        self._lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        vl.addWidget(self._val_lbl)
        vl.addWidget(self._lbl)

    def update_value(self, value: str) -> None:
        self._val_lbl.setText(value)


# ---------------------------------------------------------------------------
# QuickAction button
# ---------------------------------------------------------------------------
class _QuickBtn(QPushButton):
    def __init__(self, icon: str, title: str, desc: str, color: str, parent=None):
        super().__init__(parent)
        self.setFixedHeight(72)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setStyleSheet(f"""
            QPushButton {{
                background: {P['bg2']};
                border: 1px solid {P['border']};
                border-radius: 8px;
                text-align: left;
                padding: 12px 16px;
                color: {P['text']};
            }}
            QPushButton:hover {{
                background: {P['bg4']};
                border-color: {color};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        top = QHBoxLayout()
        top.setSpacing(8)
        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet(f"color:{color}; font-size:16px; background:transparent; border:none;")
        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(f"color:{color}; font-weight:600; font-size:13px; background:transparent; border:none;")
        top.addWidget(icon_lbl)
        top.addWidget(title_lbl)
        top.addStretch()
        layout.addLayout(top)

        desc_lbl = QLabel(desc)
        desc_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px; background:transparent; border:none;")
        layout.addWidget(desc_lbl)


# ---------------------------------------------------------------------------
# Dashboard Panel
# ---------------------------------------------------------------------------
class DashboardPanel(QWidget):
    def __init__(
        self,
        navigate_cb: Callable[[str], None],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self._navigate = navigate_cb
        self._setup_ui()

        # Refresh stats every 30 s
        t = QTimer(self)
        t.timeout.connect(self._refresh_stats)
        t.start(30_000)

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        body = QWidget()
        body.setStyleSheet(f"background:{P['bg1']};")
        scroll.setWidget(body)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.addWidget(scroll)

        vl = QVBoxLayout(body)
        vl.setContentsMargins(28, 24, 28, 28)
        vl.setSpacing(24)

        # --- Header ------------------------------------------------
        hdr = QWidget()
        hdr_l = QVBoxLayout(hdr)
        hdr_l.setContentsMargins(0, 0, 0, 0)
        hdr_l.setSpacing(4)

        title = QLabel("SwordSuite")
        title.setStyleSheet(f"color:{P['text']}; font-size:26px; font-weight:800; letter-spacing:-0.5px;")
        subtitle = QLabel(
            "Unified reconnaissance & exploitation framework  —  "
            "Dork's Eye  ·  Katana  ·  ParamSpider  ·  SQLMap"
        )
        subtitle.setStyleSheet(f"color:{P['text_sec']}; font-size:13px;")
        hdr_l.addWidget(title)
        hdr_l.addWidget(subtitle)
        vl.addWidget(hdr)

        # --- Stat tiles --------------------------------------------
        stats_grid = QGridLayout()
        stats_grid.setSpacing(14)

        self._stat_sessions   = _StatTile("0", "SESSIONS",        P["cyan"])
        self._stat_dorks      = _StatTile("0", "DORK RESULTS",    P["blue"])
        self._stat_endpoints  = _StatTile("0", "ENDPOINTS",       P["green"])
        self._stat_params     = _StatTile("0", "PARAM URLS",      P["pink"])
        self._stat_injections = _StatTile("0", "SQL INJECTIONS",  P["purple"])

        stats_grid.addWidget(self._stat_sessions,   0, 0)
        stats_grid.addWidget(self._stat_dorks,      0, 1)
        stats_grid.addWidget(self._stat_endpoints,  0, 2)
        stats_grid.addWidget(self._stat_params,     0, 3)
        stats_grid.addWidget(self._stat_injections, 0, 4)
        vl.addLayout(stats_grid)

        # --- Quick actions -----------------------------------------
        qa_title = QLabel("Quick Start")
        qa_title.setStyleSheet(f"color:{P['text']}; font-size:14px; font-weight:700;")
        vl.addWidget(qa_title)

        qa_grid = QGridLayout()
        qa_grid.setSpacing(12)

        btn_chain = _QuickBtn("⛓", "New Recon Chain",
                              "Run full Dorks → Katana → SQLMap pipeline on a target",
                              P["green"])
        btn_chain.clicked.connect(lambda: self._navigate("chain"))

        btn_dorks = _QuickBtn("👁", "Dork's Eye",
                              "Search for vulnerabilities using Google dork queries",
                              P["blue"])
        btn_dorks.clicked.connect(lambda: self._navigate("dorks"))

        btn_katana = _QuickBtn("⚔", "Katana Crawler",
                               "Deep-crawl web targets to map endpoints and forms",
                               P["cyan"])
        btn_katana.clicked.connect(lambda: self._navigate("katana"))

        btn_paramspider = _QuickBtn("P", "ParamSpider",
                                    "Extract parameterised URLs from web archives",
                                    P["pink"])
        btn_paramspider.clicked.connect(lambda: self._navigate("paramspider"))

        btn_sqlmap = _QuickBtn("💉", "SQLMap",
                               "Automated SQL injection detection and exploitation",
                               P["purple"])
        btn_sqlmap.clicked.connect(lambda: self._navigate("sqlmap"))

        qa_grid.addWidget(btn_chain,       0, 0)
        qa_grid.addWidget(btn_dorks,       0, 1)
        qa_grid.addWidget(btn_katana,      1, 0)
        qa_grid.addWidget(btn_paramspider, 1, 1)
        qa_grid.addWidget(btn_sqlmap,      2, 0)
        vl.addLayout(qa_grid)

        # --- Tool status -------------------------------------------
        ts_title = QLabel("Tool Status")
        ts_title.setStyleSheet(f"color:{P['text']}; font-size:14px; font-weight:700;")
        vl.addWidget(ts_title)

        ts_grid = QGridLayout()
        ts_grid.setSpacing(12)

        tools_info = [
            ("dorks-eye",    P["blue"],
             "Google dork automation — discovers exposed assets via search engine queries.",
             "pip install dorks-eye  OR  git clone https://github.com/BullsEye0/dorks-eye"),
            ("katana",       P["cyan"],
             "ProjectDiscovery's blazing-fast web crawler and spider with JS rendering.",
             "go install github.com/projectdiscovery/katana/cmd/katana@latest"),
            ("paramspider",  P["pink"],
             "Extracts parameterised URLs from web archives for targeted parameter testing.",
             "pip install paramspider"),
            ("sqlmap",       P["purple"],
             "The open-source SQL injection and database take-over tool.",
             "apt install sqlmap  OR  pip install sqlmap"),
        ]
        for col, (name, color, desc, hint) in enumerate(tools_info):
            card = ToolStatusCard(name, TOOL_PATHS.get(name), desc, hint, color)
            ts_grid.addWidget(card, 0 if col < 2 else 1, col % 2)

        vl.addLayout(ts_grid)

        # --- Recent sessions ----------------------------------------
        rs_hdr = QHBoxLayout()
        rs_title = QLabel("Recent Sessions")
        rs_title.setStyleSheet(f"color:{P['text']}; font-size:14px; font-weight:700;")
        rs_hdr.addWidget(rs_title)
        rs_hdr.addStretch()
        all_btn = QPushButton("View All →")
        all_btn.setStyleSheet(f"background:transparent; color:{P['cyan']}; border:none; font-size:12px;")
        all_btn.clicked.connect(lambda: self._navigate("sessions"))
        rs_hdr.addWidget(all_btn)
        vl.addLayout(rs_hdr)

        self._sessions_container = QVBoxLayout()
        self._sessions_container.setSpacing(6)
        vl.addLayout(self._sessions_container)
        self._refresh_stats()

        vl.addStretch()

    # ------------------------------------------------------------------
    def _refresh_stats(self) -> None:
        sessions = list_sessions()
        total_dorks = 0
        total_endpoints = 0
        total_params = 0
        total_injections = 0

        # Clear old session rows
        while self._sessions_container.count():
            item = self._sessions_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        for i, path in enumerate(sessions[:5]):
            try:
                s = Session.load(path)
                total_dorks     += len(s.dork_results)
                total_endpoints += len(s.katana_results)
                total_params    += len(s.paramspider_results)
                total_injections+= len(s.sqlmap_results)
                if i < 5:
                    row = self._session_row(s)
                    self._sessions_container.addWidget(row)
            except Exception:
                continue

        if not sessions:
            empty = QLabel("No sessions yet. Start a new scan to get going.")
            empty.setStyleSheet(f"color:{P['text_muted']}; font-size:12px; padding:12px;")
            self._sessions_container.addWidget(empty)

        self._stat_sessions.update_value(str(len(sessions)))
        self._stat_dorks.update_value(str(total_dorks))
        self._stat_endpoints.update_value(str(total_endpoints))
        self._stat_params.update_value(str(total_params))
        self._stat_injections.update_value(str(total_injections))

    def _session_row(self, session: Session) -> QWidget:
        row = QFrame()
        row.setStyleSheet(f"""
            QFrame {{
                background:{P['bg2']};
                border:1px solid {P['border']};
                border-radius:6px;
            }}
            QFrame:hover {{ border-color:{P['border_hi']}; }}
        """)
        hl = QHBoxLayout(row)
        hl.setContentsMargins(14, 10, 14, 10)
        hl.setSpacing(16)

        # Name + target
        info = QVBoxLayout()
        info.setSpacing(2)
        name_lbl = QLabel(session.name or "Unnamed Session")
        name_lbl.setStyleSheet(f"color:{P['text']}; font-weight:600; font-size:13px;")
        tgt_lbl  = QLabel(session.target or "—")
        tgt_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px; font-family:monospace;")
        info.addWidget(name_lbl)
        info.addWidget(tgt_lbl)
        hl.addLayout(info, 1)

        # Stats
        for count, label, color in [
            (len(session.dork_results),       "dorks",     P["blue"]),
            (len(session.katana_results),     "endpoints", P["cyan"]),
            (len(session.paramspider_results),"params",    P["pink"]),
            (len(session.sqlmap_results),     "injections",P["purple"]),
        ]:
            stat_w = QWidget()
            stat_l = QVBoxLayout(stat_w)
            stat_l.setContentsMargins(8, 0, 8, 0)
            stat_l.setSpacing(0)
            stat_l.setAlignment(Qt.AlignmentFlag.AlignCenter)
            QLabel(str(count)).setParent(None)

            c_lbl = QLabel(str(count))
            c_lbl.setStyleSheet(f"color:{color}; font-size:16px; font-weight:700; font-family:monospace;")
            c_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            l_lbl = QLabel(label)
            l_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:10px;")
            l_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            stat_l.addWidget(c_lbl)
            stat_l.addWidget(l_lbl)
            hl.addWidget(stat_w)

        # Date
        date_str = time.strftime("%b %d", time.localtime(session.updated_at))
        date_lbl = QLabel(date_str)
        date_lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
        hl.addWidget(date_lbl)

        return row
