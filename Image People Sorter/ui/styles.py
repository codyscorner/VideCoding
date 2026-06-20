"""Dark orange/amber theme for Image People Sorter"""

COLORS = {
    'bg_dark':      '#1a1000',
    'bg_medium':    '#2e1f00',
    'bg_light':     '#3d2b00',
    'fg_primary':   '#fff3e0',
    'fg_secondary': '#ffcc80',
    'fg_dim':       '#a07840',
    'accent':       '#e65100',
    'accent_hover': '#ff6d00',
    'accent_dark':  '#bf360c',
    'border':       '#5c3a00',
    'success':      '#a5d6a7',
    'error':        '#ef9a9a',
    'progress_bg':  '#2e1f00',
    'progress_fg':  '#e65100',
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
    font-size: 10pt;
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
QRadioButton {{
    color: {COLORS['fg_primary']};
    spacing: 6px;
}}
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 7px;
    background-color: {COLORS['bg_light']};
}}
QRadioButton::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 10px 30px;
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
QPlainTextEdit {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
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
"""
