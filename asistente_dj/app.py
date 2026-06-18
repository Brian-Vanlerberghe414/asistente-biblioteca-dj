"""Punto de entrada de la GUI del Asistente DJ.

Correr desde la carpeta asistente_dj/:
    python app.py
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

if __name__ == "__main__":
    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFontDatabase, QFont
    from gui.main_window import MainWindow
    from gui.theme import QSS

    app = QApplication(sys.argv)
    app.setApplicationName("Asistente DJ")

    # ── Fuentes ───────────────────────────────────────────────────────────────
    _gui_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "gui")
    _fonts_dir = os.path.join(_gui_dir, "assets", "fonts")
    if os.path.isdir(_fonts_dir):
        for fname in os.listdir(_fonts_dir):
            if fname.lower().endswith((".ttf", ".otf")):
                QFontDatabase.addApplicationFont(os.path.join(_fonts_dir, fname))

    # ── Tema QSS ──────────────────────────────────────────────────────────────
    app.setStyleSheet(QSS)

    # Fuente base: Space Grotesk si está disponible, Segoe UI si no
    families = QFontDatabase.families()
    if "Space Grotesk" in families:
        app.setFont(QFont("Space Grotesk", 12))
    else:
        app.setFont(QFont("Segoe UI Variable Text", 12)
                    if "Segoe UI Variable Text" in families
                    else QFont("Segoe UI", 12))

    win = MainWindow()
    win.show()
    sys.exit(app.exec())
