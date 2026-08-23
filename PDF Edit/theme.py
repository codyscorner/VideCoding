"""Dark green application theme (QSS)."""

# Palette
BG = "#0e1813"          # window background
PANEL = "#152219"       # panels / bars
PANEL_2 = "#1b2c21"     # raised elements
BORDER = "#2b4636"
ACCENT = "#2e7d4f"      # primary green
ACCENT_HI = "#3fa46a"   # hover / highlight
TEXT = "#d7e8dd"
TEXT_DIM = "#8fae9c"

DARK_GREEN_QSS = f"""
QWidget {{
    background: {BG};
    color: {TEXT};
    font-size: 10pt;
}}
QMainWindow, QDialog {{ background: {BG}; }}

QMenuBar {{ background: {PANEL}; border-bottom: 1px solid {BORDER}; }}
QMenuBar::item {{ padding: 4px 10px; background: transparent; }}
QMenuBar::item:selected {{ background: {ACCENT}; color: white; }}
QMenu {{ background: {PANEL_2}; border: 1px solid {BORDER}; }}
QMenu::item {{ padding: 5px 24px 5px 16px; }}
QMenu::item:selected {{ background: {ACCENT}; color: white; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}
QMenu::item:disabled {{ color: {TEXT_DIM}; }}

QToolBar {{
    background: {PANEL};
    border-bottom: 1px solid {BORDER};
    spacing: 3px;
    padding: 3px;
}}
QToolBar::separator {{ width: 1px; background: {BORDER}; margin: 4px 4px; }}
QToolButton {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 4px 7px;
}}
QToolButton:hover {{ background: {PANEL_2}; border-color: {BORDER}; }}
QToolButton:checked {{ background: {ACCENT}; color: white; }}
QToolButton:disabled {{ color: {TEXT_DIM}; }}

QPushButton {{
    background: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 5px 14px;
}}
QPushButton:hover {{ background: {ACCENT}; color: white; }}
QPushButton:default {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: {TEXT_DIM}; background: {PANEL}; }}

QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QPlainTextEdit, QTextEdit {{
    background: {PANEL_2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 3px 6px;
    selection-background-color: {ACCENT};
}}
QLineEdit:focus, QSpinBox:focus, QPlainTextEdit:focus {{
    border-color: {ACCENT_HI};
}}

QListWidget {{
    background: {PANEL};
    border: none;
    border-right: 1px solid {BORDER};
    outline: none;
}}
QListWidget::item {{
    padding: 6px;
    margin: 4px;
    border: 1px solid {BORDER};
    border-radius: 4px;
    background: {PANEL_2};
}}
QListWidget::item:selected {{ border: 2px solid {ACCENT_HI}; background: #1f3a2a; }}
QListWidget::item:hover {{ border-color: {ACCENT}; }}

QScrollArea {{ border: none; background: {BG}; }}
QScrollBar:vertical {{
    background: {PANEL}; width: 12px; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 5px; min-height: 30px; margin: 2px;
}}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{
    background: {PANEL}; height: 12px; margin: 0;
}}
QScrollBar::handle:horizontal {{
    background: {BORDER}; border-radius: 5px; min-width: 30px; margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

QStatusBar {{
    background: {PANEL};
    border-top: 1px solid {BORDER};
    color: {TEXT_DIM};
}}
QStatusBar::item {{ border: none; }}

QSlider::groove:horizontal {{
    height: 4px; background: {BORDER}; border-radius: 2px;
}}
QSlider::handle:horizontal {{
    width: 14px; margin: -6px 0; border-radius: 7px; background: {ACCENT_HI};
}}

QSplitter::handle {{ background: {BORDER}; width: 2px; }}

QMessageBox, QInputDialog {{ background: {PANEL_2}; }}

QToolTip {{
    background: {PANEL_2}; color: {TEXT};
    border: 1px solid {ACCENT}; padding: 3px;
}}
"""
