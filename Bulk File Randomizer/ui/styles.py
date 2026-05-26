"""Stylesheet for Bulk File Randomizer"""

COLORS = {
    "bg":          "#1e1e2e",
    "surface":     "#2a2a3d",
    "border":      "#3d3d56",
    "accent":      "#7c6af7",
    "accent_hover":"#9b8dff",
    "text":        "#cdd6f4",
    "dim":         "#6c7086",
    "success":     "#a6e3a1",
    "error":       "#f38ba8",
    "cancel":      "#f38ba8",
    "cancel_hover":"#ff9999",
}

STYLESHEET = f"""
QWidget {{
    background-color: {COLORS['bg']};
    color: {COLORS['text']};
    font-family: 'Segoe UI', Arial, sans-serif;
    font-size: 13px;
}}

QMainWindow {{
    background-color: {COLORS['bg']};
}}

QScrollArea, QScrollArea > QWidget > QWidget {{
    background-color: {COLORS['bg']};
    border: none;
}}

QLabel#title_label {{
    font-size: 22px;
    font-weight: bold;
    color: {COLORS['accent']};
    padding: 6px 0;
}}

QLabel#subtitle_label {{
    font-size: 12px;
    color: {COLORS['dim']};
    padding-bottom: 8px;
}}

QLabel#section_label {{
    font-size: 13px;
    font-weight: bold;
    color: {COLORS['accent']};
    padding-top: 6px;
}}

QLabel#dim_label {{
    color: {COLORS['dim']};
    font-size: 11px;
}}

QLabel#preview_label {{
    color: {COLORS['success']};
    font-size: 12px;
    padding: 2px 0;
}}

QLabel#clear_label {{
    color: {COLORS['accent']};
    font-size: 11px;
}}
QLabel#clear_label:hover {{
    color: {COLORS['accent_hover']};
    text-decoration: underline;
}}

QLineEdit {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 8px;
    color: {COLORS['text']};
}}
QLineEdit:focus {{
    border-color: {COLORS['accent']};
}}

QComboBox {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 5px 8px;
    color: {COLORS['text']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    selection-background-color: {COLORS['accent']};
}}

QPushButton {{
    background-color: {COLORS['accent']};
    color: #ffffff;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    font-weight: bold;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['border']};
    color: {COLORS['dim']};
}}

QPushButton#cancel_btn {{
    background-color: {COLORS['cancel']};
}}
QPushButton#cancel_btn:hover {{
    background-color: {COLORS['cancel_hover']};
}}

QCheckBox {{
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background: {COLORS['surface']};
}}
QCheckBox::indicator:checked {{
    background: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}

QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    background-color: {COLORS['surface']};
    height: 18px;
    text-align: center;
    color: {COLORS['text']};
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 3px;
}}

QListWidget {{
    background-color: {COLORS['surface']};
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    padding: 4px;
}}
QListWidget::item {{
    padding: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: #ffffff;
}}

QScrollBar:vertical {{
    background: {COLORS['surface']};
    width: 10px;
    border-radius: 5px;
}}
QScrollBar::handle:vertical {{
    background: {COLORS['border']};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0;
}}
"""
