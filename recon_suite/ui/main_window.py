"""
SwordSuite — Main Window
Sidebar navigation + stacked panel container.
"""
from __future__ import annotations

from typing import Dict

from PyQt6.QtCore    import Qt, QSize
from PyQt6.QtGui     import QFont, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QPushButton, QSizePolicy, QStackedWidget,
    QStatusBar, QVBoxLayout, QWidget,
)

from recon_suite.styles.theme           import P, get_stylesheet
from recon_suite.core.tool_runner       import detect_tools, TOOL_PATHS
from recon_suite.ui.panels.dashboard    import DashboardPanel
from recon_suite.ui.panels.dorks_panel  import DorksPanel
from recon_suite.ui.panels.katana_panel import KatanaPanel
from recon_suite.ui.panels.paramspider_panel import ParamSpiderPanel
from recon_suite.ui.panels.sqlmap_panel import SqlmapPanel
from recon_suite.ui.panels.chain_panel  import ChainPanel
from recon_suite.ui.panels.sessions_panel import SessionsPanel


# ---------------------------------------------------------------------------
# Sidebar navigation button
# ---------------------------------------------------------------------------
class _NavButton(QPushButton):
    def __init__(self, icon: str, label: str, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setFixedHeight(46)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        hl = QHBoxLayout(self)
        hl.setContentsMargins(16, 0, 16, 0)
        hl.setSpacing(12)

        icon_lbl = QLabel(icon)
        icon_lbl.setStyleSheet("background:transparent; border:none; font-size:15px;")
        icon_lbl.setFixedWidth(20)

        text_lbl = QLabel(label)
        text_lbl.setStyleSheet("background:transparent; border:none; font-size:13px; font-weight:500;")

        hl.addWidget(icon_lbl)
        hl.addWidget(text_lbl)
        hl.addStretch()

    @property
    def key(self) -> str:
        return self._key


# ---------------------------------------------------------------------------
# Main Window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("SwordSuite — Unified Recon & Exploitation Framework")
        self.setMinimumSize(1200, 720)
        self.resize(1440, 860)

        # Apply global stylesheet
        QApplication.instance().setStyleSheet(get_stylesheet())

        self._panels:  Dict[str, QWidget] = {}
        self._nav_btns: Dict[str, _NavButton] = {}

        self._setup_ui()
        self._setup_shortcuts()
        self._navigate("dashboard")

    # ------------------------------------------------------------------
    def _setup_ui(self) -> None:
        central = QWidget()
        central.setObjectName("ContentArea")
        self.setCentralWidget(central)

        hl = QHBoxLayout(central)
        hl.setContentsMargins(0, 0, 0, 0)
        hl.setSpacing(0)

        hl.addWidget(self._build_sidebar())

        self._stack = QStackedWidget()
        self._stack.setStyleSheet(f"background:{P['bg1']};")
        hl.addWidget(self._stack, 1)

        self._build_panels()
        self._build_statusbar()

    # ------------------------------------------------------------------
    def _build_sidebar(self) -> QWidget:
        sidebar = QWidget()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(210)

        vl = QVBoxLayout(sidebar)
        vl.setContentsMargins(0, 0, 0, 0)
        vl.setSpacing(0)

        # Logo / brand
        logo = QWidget()
        logo.setObjectName("SidebarLogo")
        logo.setFixedHeight(64)
        logo_l = QVBoxLayout(logo)
        logo_l.setContentsMargins(18, 0, 18, 0)
        logo_l.setAlignment(Qt.AlignmentFlag.AlignVCenter)

        brand = QLabel("⚔ SwordSuite")
        brand.setStyleSheet(f"color:{P['cyan']}; font-size:17px; font-weight:800; letter-spacing:-0.5px;")
        tagline = QLabel("Recon & Exploit Chain")
        tagline.setStyleSheet(f"color:{P['text_muted']}; font-size:10px; letter-spacing:0.5px;")
        logo_l.addWidget(brand)
        logo_l.addWidget(tagline)
        vl.addWidget(logo)

        # Nav items
        def section(title: str) -> QLabel:
            lbl = QLabel(title)
            lbl.setObjectName("SidebarSection")
            return lbl

        nav_items = [
            ("MAIN", [
                ("🏠", "Dashboard",  "dashboard"),
            ]),
            ("TOOLS", [
                ("👁", "Dork's Eye",    "dorks"),
                ("⚔", "Katana",        "katana"),
                ("P", "ParamSpider",   "paramspider"),
                ("💉", "SQLMap",        "sqlmap"),
            ]),
            ("WORKFLOW", [
                ("⛓", "Recon Chain", "chain"),
                ("💾", "Sessions",    "sessions"),
            ]),
        ]

        self._nav_group: list[_NavButton] = []

        for section_title, items in nav_items:
            vl.addWidget(section(section_title))
            for icon, label, key in items:
                btn = _NavButton(icon, label, key)
                btn.clicked.connect(lambda checked, k=key: self._navigate(k))
                self._nav_btns[key] = btn
                self._nav_group.append(btn)
                vl.addWidget(btn)

        vl.addStretch()

        # Bottom: version + tool status dots
        bottom = QWidget()
        bottom.setStyleSheet(f"background:{P['bg0']}; border-top:1px solid {P['border']};")
        b_vl = QVBoxLayout(bottom)
        b_vl.setContentsMargins(16, 10, 16, 10)
        b_vl.setSpacing(4)

        detect_tools()
        for tool, color in [("dorks-eye", P["blue"]), ("katana", P["cyan"]), ("paramspider", P["pink"]), ("sqlmap", P["purple"])]:
            dot_color = P["green"] if TOOL_PATHS.get(tool) else P["text_muted"]
            row = QHBoxLayout()
            dot = QLabel("●")
            dot.setStyleSheet(f"color:{dot_color}; font-size:9px;")
            lbl = QLabel(tool)
            lbl.setStyleSheet(f"color:{P['text_muted']}; font-size:11px;")
            row.addWidget(dot)
            row.addWidget(lbl)
            row.addStretch()
            b_vl.addLayout(row)

        ver = QLabel("v1.0.0")
        ver.setStyleSheet(f"color:{P['text_muted']}; font-size:10px; margin-top:4px;")
        b_vl.addWidget(ver)
        vl.addWidget(bottom)

        return sidebar

    # ------------------------------------------------------------------
    def _build_panels(self) -> None:
        def nav(key: str) -> None:
            self._navigate(key)

        # Dashboard
        dash = DashboardPanel(navigate_cb=nav)
        self._add_panel("dashboard", dash)

        # Dork's Eye
        dorks = DorksPanel(navigate_cb=nav)
        dorks.send_to_katana.connect(self._katana_receive)
        dorks.send_to_sqlmap.connect(self._sqlmap_receive)
        self._add_panel("dorks", dorks)

        # Katana
        katana = KatanaPanel(navigate_cb=nav)
        katana.send_to_paramspider.connect(self._paramspider_receive)
        katana.send_to_sqlmap.connect(self._sqlmap_receive)
        self._add_panel("katana", katana)

        # ParamSpider
        paramspider = ParamSpiderPanel(navigate_cb=nav)
        paramspider.send_to_sqlmap.connect(self._sqlmap_receive)
        self._add_panel("paramspider", paramspider)

        # SQLMap
        sqlmap = SqlmapPanel(navigate_cb=nav)
        self._add_panel("sqlmap", sqlmap)

        # Chain
        chain = ChainPanel(navigate_cb=nav)
        self._add_panel("chain", chain)

        # Sessions
        sessions = SessionsPanel(navigate_cb=nav)
        self._add_panel("sessions", sessions)

    def _add_panel(self, key: str, widget: QWidget) -> None:
        self._panels[key] = widget
        self._stack.addWidget(widget)

    # ------------------------------------------------------------------
    def _build_statusbar(self) -> None:
        sb = QStatusBar()
        self.setStatusBar(sb)

        self._status_lbl = QLabel("Ready")
        sb.addWidget(self._status_lbl)
        sb.addPermanentWidget(QLabel(f"PyQt6  |  Python  |  SwordSuite v1.0"))

    # ------------------------------------------------------------------
    def _navigate(self, key: str) -> None:
        panel = self._panels.get(key)
        if panel is None:
            return
        self._stack.setCurrentWidget(panel)

        # Update nav button states
        for k, btn in self._nav_btns.items():
            btn.setChecked(k == key)
            btn.setProperty("active", "true" if k == key else "false")
            # Refresh style so property selector re-evaluates
            btn.style().unpolish(btn)
            btn.style().polish(btn)

        self._status_lbl.setText(f"Panel: {key.capitalize()}")

    def _katana_receive(self, urls: list) -> None:
        katana: KatanaPanel = self._panels["katana"]
        katana.set_targets(urls)

    def _paramspider_receive(self, domains: list) -> None:
        paramspider: ParamSpiderPanel = self._panels["paramspider"]
        paramspider.set_domains(domains)

    def _sqlmap_receive(self, urls: list) -> None:
        sqlmap: SqlmapPanel = self._panels["sqlmap"]
        sqlmap.set_targets(urls)

    # ------------------------------------------------------------------
    def _setup_shortcuts(self) -> None:
        keys = {
            "dashboard":    "Ctrl+1",
            "dorks":        "Ctrl+2",
            "katana":       "Ctrl+3",
            "paramspider":  "Ctrl+4",
            "sqlmap":       "Ctrl+5",
            "chain":        "Ctrl+6",
            "sessions":     "Ctrl+7",
        }
        for key, shortcut in keys.items():
            sc = QShortcut(QKeySequence(shortcut), self)
            sc.activated.connect(lambda k=key: self._navigate(k))

    # ------------------------------------------------------------------
    def closeEvent(self, event) -> None:
        # Graceful shutdown — nothing special needed yet
        event.accept()
