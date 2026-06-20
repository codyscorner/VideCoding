COLORS = {
    "bg_dark":       "#0d1117",
    "bg_medium":     "#161b27",
    "bg_light":      "#1f2937",
    "fg_primary":    "#e2e8f0",
    "fg_secondary":  "#94a3b8",
    "fg_dim":        "#4a5568",
    "accent":        "#0d9488",
    "accent_hover":  "#14b8a6",
    "accent_dark":   "#0f766e",
    "accent_purple": "#7c3aed",
    "border":        "#2d3748",
    "filmstrip_bg":  "#111827",
    "viewer_bg":     "#0a0f1a",
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['bg_dark']};
    color: {COLORS['fg_primary']};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QLabel {{
    background-color: transparent;
    color: {COLORS['fg_primary']};
}}
QLabel#subtitle {{
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
}}
QLabel#image_viewer {{
    background-color: {COLORS['viewer_bg']};
    color: {COLORS['fg_dim']};
    font-size: 12pt;
}}
QLineEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 6px;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 7px 18px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:pressed {{
    background-color: {COLORS['accent_dark']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#slideshow_btn {{
    background-color: {COLORS['accent_purple']};
}}
QPushButton#slideshow_btn:hover {{
    background-color: #8b5cf6;
}}
QPushButton#slideshow_btn:pressed {{
    background-color: #6d28d9;
}}
QPushButton#slideshow_btn:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QDoubleSpinBox, QSpinBox {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px 6px;
}}
QDoubleSpinBox:focus, QSpinBox:focus {{
    border: 1px solid {COLORS['accent']};
}}
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
QSpinBox::up-button, QSpinBox::down-button {{
    background-color: {COLORS['bg_medium']};
    border: none;
    width: 16px;
}}
QDoubleSpinBox::up-button:hover, QDoubleSpinBox::down-button:hover,
QSpinBox::up-button:hover, QSpinBox::down-button:hover {{
    background-color: {COLORS['accent']};
}}
QListWidget {{
    background-color: {COLORS['filmstrip_bg']};
    border: none;
    border-right: 1px solid {COLORS['border']};
    outline: none;
}}
QListWidget::item {{
    padding: 3px 2px;
    border-bottom: 1px solid {COLORS['border']};
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
}}
QListWidget::item:hover:!selected {{
    background-color: {COLORS['bg_medium']};
}}
QSplitter::handle {{
    background-color: {COLORS['border']};
    width: 2px;
}}
QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
    border-top: 1px solid {COLORS['border']};
}}
QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 10px;
    border: none;
    margin: 0;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-height: 20px;
    margin: 2px;
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
    border: none;
    margin: 0;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-width: 20px;
    margin: 2px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {COLORS['accent']};
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QToolTip {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    padding: 4px;
}}
"""
