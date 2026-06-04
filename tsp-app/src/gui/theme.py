"""
Temă vizuală centralizată — paletă caldă „Claude" (gri cald + portocaliu).

Toate componentele GUI (fereastra principală, canvas, vizualizare live, panoul
asistentului AI) importă culorile și foaia de stil de aici, astfel încât întreaga
aplicație să aibă un aspect unitar. Pentru a schimba tema, se editează un singur loc.
"""

from __future__ import annotations


# ─── Paletă „warm dark" inspirată din estetica Claude ───────────────────────
BG = "#262624"          # fundal principal (negru cald)
BG_DARK = "#1C1B1A"     # bară de stare / cele mai adânci suprafețe
SURFACE = "#30302E"     # carduri, panouri, câmpuri de input
SURFACE_HI = "#3B3A37"  # hover pe suprafețe
BORDER = "#48463F"      # contur gri-cald
TEXT = "#ECE9DE"        # text principal (alb-cald)
TEXT_MUTED = "#9E9B90"  # text secundar

ACCENT = "#D97757"      # portocaliu „clay" Claude (accent principal)
ACCENT_HI = "#E58E70"   # hover accent
ACCENT_DIM = "#BE5F3E"  # accent apăsat / dezactivat
ON_ACCENT = "#1C1B1A"   # text peste butoane portocalii

# ─── Culori pentru vizualizarea TSP ─────────────────────────────────────────
VIZ_BG = BG
VIZ_BG_DARK = BG_DARK
VIZ_GRID = BORDER
VIZ_CITY = "#D97757"        # orașe — portocaliu
VIZ_CITY_BORDER = "#ECE9DE"  # contur oraș — crem
VIZ_START = "#E5604D"        # orașul de pornire — roșu-portocaliu
VIZ_TOUR = "#E0A458"         # turul curent — chihlimbar (linie principală)
VIZ_BEST = "#ECE9DE"         # cel mai bun tur — crem (underlay discret)


def app_stylesheet() -> str:
    """Foaia de stil globală aplicată pe QApplication / fereastra principală."""
    return f"""
    QMainWindow, QDialog, QWidget {{
        background-color: {BG};
        color: {TEXT};
        font-family: "Segoe UI", "Inter", sans-serif;
        font-size: 13px;
    }}

    QToolBar {{
        background-color: {BG_DARK};
        border: none;
        border-bottom: 1px solid {BORDER};
        padding: 4px;
        spacing: 4px;
    }}
    QToolBar QToolButton, QToolButton {{
        background-color: transparent;
        color: {TEXT};
        border: 1px solid transparent;
        padding: 6px 10px;
        border-radius: 6px;
    }}
    QToolBar QToolButton:hover, QToolButton:hover {{
        background-color: {SURFACE_HI};
        border: 1px solid {BORDER};
    }}
    QToolBar::separator {{
        background-color: {BORDER};
        width: 1px;
        margin: 4px 6px;
    }}

    QPushButton {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {BORDER};
        padding: 7px 14px;
        border-radius: 6px;
    }}
    QPushButton:hover {{ background-color: {SURFACE_HI}; }}
    QPushButton:disabled {{ color: {TEXT_MUTED}; background-color: {BG_DARK}; }}

    /* Buton accent (clasa „accent") */
    QPushButton[accent="true"] {{
        background-color: {ACCENT};
        color: {ON_ACCENT};
        border: 1px solid {ACCENT};
        font-weight: 600;
    }}
    QPushButton[accent="true"]:hover {{ background-color: {ACCENT_HI}; border-color: {ACCENT_HI}; }}
    QPushButton[accent="true"]:disabled {{ background-color: {ACCENT_DIM}; color: {TEXT_MUTED}; border-color: {ACCENT_DIM}; }}

    QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit, QTextEdit, QPlainTextEdit {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {BORDER};
        padding: 5px 6px;
        border-radius: 6px;
        selection-background-color: {ACCENT};
        selection-color: {ON_ACCENT};
    }}
    QComboBox:hover, QSpinBox:hover, QDoubleSpinBox:hover, QLineEdit:hover {{ border-color: {ACCENT_DIM}; }}
    QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus,
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus {{ border-color: {ACCENT}; }}
    QComboBox QAbstractItemView {{
        background-color: {SURFACE};
        color: {TEXT};
        border: 1px solid {BORDER};
        selection-background-color: {ACCENT};
        selection-color: {ON_ACCENT};
    }}

    QGroupBox {{
        border: 1px solid {BORDER};
        margin-top: 10px;
        padding-top: 14px;
        border-radius: 8px;
        font-weight: 600;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 10px;
        padding: 0 5px;
        color: {ACCENT};
    }}

    QLabel {{ color: {TEXT}; }}
    QCheckBox {{ color: {TEXT}; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 16px; height: 16px;
        border: 1px solid {BORDER};
        border-radius: 4px;
        background-color: {SURFACE};
    }}
    QCheckBox::indicator:checked {{ background-color: {ACCENT}; border-color: {ACCENT}; }}

    QStatusBar {{ background-color: {BG_DARK}; color: {TEXT_MUTED}; border-top: 1px solid {BORDER}; }}
    QStatusBar::item {{ border: none; }}

    QScrollArea {{ border: none; }}
    QSplitter::handle {{ background-color: {BORDER}; }}
    QSplitter::handle:horizontal {{ width: 2px; }}
    QSplitter::handle:vertical {{ height: 2px; }}

    QProgressBar {{
        background-color: {SURFACE};
        border: 1px solid {BORDER};
        border-radius: 6px;
        text-align: center;
        color: {TEXT};
    }}
    QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 5px; }}

    QMenu {{ background-color: {SURFACE}; color: {TEXT}; border: 1px solid {BORDER}; }}
    QMenu::item:selected {{ background-color: {ACCENT}; color: {ON_ACCENT}; }}

    QDockWidget {{ color: {TEXT}; titlebar-close-icon: none; }}
    QDockWidget::title {{
        background-color: {BG_DARK};
        padding: 6px 8px;
        border-bottom: 1px solid {BORDER};
    }}

    QScrollBar:vertical {{ background: {BG}; width: 12px; margin: 0; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; min-height: 24px; border-radius: 6px; }}
    QScrollBar::handle:vertical:hover {{ background: {ACCENT_DIM}; }}
    QScrollBar:horizontal {{ background: {BG}; height: 12px; margin: 0; }}
    QScrollBar::handle:horizontal {{ background: {BORDER}; min-width: 24px; border-radius: 6px; }}
    QScrollBar::handle:horizontal:hover {{ background: {ACCENT_DIM}; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; width: 0; }}
    QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

    QToolTip {{ background-color: {BG_DARK}; color: {TEXT}; border: 1px solid {ACCENT_DIM}; padding: 4px; }}
    """
