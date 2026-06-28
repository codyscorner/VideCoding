COLORS = {
    "bg_dark":      "#1a1a1a",
    "bg_medium":    "#242424",
    "bg_light":     "#2e2e2e",
    "fg_primary":   "#e8e8e8",
    "fg_secondary": "#909090",
    "accent":       "#5e4bdb",
    "accent_hover": "#7060f0",
    "error":        "#ef5350",
    "success":      "#4caf8a",
    "border":       "#3a3a3a",
}

STYLESHEET = f"""
QMainWindow, QDialog {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['fg_primary']};
}}

QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['fg_primary']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

QLabel {{
    color: {COLORS['fg_primary']};
    background-color: transparent;
}}

QLabel#header {{
    font-size: 18px;
    font-weight: bold;
    color: {COLORS['fg_primary']};
    padding: 8px 0px;
}}

QLabel#status {{
    color: {COLORS['fg_secondary']};
    font-size: 12px;
    padding: 2px 0px;
}}

QLineEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 8px;
}}

QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}

QPushButton {{
    background-color: {COLORS['accent']};
    color: {COLORS['fg_primary']};
    border: none;
    border-radius: 4px;
    padding: 6px 16px;
    font-weight: bold;
}}

QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}

QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_secondary']};
}}

QPushButton#browse {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_secondary']};
    font-weight: normal;
    padding: 6px 12px;
}}

QPushButton#browse:hover {{
    background-color: {COLORS['border']};
    color: {COLORS['fg_primary']};
}}

QPushButton#cancel {{
    background-color: {COLORS['error']};
}}

QPushButton#cancel:hover {{
    background-color: #ff6b6b;
}}

QCheckBox {{
    color: {COLORS['fg_secondary']};
    spacing: 6px;
}}

QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['bg_light']};
}}

QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border: 1px solid {COLORS['accent']};
}}

QTableWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    gridline-color: {COLORS['border']};
    selection-background-color: {COLORS['accent']};
}}

QTableWidget::item {{
    padding: 4px 8px;
}}

QHeaderView::section {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_secondary']};
    border: none;
    border-right: 1px solid {COLORS['border']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 5px 8px;
    font-weight: bold;
}}

QHeaderView::section:hover {{
    background-color: {COLORS['border']};
    color: {COLORS['fg_primary']};
}}

QProgressBar {{
    background-color: {COLORS['bg_light']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    text-align: center;
    color: {COLORS['fg_primary']};
    height: 18px;
}}

QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 3px;
}}

QPlainTextEdit {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    font-family: 'Consolas', 'Courier New', monospace;
    font-size: 12px;
}}

QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-height: 20px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: {COLORS['accent']};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}

QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 10px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-width: 20px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['accent']};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}

QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 12px;
}}
"""
