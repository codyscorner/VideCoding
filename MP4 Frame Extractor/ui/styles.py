COLORS = {
    'bg_dark':      '#0e0905',
    'bg_medium':    '#1a1008',
    'bg_light':     '#231608',
    'fg_primary':   '#f2d9b8',
    'fg_secondary': '#b8895a',
    'fg_dim':       '#6b5030',
    'accent':       '#c04a08',
    'accent_hover': '#e05c0a',
    'accent_dark':  '#7a2e05',
    'border':       '#3d2210',
    'success':      '#5faa3e',
    'error':        '#e04040',
    'warning':      '#d4980a',
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
QLabel#header {{
    color: {COLORS['accent_hover']};
    font-size: 16pt;
    font-weight: bold;
}}
QLabel#section {{
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
    font-weight: bold;
}}
QLineEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 6px 8px;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 6px 10px;
}}
QComboBox:focus {{
    border: 1px solid {COLORS['accent']};
}}
QComboBox::drop-down {{
    border: none;
    width: 24px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    selection-background-color: {COLORS['accent']};
    border: 1px solid {COLORS['border']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: {COLORS['fg_primary']};
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 10px 28px;
    font-size: 11pt;
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
QPushButton#browse_btn {{
    padding: 6px 12px;
    font-size: 10pt;
}}
QLabel#preview {{
    background-color: {COLORS['bg_medium']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    color: {COLORS['fg_dim']};
}}
QListWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item {{
    padding: 1px 4px;
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
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
"""
