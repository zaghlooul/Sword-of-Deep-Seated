#!/usr/bin/env python3
"""
SwordSuite — Unified Recon & Exploitation Framework
Entry point.

Usage:
    python main.py
"""
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(__file__))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore    import Qt, QCoreApplication
from PyQt6.QtGui     import QFont

from recon_suite.ui.main_window import MainWindow


def main() -> None:
    # High DPI support
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_UseHighDpiPixmaps)

    app = QApplication(sys.argv)
    app.setApplicationName("SwordSuite")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("SwordSuite")

    # Base font
    font = QFont("Segoe UI", 10)
    font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(font)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
