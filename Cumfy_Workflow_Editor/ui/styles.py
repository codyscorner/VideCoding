COLORS = {
    "bg_dark":      "#0d0d1a",
    "bg_medium":    "#1a1a2e",
    "bg_light":     "#16213e",
    "bg_card":      "#1e1e35",
    "fg_primary":   "#e0e0ff",
    "fg_secondary": "#9090cc",
    "fg_dim":       "#505080",
    "accent":       "#5e4bdb",
    "accent_hover": "#7b6cf0",
    "accent_dark":  "#3d2fb0",
    "border":       "#2a2a4a",
    "border_card":  "#2e2e50",
    # node-type accent colors
    "prompt_color":     "#4caf8a",
    "lora_color":       "#9c6fdb",
    "sampler_color":    "#ffb74d",
    "checkpoint_color": "#4fc3f7",
    "output_color":     "#f06292",
    "media_color":      "#26c6da",
    "generic_color":    "#606090",
    "success": "#4caf8a",
    "error":   "#ef5350",
    "warning": "#ffb74d",
}

APP_STYLESHEET = f"""
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
QMenuBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border-bottom: 1px solid {COLORS['border']};
    padding: 2px 4px;
}}
QMenuBar::item:selected {{
    background-color: {COLORS['accent']};
    border-radius: 3px;
}}
QMenu {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
}}
QMenu::item:selected {{
    background-color: {COLORS['accent']};
}}
QMenu::separator {{
    height: 1px;
    background: {COLORS['border']};
    margin: 3px 0;
}}
QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border-top: 1px solid {COLORS['border']};
}}
QToolBar {{
    background-color: {COLORS['bg_medium']};
    border-bottom: 1px solid {COLORS['border']};
    spacing: 4px;
    padding: 4px 6px;
}}
QToolBar::separator {{
    background: {COLORS['border']};
    width: 1px;
    margin: 4px 2px;
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 6px 18px;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 10px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 10px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 5px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0px; }}
"""

CARD_STYLESHEET = f"""
QFrame#card {{
    background-color: {COLORS['bg_card']};
    border: 1px solid {COLORS['border_card']};
    border-radius: 6px;
}}
QTextEdit {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: "Segoe UI";
    font-size: 9pt;
    padding: 4px;
}}
QTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QLineEdit {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 3px 7px;
    font-size: 9pt;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {COLORS['border']};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {COLORS['accent_hover']};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS['accent']};
    border-radius: 2px;
}}
QSpinBox, QDoubleSpinBox {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 2px 6px;
}}
QSpinBox:focus, QDoubleSpinBox:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 3px 8px;
}}
QComboBox:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    selection-background-color: {COLORS['accent']};
    border: 1px solid {COLORS['border']};
}}
"""
