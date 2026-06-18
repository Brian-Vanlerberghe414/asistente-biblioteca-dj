"""Tokens de diseño y hoja de estilos QSS — Asistente DJ by Overcome Harmony."""
from __future__ import annotations

# ── Colores base ──────────────────────────────────────────────────────────────
BG_BASE      = "#0F0F10"
BG_PANEL     = "#0D0D0E"
BG_ELEVATED  = "#161617"
BG_TOOLBAR   = "#131314"
BG_HEADER    = "#141415"
LINE         = "#1F1F21"
TEXT_PRIMARY   = "#E9E9EC"
TEXT_SECONDARY = "#9A9CA1"
TEXT_MUTED     = "#75777B"

# ── Acentos ───────────────────────────────────────────────────────────────────
CYAN   = "#00E5FF"
ORANGE = "#FF6B00"
GREEN  = "#16D6A6"
AMBER  = "#FFB02E"

# ── Escala de energía 1-10 (índice 0 = nivel 1) ───────────────────────────────
ENERGY_COLORS = [
    "#2F6BFF", "#2F9BFF", "#18C5E0", "#16D6A6", "#4FD64F",
    "#B7D63A", "#FFD23A", "#FF9B2F", "#FF6A2A", "#FF3326",
]

# ── Camelot Wheel 1-12 (índice 0 = número 1) ─────────────────────────────────
CAMELOT_COLORS = [
    "#6AD5B0", "#7ED99A", "#A8DF7C", "#D4DD6F", "#F0CF6A",
    "#F5A85F", "#F07D6A", "#EE6A8F", "#D96EC0", "#A77CE0",
    "#7A8CE8", "#6AB4DC",
]

# ── Colores por género ────────────────────────────────────────────────────────
GENRE_COLORS = {
    "Techno":      "#00E5FF",
    "House":       "#FF6B00",
    "Trance":      "#A77CE0",
    "Indie Dance": "#4FD64F",
    "Big Room":    "#FFD23A",
}

