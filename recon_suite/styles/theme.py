"""
SwordSuite — Unified Recon & Exploitation GUI
Dark theme: colour palette + complete QSS stylesheet
"""

# ---------------------------------------------------------------------------
# Colour palette
# ---------------------------------------------------------------------------
P = {
    # Backgrounds
    "bg0":  "#060a12",   # deepest (window)
    "bg1":  "#0d1117",   # main body
    "bg2":  "#161b27",   # cards / panels
    "bg3":  "#1e2638",   # inputs / table rows
    "bg4":  "#263045",   # hover / selected

    # Borders
    "border":   "#2a3550",
    "border_hi": "#06b6d4",

    # Accent colours
    "cyan":   "#06b6d4",   # primary  (Katana / chain)
    "green":  "#10b981",   # success  (found / active)
    "red":    "#ef4444",   # danger   (error / stop)
    "orange": "#f59e0b",   # warning  (SQLMap)
    "purple": "#8b5cf6",   # SQLMap accent
    "blue":   "#3b82f6",   # Dork's Eye accent
    "pink":   "#ec4899",   # secondary highlight

    # Text
    "text":       "#e2e8f0",
    "text_sec":   "#94a3b8",
    "text_muted": "#4b5675",

    # Specific semantic roles
    "dork_hi":   "#3b82f6",
    "katana_hi": "#06b6d4",
    "sql_hi":    "#8b5cf6",
    "chain_hi":  "#10b981",
}


