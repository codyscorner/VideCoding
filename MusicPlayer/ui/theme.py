"""Dark-blue theme for Music Player.

A single Qt stylesheet string applied app-wide in main.py. Palette:
  base bg     #0d1b2a   (darkest — window)
  panel bg    #12233a   (tables, inputs)
  panel alt   #1b2f4a   (alternating rows / hover)
  border      #2a4a6e
  accent      #3d8bfd   (buttons, selection, seek)
  accent hi   #5a9ffd
  text        #e6edf5
  text dim    #8aa0b8
"""

DARK_BLUE_QSS = """
* {
    color: #e6edf5;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMainWindow, QWidget {
    background-color: #0d1b2a;
}

/* --- Toolbar --- */
QToolBar {
    background-color: #12233a;
    border: none;
    border-bottom: 1px solid #2a4a6e;
    padding: 4px;
    spacing: 6px;
}

/* --- Buttons --- */
QPushButton {
    background-color: #1b2f4a;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    padding: 5px 12px;
}
QPushButton:hover {
    background-color: #24406a;
    border-color: #3d8bfd;
}
QPushButton:pressed {
    background-color: #3d8bfd;
    color: #ffffff;
}
QPushButton:disabled {
    color: #8aa0b8;
    background-color: #16273f;
}

/* --- Mode buttons (shuffle/repeat) when active --- */
QPushButton#modeBtn:checked {
    background-color: #3d8bfd;
    color: #ffffff;
    border-color: #3d8bfd;
}

/* --- Checkbox --- */
QCheckBox {
    spacing: 6px;
}
QCheckBox::indicator {
    width: 16px;
    height: 16px;
    border: 1px solid #2a4a6e;
    border-radius: 3px;
    background-color: #12233a;
}
QCheckBox::indicator:checked {
    background-color: #3d8bfd;
    border-color: #3d8bfd;
}

/* --- Line edit (search) --- */
QLineEdit {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: #3d8bfd;
}
QLineEdit:focus {
    border-color: #3d8bfd;
}

/* --- Playlist table --- */
QTableView {
    background-color: #0f1e30;
    alternate-background-color: #14263d;
    gridline-color: #1b2f4a;
    border: 1px solid #2a4a6e;
    selection-background-color: #3d8bfd;
    selection-color: #ffffff;
    outline: none;
}
QTableView::item {
    padding: 3px 6px;
}
QHeaderView::section {
    background-color: #1b2f4a;
    color: #cbd8e6;
    padding: 6px 8px;
    border: none;
    border-right: 1px solid #0d1b2a;
    border-bottom: 1px solid #2a4a6e;
}
QHeaderView::section:hover {
    background-color: #24406a;
}

/* --- Playlist sidebar --- */
QWidget#sidebar {
    background-color: #0f1e30;
    border-right: 1px solid #2a4a6e;
}
QListWidget {
    background-color: #0f1e30;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    outline: none;
    padding: 2px;
}
QListWidget::item {
    padding: 6px 6px;
    border-radius: 3px;
}
QListWidget::item:selected {
    background-color: #3d8bfd;
    color: #ffffff;
}
QListWidget::item:hover:!selected {
    background-color: #1b2f4a;
}

/* --- Scrollbars --- */
QScrollBar:vertical {
    background: #0d1b2a;
    width: 12px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2a4a6e;
    min-height: 24px;
    border-radius: 6px;
}
QScrollBar::handle:vertical:hover {
    background: #3d8bfd;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

/* --- Sliders (seek / volume) --- */
QSlider::groove:horizontal {
    height: 5px;
    background: #1b2f4a;
    border-radius: 2px;
}
QSlider::sub-page:horizontal {
    background: #3d8bfd;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #e6edf5;
    width: 13px;
    height: 13px;
    margin: -5px 0;
    border-radius: 6px;
}
QSlider::handle:horizontal:hover {
    background: #5a9ffd;
}

/* --- Now-playing label --- */
QLabel#nowPlaying {
    color: #5a9ffd;
    font-weight: bold;
}

/* --- Album art thumbnail --- */
QLabel#albumArt {
    border: 1px solid #2a4a6e;
    border-radius: 3px;
    background: #12233a;
}

/* --- Status bar --- */
QStatusBar {
    background-color: #12233a;
    color: #8aa0b8;
    border-top: 1px solid #2a4a6e;
}
"""
