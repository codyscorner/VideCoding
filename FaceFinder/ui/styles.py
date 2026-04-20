"""Dark gold/amber theme for FaceFinder"""

COLORS = {
    'bg_dark':      '#1a1600',
    'bg_medium':    '#2e2500',
    'bg_light':     '#3d3100',
    'fg_primary':   '#fff8e1',
    'fg_secondary': '#ffe082',
    'fg_dim':       '#a08830',
    'accent':       '#f9a825',
    'accent_hover': '#fdd835',
    'accent_dark':  '#c17900',
    'border':       '#5c4a00',
    'success':      '#a5d6a7',
    'error':        '#ef9a9a',
    'progress_bg':  '#2e2500',
    'progress_fg':  '#f9a825',
    'match_bg':     '#3d3100',
    'thumb_hover':  '#5c4a00',
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
QLabel#header {{
    color: {COLORS['accent_hover']};
    font-size: 18pt;
    font-weight: bold;
}}
QLabel#drop_zone {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border: 2px dashed {COLORS['accent']};
    border-radius: 6px;
    font-style: italic;
    padding: 14px;
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding: 8px;
    color: {COLORS['accent_hover']};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
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
QCheckBox {{
    color: {COLORS['fg_primary']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    background-color: {COLORS['bg_light']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QSlider::groove:horizontal {{
    height: 6px;
    background: {COLORS['bg_light']};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {COLORS['accent']};
    width: 16px;
    height: 16px;
    margin: -5px 0;
    border-radius: 8px;
}}
QSlider::sub-page:horizontal {{
    background: {COLORS['accent']};
    border-radius: 3px;
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: #1a1600;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 10px 26px;
    font-size: 11pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#cancel_btn {{
    background-color: {COLORS['accent_dark']};
    color: {COLORS['fg_primary']};
}}
QPushButton#cancel_btn:hover {{
    background-color: {COLORS['error']};
    color: white;
}}
QPushButton#secondary_btn {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    font-weight: normal;
    padding: 7px 14px;
    font-size: 9pt;
}}
QPushButton#secondary_btn:hover {{
    background-color: {COLORS['accent_dark']};
    color: white;
}}
QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['progress_bg']};
    height: 22px;
    text-align: center;
    color: {COLORS['fg_primary']};
}}
QProgressBar::chunk {{
    background-color: {COLORS['progress_fg']};
    border-radius: 2px;
}}
QListWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: #1a1600;
}}
QScrollBar:vertical {{
    background-color: {COLORS['bg_dark']};
    width: 12px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {COLORS['bg_dark']};
    height: 12px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['border']};
    border-radius: 6px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
"""