# ── QSS principal ─────────────────────────────────────────────────────────────
QSS = f"""
/* ═══════════════════════════════ BASE ═══════════════════════════════════════ */
QWidget {{
    background-color: {BG_BASE};
    color: {TEXT_PRIMARY};
    font-family: "Space Grotesk", "Segoe UI Variable", "Segoe UI", sans-serif;
    font-size: 13px;
    selection-background-color: rgba(0,229,255,0.20);
    selection-color: {TEXT_PRIMARY};
}}

QMainWindow, QDialog {{
    background-color: {BG_BASE};
}}

/* ═══════════════════════════════ TOOLBAR ════════════════════════════════════ */
QToolBar {{
    background-color: {BG_TOOLBAR};
    border: none;
    border-bottom: 1px solid {LINE};
    padding: 5px 8px;
    spacing: 2px;
}}
QToolBar::separator {{
    background: {LINE};
    width: 1px;
    margin: 8px 4px;
}}
QToolBar QToolButton {{
    background: transparent;
    color: #C4C5C8;
    border: none;
    border-radius: 7px;
    padding: 6px 11px;
    font-size: 12px;
    font-weight: 500;
    min-width: 70px;
}}
QToolBar QToolButton:hover {{
    background: rgba(255,255,255,0.06);
    color: {TEXT_PRIMARY};
}}
QToolBar QToolButton:pressed, QToolBar QToolButton:checked {{
    background: rgba(255,255,255,0.10);
}}

/* ═══════════════════════════════ TABS ═══════════════════════════════════════ */
QTabWidget::pane {{
    border: none;
    background: {BG_BASE};
}}
QTabWidget::tab-bar {{
    left: 0px;
}}
QTabBar {{
    background: {BG_ELEVATED};
    border-bottom: 1px solid {LINE};
}}
QTabBar::tab {{
    background: transparent;
    color: {TEXT_MUTED};
    padding: 8px 20px;
    border: none;
    border-bottom: 2px solid transparent;
    font-size: 12px;
    font-weight: 600;
}}
QTabBar::tab:selected {{
    color: {TEXT_PRIMARY};
    border-bottom: 2px solid {CYAN};
}}
QTabBar::tab:hover:!selected {{
    color: {TEXT_SECONDARY};
    background: rgba(255,255,255,0.03);
}}

/* ═══════════════════════════════ TREE WIDGET ════════════════════════════════ */
QTreeWidget {{
    background: {BG_PANEL};
    alternate-background-color: transparent;
    border: none;
    border-right: 1px solid {LINE};
    color: {TEXT_PRIMARY};
    font-size: 12px;
    outline: none;
    padding-top: 4px;
}}
QTreeWidget::item {{
    padding: 5px 8px 5px 4px;
    border-radius: 4px;
    height: 26px;
}}
QTreeWidget::item:hover {{
    background: rgba(255,255,255,0.04);
}}
QTreeWidget::item:selected {{
    background: rgba(0,229,255,0.10);
    color: {CYAN};
}}
QTreeWidget::branch {{
    background: transparent;
}}
QTreeWidget QHeaderView::section {{
    background: {BG_PANEL};
    border: none;
    color: {TEXT_MUTED};
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    padding: 6px 8px;
    letter-spacing: 1px;
}}

/* ═══════════════════════════════ TABLE VIEW ═════════════════════════════════ */
QTableView {{
    background: {BG_BASE};
    border: none;
    gridline-color: rgba(31,31,33,0.60);
    color: {TEXT_PRIMARY};
    alternate-background-color: transparent;
    outline: none;
    font-size: 12px;
}}
QTableView::item {{
    padding: 0px 4px;
    border: none;
}}
QTableView::item:hover {{
    background: rgba(255,255,255,0.035);
}}
QTableView::item:selected {{
    background: rgba(0,229,255,0.09);
    color: {TEXT_PRIMARY};
}}
QHeaderView {{
    background: {BG_HEADER};
}}
QHeaderView::section {{
    background: {BG_HEADER};
    color: {TEXT_MUTED};
    border: none;
    border-bottom: 1px solid {LINE};
    border-right: 1px solid {LINE};
    padding: 0px 12px;
    height: 32px;
    font-size: 10px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 1px;
}}
QHeaderView::section:checked {{
    background: {BG_HEADER};
}}
QHeaderView::section:last {{
    border-right: none;
}}

/* ═══════════════════════════════ SCROLLBARS ══════════════════════════════════ */
QScrollBar:vertical {{
    background: transparent;
    width: 6px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background: rgba(255,255,255,0.22);
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; border: none; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}

QScrollBar:horizontal {{
    background: transparent;
    height: 6px;
    margin: 0;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background: rgba(255,255,255,0.12);
    border-radius: 3px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background: rgba(255,255,255,0.22);
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; border: none; }}
QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{ background: none; }}

/* ═══════════════════════════════ LINE EDIT ══════════════════════════════════ */
QLineEdit {{
    background: #1A1A1C;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 6px 10px;
    font-size: 12px;
}}
QLineEdit:focus {{
    border: 1px solid rgba(0,229,255,0.45);
    background: #1C1C1E;
}}
QLineEdit:disabled {{
    color: {TEXT_MUTED};
}}

/* ═══════════════════════════════ COMBO BOX ══════════════════════════════════ */
QComboBox {{
    background: #1A1A1C;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 5px 10px;
    font-size: 12px;
    min-width: 72px;
}}
QComboBox:hover {{
    border-color: rgba(255,255,255,0.18);
}}
QComboBox:on {{
    border-color: rgba(0,229,255,0.35);
}}
QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 18px;
    border: none;
}}
QComboBox::down-arrow {{
    width: 0;
    height: 0;
}}
QComboBox QAbstractItemView {{
    background: #1E1E20;
    border: 1px solid {LINE};
    color: {TEXT_PRIMARY};
    selection-background-color: rgba(0,229,255,0.14);
    selection-color: {TEXT_PRIMARY};
    outline: none;
    padding: 4px;
}}
QComboBox QAbstractItemView::item {{
    padding: 6px 10px;
    border-radius: 4px;
}}

/* ═══════════════════════════════ PUSH BUTTON ════════════════════════════════ */
QPushButton {{
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.10);
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 7px 16px;
    font-size: 12px;
    font-weight: 500;
    min-height: 30px;
}}
QPushButton:hover {{
    background: rgba(255,255,255,0.09);
    border-color: rgba(255,255,255,0.18);
}}
QPushButton:pressed {{
    background: rgba(255,255,255,0.13);
}}
QPushButton:default {{
    background: rgba(0,229,255,0.14);
    border-color: rgba(0,229,255,0.55);
    color: {CYAN};
}}
QPushButton:default:hover {{
    background: rgba(0,229,255,0.22);
    border-color: {CYAN};
}}
QPushButton:checked {{
    background: rgba(0,229,255,0.14);
    border-color: rgba(0,229,255,0.50);
    color: {CYAN};
}}
QPushButton:disabled {{
    color: {TEXT_MUTED};
    border-color: rgba(255,255,255,0.05);
    background: rgba(255,255,255,0.02);
}}

/* ═══════════════════════════════ SPLITTER ═══════════════════════════════════ */
QSplitter::handle {{
    background: {LINE};
}}
QSplitter::handle:horizontal {{ width: 1px; }}
QSplitter::handle:vertical   {{ height: 1px; }}

/* ═══════════════════════════════ STATUS BAR ══════════════════════════════════ */
QStatusBar {{
    background: {BG_ELEVATED};
    color: {TEXT_MUTED};
    border-top: 1px solid {LINE};
    font-size: 11px;
    padding: 2px 8px;
}}

/* ═══════════════════════════════ SLIDER ═════════════════════════════════════ */
QSlider::groove:horizontal {{
    background: rgba(255,255,255,0.10);
    height: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:horizontal {{
    background: {CYAN};
    height: 4px;
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: white;
    width: 12px;
    height: 12px;
    margin: -4px 0;
    border-radius: 6px;
}}
QSlider::handle:horizontal:hover {{
    background: #00E5FF;
}}
QSlider::groove:vertical {{
    background: rgba(255,255,255,0.10);
    width: 4px;
    border-radius: 2px;
}}
QSlider::sub-page:vertical {{
    background: {CYAN};
}}
QSlider::handle:vertical {{
    background: white;
    width: 12px;
    height: 12px;
    margin: 0 -4px;
    border-radius: 6px;
}}

/* ═══════════════════════════════ CHECKBOX ═══════════════════════════════════ */
QCheckBox {{
    color: {TEXT_PRIMARY};
    spacing: 6px;
    font-size: 12px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border-radius: 3px;
    border: 1px solid #4C4E52;
    background: transparent;
}}
QCheckBox::indicator:hover {{
    border-color: rgba(0,229,255,0.50);
}}
QCheckBox::indicator:checked {{
    background: {CYAN};
    border-color: {CYAN};
}}
QCheckBox::indicator:checked:hover {{
    background: #33EBFF;
}}

/* ═══════════════════════════════ LABEL ══════════════════════════════════════ */
QLabel {{
    color: {TEXT_PRIMARY};
    background: transparent;
}}

/* ═══════════════════════════════ FRAME ══════════════════════════════════════ */
QFrame[frameShape="4"], QFrame[frameShape="5"] {{
    color: {LINE};
    background: {LINE};
}}

/* ═══════════════════════════════ SPIN BOX ═══════════════════════════════════ */
QSpinBox, QDoubleSpinBox {{
    background: #1A1A1C;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 5px 8px;
    font-family: "JetBrains Mono", "Consolas", monospace;
    font-size: 12px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: rgba(0,229,255,0.45);
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    border: none;
    background: transparent;
    width: 14px;
}}

/* ═══════════════════════════════ DIALOGS ════════════════════════════════════ */
QDialog {{
    background: {BG_ELEVATED};
}}
QDialogButtonBox QPushButton {{
    min-width: 90px;
}}
QMessageBox {{
    background: {BG_ELEVATED};
}}
QMessageBox QLabel {{
    color: {TEXT_PRIMARY};
    font-size: 13px;
}}
QInputDialog {{
    background: {BG_ELEVATED};
}}

/* ═══════════════════════════════ FORM LAYOUT ════════════════════════════════ */
QFormLayout QLabel {{
    color: {TEXT_SECONDARY};
    font-size: 12px;
}}

/* ═══════════════════════════════ TEXT EDIT ══════════════════════════════════ */
QTextEdit {{
    background: #1A1A1C;
    border: 1px solid rgba(255,255,255,0.09);
    border-radius: 7px;
    color: {TEXT_PRIMARY};
    padding: 6px;
    font-size: 12px;
}}
QTextEdit:focus {{
    border-color: rgba(0,229,255,0.35);
}}
"""
