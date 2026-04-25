"""Dark yellow/gold theme for File Copy Manager"""

COLORS = {
    'background':      '#1a1a1a',
    'bg_mid':          '#2d2d2d',
    'bg_light':        '#3a3a3a',
    'foreground':      '#FFD700',
    'input_bg':        '#2d2d2d',
    'input_fg':        '#FFFF00',
    'button_bg':       '#FFD700',
    'button_fg':       '#000000',
    'button_active':   '#FFA500',
    'button_hover':    '#FFED4E',
    'select_bg':       '#FFD700',
    'select_fg':       '#000000',
    'scrollbar_bg':    '#333333',
    'accent':          '#FFD700',
    'accent_hover':    '#FFED4E',
    'border':          '#444444',
    'error':           '#ff6b6b',
    'success':         '#7ddc7d',
    'fg_dim':          '#888888',
    'fg_secondary':    '#ccaa00',
}

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {COLORS['background']};
    color: {COLORS['foreground']};
    font-family: Arial;
    font-size: 10pt;
}}
QLabel {{
    background-color: transparent;
    color: {COLORS['foreground']};
}}
QLabel#title_label {{
    font-size: 14pt;
    font-weight: bold;
}}
QLabel#subtitle_label {{
    font-size: 9pt;
    font-style: italic;
    color: {COLORS['fg_secondary']};
}}
QLabel#section_label {{
    font-size: 12pt;
    font-weight: bold;
}}
QLabel#dim_label {{
    color: {COLORS['fg_dim']};
    font-size: 9pt;
    font-style: italic;
}}
QGroupBox {{
    border: 1px solid {COLORS['border']};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 8px;
    color: {COLORS['foreground']};
    font-weight: bold;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
}}
QLineEdit {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['input_fg']};
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    padding: 4px 6px;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QCheckBox {{
    color: {COLORS['foreground']};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    background-color: {COLORS['input_bg']};
}}
QCheckBox::indicator:checked {{
    background-color: {COLORS['accent']};
    border-color: {COLORS['accent']};
}}
QComboBox {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['foreground']};
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
    padding: 4px 6px;
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['button_fg']};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['foreground']};
    selection-background-color: {COLORS['accent']};
    selection-color: {COLORS['button_fg']};
    border: 1px solid {COLORS['border']};
}}
QPushButton {{
    background-color: {COLORS['button_bg']};
    color: {COLORS['button_fg']};
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 8px 20px;
    font-size: 12pt;
}}
QPushButton:hover {{
    background-color: {COLORS['button_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#cancel_btn {{
    background-color: #8B0000;
    color: {COLORS['foreground']};
}}
QPushButton#cancel_btn:hover {{
    background-color: #a00000;
}}
QProgressBar {{
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    background-color: {COLORS['bg_light']};
    height: 20px;
    text-align: center;
    color: {COLORS['background']};
}}
QProgressBar::chunk {{
    background-color: {COLORS['accent']};
    border-radius: 2px;
}}
QListWidget {{
    background-color: {COLORS['input_bg']};
    color: {COLORS['input_fg']};
    border: 1px solid {COLORS['border']};
    border-radius: 2px;
}}
QListWidget::item:selected {{
    background-color: {COLORS['select_bg']};
    color: {COLORS['select_fg']};
}}
QScrollBar:vertical {{
    background-color: {COLORS['background']};
    width: 12px;
    border: none;
}}
QScrollBar::handle:vertical {{
    background-color: {COLORS['scrollbar_bg']};
    border-radius: 6px;
    min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
}}
QScrollBar:horizontal {{
    background-color: {COLORS['background']};
    height: 12px;
    border: none;
}}
QScrollBar::handle:horizontal {{
    background-color: {COLORS['scrollbar_bg']};
    border-radius: 6px;
    min-width: 20px;
}}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
}}
QLabel#clear_label {{
    color: {COLORS['accent']};
    text-decoration: underline;
    font-size: 11px;
}}
QLabel#clear_label:hover {{
    color: {COLORS['accent_hover']};
}}
"""
