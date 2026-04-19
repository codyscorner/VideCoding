"""Theme and styling management for Frame Extractor application"""


COLORS = {
    'background': '#1a1a1a',
    'foreground': '#FFA500',
    'input_bg': '#2d2d2d',
    'input_fg': '#FF8C00',
    'button_bg': '#FFA500',
    'button_fg': '#000000',
    'button_active': '#FF8C00',
    'button_hover': '#FFB732',
    'accent': '#333333',
    'select_bg': '#FFA500',
    'select_fg': '#000000',
    'scrollbar_bg': '#333333',
    'scrollbar_trough': '#1a1a1a',
}

STYLESHEET = """
QWidget {
    background-color: #1a1a1a;
    color: #FFA500;
    font-family: Arial;
    font-size: 10pt;
}

QLabel {
    background-color: transparent;
}

QLineEdit, QListWidget {
    background-color: #2d2d2d;
    color: #FF8C00;
    border: 1px solid #333333;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #FFA500;
    selection-color: #000000;
}

QComboBox {
    background-color: #2d2d2d;
    color: #FF8C00;
    border: 1px solid #333333;
    border-radius: 3px;
    padding: 2px 4px;
    selection-background-color: #FFA500;
    selection-color: #000000;
}

QComboBox::drop-down {
    border: none;
    width: 20px;
}

QComboBox QAbstractItemView {
    background-color: #2d2d2d;
    color: #FF8C00;
    selection-background-color: #FFA500;
    selection-color: #000000;
    border: 1px solid #333333;
}

QPushButton {
    background-color: #FFA500;
    color: #000000;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 5px 12px;
}

QPushButton:hover {
    background-color: #FFB732;
}

QPushButton:pressed {
    background-color: #FF8C00;
}

QScrollBar:vertical {
    background-color: #1a1a1a;
    width: 12px;
    border: none;
}

QScrollBar::handle:vertical {
    background-color: #333333;
    border-radius: 6px;
    min-height: 20px;
}

QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {
    height: 0px;
}

QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {
    background: none;
}
"""