# ---------------------------------------------------------------------------
# QSS stylesheet (returned as string)
# ---------------------------------------------------------------------------
def get_stylesheet() -> str:
    return f"""
/* ============================  BASE  ============================ */
QMainWindow, QDialog {{
    background-color: {P['bg0']};
    color: {P['text']};
}}

QWidget {{
    background-color: transparent;
    color: {P['text']};
    font-family: "Segoe UI", "Inter", "SF Pro Display", sans-serif;
    font-size: 13px;
}}

QScrollArea {{
    border: none;
    background-color: transparent;
}}

/* ============================  SIDEBAR  ============================ */
#Sidebar {{
    background-color: {P['bg0']};
    border-right: 1px solid {P['border']};
    min-width: 210px;
    max-width: 210px;
}}

#SidebarLogo {{
    background-color: {P['bg0']};
    border-bottom: 1px solid {P['border']};
    padding: 0px;
}}

#NavButton {{
    background-color: transparent;
    color: {P['text_sec']};
    border: none;
    border-left: 3px solid transparent;
    border-radius: 0px;
    padding: 10px 16px;
    text-align: left;
    font-size: 13px;
    font-weight: 500;
}}
#NavButton:hover {{
    background-color: {P['bg4']};
    color: {P['text']};
    border-left: 3px solid {P['cyan']};
}}
#NavButton[active="true"] {{
    background-color: {P['bg3']};
    color: {P['cyan']};
    border-left: 3px solid {P['cyan']};
    font-weight: 600;
}}

#SidebarSection {{
    color: {P['text_muted']};
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 1.5px;
    padding: 14px 18px 4px 18px;
    text-transform: uppercase;
}}

/* ============================  CONTENT AREA  ============================ */
#ContentArea {{
    background-color: {P['bg1']};
}}

#PanelHeader {{
    background-color: {P['bg0']};
    border-bottom: 1px solid {P['border']};
    padding: 0 24px;
}}

/* ============================  CARDS / GROUPS  ============================ */
#Card {{
    background-color: {P['bg2']};
    border: 1px solid {P['border']};
    border-radius: 8px;
}}

QGroupBox {{
    background-color: {P['bg2']};
    border: 1px solid {P['border']};
    border-radius: 8px;
    margin-top: 18px;
    padding: 12px 12px 8px 12px;
    font-weight: 600;
    color: {P['text_sec']};
    font-size: 11px;
    letter-spacing: 0.8px;
    text-transform: uppercase;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 12px;
    top: -1px;
    padding: 0 6px;
    background-color: {P['bg2']};
    color: {P['text_sec']};
}}

/* ============================  INPUTS  ============================ */
QLineEdit, QTextEdit, QPlainTextEdit {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 6px 10px;
    selection-background-color: {P['cyan']}44;
    font-family: "Cascadia Code", "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}}
QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{
    border: 1px solid {P['border_hi']};
    background-color: {P['bg4']};
}}
QLineEdit:disabled, QTextEdit:disabled, QPlainTextEdit:disabled {{
    color: {P['text_muted']};
    background-color: {P['bg2']};
}}

QComboBox {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 6px 10px;
    min-width: 120px;
}}
QComboBox:focus {{ border: 1px solid {P['border_hi']}; }}
QComboBox::drop-down {{
    border: none;
    width: 28px;
}}
QComboBox::down-arrow {{
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 6px solid {P['text_sec']};
    width: 0; height: 0;
    margin-right: 8px;
}}
QComboBox QAbstractItemView {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border_hi']};
    border-radius: 4px;
    selection-background-color: {P['bg4']};
    outline: none;
}}

QSpinBox {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 5px 8px;
}}
QSpinBox:focus {{ border: 1px solid {P['border_hi']}; }}
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {P['bg4']};
    border: none;
    width: 18px;
    border-radius: 3px;
}}
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {P['cyan']}55;
}}

/* ============================  BUTTONS  ============================ */
QPushButton {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    padding: 7px 16px;
    font-weight: 500;
    font-size: 12px;
}}
QPushButton:hover {{
    background-color: {P['bg4']};
    border-color: {P['cyan']};
    color: {P['cyan']};
}}
QPushButton:pressed {{ background-color: {P['bg0']}; }}
QPushButton:disabled {{
    color: {P['text_muted']};
    background-color: {P['bg2']};
    border-color: {P['border']};
}}

/* Semantic button variants via object names */
#BtnPrimary {{
    background-color: {P['cyan']}22;
    color: {P['cyan']};
    border: 1px solid {P['cyan']}88;
    font-weight: 600;
}}
#BtnPrimary:hover {{
    background-color: {P['cyan']}44;
    border-color: {P['cyan']};
}}

#BtnSuccess {{
    background-color: {P['green']}22;
    color: {P['green']};
    border: 1px solid {P['green']}88;
    font-weight: 600;
}}
#BtnSuccess:hover {{
    background-color: {P['green']}44;
    border-color: {P['green']};
}}

#BtnDanger {{
    background-color: {P['red']}22;
    color: {P['red']};
    border: 1px solid {P['red']}88;
    font-weight: 600;
}}
#BtnDanger:hover {{
    background-color: {P['red']}44;
    border-color: {P['red']};
}}

#BtnWarning {{
    background-color: {P['orange']}22;
    color: {P['orange']};
    border: 1px solid {P['orange']}88;
    font-weight: 600;
}}
#BtnWarning:hover {{
    background-color: {P['orange']}44;
    border-color: {P['orange']};
}}

#BtnPurple {{
    background-color: {P['purple']}22;
    color: {P['purple']};
    border: 1px solid {P['purple']}88;
    font-weight: 600;
}}
#BtnPurple:hover {{
    background-color: {P['purple']}44;
    border-color: {P['purple']};
}}

#BtnSmall {{
    padding: 4px 10px;
    font-size: 11px;
    border-radius: 4px;
}}

/* ============================  CHECKBOXES / RADIOS  ============================ */
QCheckBox, QRadioButton {{
    color: {P['text']};
    spacing: 8px;
}}
QCheckBox::indicator, QRadioButton::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {P['border']};
    border-radius: 4px;
    background-color: {P['bg3']};
}}
QCheckBox::indicator:checked, QRadioButton::indicator:checked {{
    background-color: {P['cyan']};
    border-color: {P['cyan']};
}}
QCheckBox::indicator:hover, QRadioButton::indicator:hover {{
    border-color: {P['cyan']};
}}
QRadioButton::indicator {{ border-radius: 8px; }}

/* ============================  SLIDERS  ============================ */
QSlider::groove:horizontal {{
    height: 4px;
    background: {P['border']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {P['cyan']};
    border: 2px solid {P['bg0']};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{ background: {P['cyan']}66; border-radius: 2px; }}

/* ============================  PROGRESS BAR  ============================ */
QProgressBar {{
    background-color: {P['bg3']};
    border: none;
    border-radius: 4px;
    height: 6px;
    text-align: center;
}}
QProgressBar::chunk {{
    background-color: {P['cyan']};
    border-radius: 4px;
}}

/* ============================  TABLES  ============================ */
QTableWidget, QTableView {{
    background-color: {P['bg2']};
    alternate-background-color: {P['bg3']};
    color: {P['text']};
    gridline-color: {P['border']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    selection-background-color: {P['bg4']};
    outline: none;
}}
QTableWidget::item, QTableView::item {{
    padding: 5px 8px;
    border-bottom: 1px solid {P['border']};
}}
QTableWidget::item:selected, QTableView::item:selected {{
    background-color: {P['cyan']}33;
    color: {P['text']};
}}
QHeaderView::section {{
    background-color: {P['bg3']};
    color: {P['text_sec']};
    border: none;
    border-bottom: 1px solid {P['border']};
    border-right: 1px solid {P['border']};
    padding: 6px 10px;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
    text-transform: uppercase;
}}
QHeaderView::section:last {{ border-right: none; }}

/* ============================  TREE WIDGET  ============================ */
QTreeWidget {{
    background-color: {P['bg2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    outline: none;
}}
QTreeWidget::item {{
    padding: 3px 0;
}}
QTreeWidget::item:selected {{
    background-color: {P['cyan']}33;
    color: {P['text']};
}}
QTreeWidget::item:hover {{
    background-color: {P['bg4']};
}}
QTreeWidget::branch:has-children:closed {{
    image: none;
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-top: 5px solid {P['text_sec']};
}}
QTreeWidget::branch:has-children:open {{
    border-left: 4px solid transparent;
    border-right: 4px solid transparent;
    border-bottom: 5px solid {P['text_sec']};
}}

/* ============================  TABS  ============================ */
QTabWidget::pane {{
    border: 1px solid {P['border']};
    border-top: none;
    background-color: {P['bg2']};
    border-radius: 0 0 8px 8px;
}}
QTabBar::tab {{
    background-color: {P['bg3']};
    color: {P['text_sec']};
    border: 1px solid {P['border']};
    border-bottom: none;
    padding: 7px 16px;
    margin-right: 2px;
    border-radius: 6px 6px 0 0;
}}
QTabBar::tab:selected {{
    background-color: {P['bg2']};
    color: {P['cyan']};
    border-bottom-color: {P['bg2']};
}}
QTabBar::tab:hover:!selected {{ background-color: {P['bg4']}; color: {P['text']}; }}

/* ============================  SCROLLBARS  ============================ */
QScrollBar:vertical {{
    background: {P['bg2']};
    width: 8px;
    border-radius: 4px;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {P['border']};
    border-radius: 4px;
    min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: {P['cyan']}88; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

QScrollBar:horizontal {{
    background: {P['bg2']};
    height: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:horizontal {{
    background: {P['border']};
    border-radius: 4px;
    min-width: 30px;
}}
QScrollBar::handle:horizontal:hover {{ background: {P['cyan']}88; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}

/* ============================  LABELS  ============================ */
#SectionTitle {{
    font-size: 18px;
    font-weight: 700;
    color: {P['text']};
}}
#SubTitle {{
    font-size: 13px;
    color: {P['text_sec']};
}}
#StatValue {{
    font-size: 28px;
    font-weight: 700;
    color: {P['cyan']};
    font-family: "Cascadia Code", monospace;
}}
#StatLabel {{
    font-size: 11px;
    font-weight: 600;
    color: {P['text_muted']};
    letter-spacing: 1px;
    text-transform: uppercase;
}}
#ToolBadge {{
    padding: 2px 8px;
    border-radius: 10px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 0.5px;
}}
#BadgeOK    {{ background-color: {P['green']}33; color: {P['green']}; border: 1px solid {P['green']}66; }}
#BadgeMiss  {{ background-color: {P['red']}33;   color: {P['red']};   border: 1px solid {P['red']}66; }}
#BadgeWarn  {{ background-color: {P['orange']}33; color: {P['orange']}; border: 1px solid {P['orange']}66; }}
#BadgeInfo  {{ background-color: {P['cyan']}22;  color: {P['cyan']};  border: 1px solid {P['cyan']}55; }}

/* ============================  SPLITTER  ============================ */
QSplitter::handle {{
    background-color: {P['border']};
    width: 1px;
    height: 1px;
}}
QSplitter::handle:hover {{
    background-color: {P['cyan']};
}}

/* ============================  STATUS BAR  ============================ */
QStatusBar {{
    background-color: {P['bg0']};
    color: {P['text_muted']};
    border-top: 1px solid {P['border']};
    font-size: 11px;
    padding: 0 12px;
}}
QStatusBar::item {{ border: none; }}

/* ============================  TOOLTIPS  ============================ */
QToolTip {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border_hi']};
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
}}

/* ============================  MENU  ============================ */
QMenu {{
    background-color: {P['bg3']};
    color: {P['text']};
    border: 1px solid {P['border_hi']};
    border-radius: 6px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 20px 6px 12px;
    border-radius: 4px;
}}
QMenu::item:selected {{
    background-color: {P['bg4']};
    color: {P['cyan']};
}}
QMenu::separator {{
    height: 1px;
    background: {P['border']};
    margin: 4px 0;
}}

/* ============================  LIST WIDGET  ============================ */
QListWidget {{
    background-color: {P['bg2']};
    color: {P['text']};
    border: 1px solid {P['border']};
    border-radius: 6px;
    outline: none;
}}
QListWidget::item {{
    padding: 5px 10px;
    border-bottom: 1px solid {P['border']};
}}
QListWidget::item:selected {{
    background-color: {P['cyan']}33;
    color: {P['text']};
}}
QListWidget::item:hover {{ background-color: {P['bg4']}; }}
"""
