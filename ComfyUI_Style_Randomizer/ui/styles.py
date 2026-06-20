COLORS = {
    'bg_dark':      '#0d0d1a',
    'bg_medium':    '#1a1a2e',
    'bg_light':     '#16213e',
    'fg_primary':   '#e0e0ff',
    'fg_secondary': '#9090cc',
    'fg_dim':       '#505080',
    'accent':       '#5e4bdb',
    'accent_hover': '#7b6cf0',
    'accent_dark':  '#3d2fb0',
    'border':       '#2a2a4a',
    'success':      '#4caf8a',
    'error':        '#ef5350',
    'warning':      '#ffb74d',
    'progress_bg':  '#1a1a2e',
    'progress_fg':  '#5e4bdb',
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
QLabel#subtitle {{
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
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
QRadioButton {{
    color: {COLORS['fg_primary']};
    font-size: 11pt;
    font-weight: bold;
    spacing: 8px;
    padding: 4px 12px;
}}
QRadioButton::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 9px;
    border: 2px solid {COLORS['border']};
    background-color: {COLORS['bg_light']};
}}
QRadioButton::indicator:checked {{
    background-color: {COLORS['accent']};
    border: 2px solid {COLORS['accent_hover']};
}}
QRadioButton::indicator:hover {{
    border: 2px solid {COLORS['accent_hover']};
}}
QCheckBox {{
    color: {COLORS['fg_primary']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px;
    height: 16px;
    border: 2px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['bg_light']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border: 2px solid {COLORS['accent_hover']};
}}
QLineEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 5px 8px;
    font-size: 10pt;
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
    padding: 10px 28px;
    font-size: 11pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#small_btn {{
    padding: 5px 10px;
    font-size: 9pt;
    font-weight: normal;
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
QListWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item {{
    padding: 2px 4px;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
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
QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    font-size: 9pt;
}}
"""
