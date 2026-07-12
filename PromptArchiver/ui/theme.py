"""Dark-blue theme for Prompt Archiver.

Same palette as the other VibeCoded apps (Music Player etc.):
  base bg     #0d1b2a   (darkest — window)
  panel bg    #12233a   (cards, inputs)
  panel alt   #1b2f4a   (hover / chips)
  border      #2a4a6e
  accent      #3d8bfd   (buttons, selection)
  accent hi   #5a9ffd
  text        #e6edf5
  text dim    #8aa0b8

Type badge colors carried over from the v1.x MUI app:
  text=blue #3d8bfd, image=purple #b06ad4, video=green #4caf7d
Star gold #ffd700.
"""

TYPE_COLORS = {
    "text": "#3d8bfd",
    "image": "#b06ad4",
    "video": "#4caf7d",
}

STAR_FILLED = "#ffd700"
STAR_EMPTY = "#4a5a70"

DARK_BLUE_QSS = """
* {
    color: #e6edf5;
    font-family: "Segoe UI";
    font-size: 10pt;
}

QMainWindow, QDialog, QWidget {
    background-color: #0d1b2a;
}

QMenuBar {
    background-color: #12233a;
    border-bottom: 1px solid #2a4a6e;
}
QMenuBar::item:selected {
    background-color: #24406a;
}
QMenu {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
}
QMenu::item {
    padding: 5px 24px 5px 12px;
}
QMenu::item:selected {
    background-color: #3d8bfd;
    color: #ffffff;
}
QMenu::separator {
    height: 1px;
    background: #2a4a6e;
    margin: 4px 8px;
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
QPushButton#primaryBtn {
    background-color: #3d8bfd;
    color: #ffffff;
    border-color: #3d8bfd;
    font-weight: bold;
}
QPushButton#primaryBtn:hover {
    background-color: #5a9ffd;
}
QPushButton#primaryBtn:disabled {
    background-color: #24406a;
    color: #8aa0b8;
}
QPushButton#dangerBtn {
    background-color: #b3403f;
    color: #ffffff;
    border-color: #b3403f;
    font-weight: bold;
}
QPushButton#dangerBtn:hover {
    background-color: #d05150;
}

/* --- Checkbox --- */
QCheckBox {
    spacing: 6px;
    background: transparent;
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

/* --- Inputs --- */
QLineEdit, QPlainTextEdit, QTextEdit {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    padding: 5px 8px;
    selection-background-color: #3d8bfd;
}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus {
    border-color: #3d8bfd;
}

QComboBox {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    padding: 5px 8px;
}
QComboBox:hover {
    border-color: #3d8bfd;
}
QComboBox::drop-down {
    border: none;
    width: 20px;
}
QComboBox QAbstractItemView {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    selection-background-color: #3d8bfd;
    selection-color: #ffffff;
    outline: none;
}

/* --- Lists --- */
QListWidget {
    background-color: #0f1e30;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    outline: none;
    padding: 2px;
}
QListWidget::item {
    border-radius: 3px;
    border-bottom: 1px solid #1b2f4a;
}
QListWidget::item:selected {
    background-color: #1f3d63;
}
QListWidget::item:hover:!selected {
    background-color: #16273f;
}

/* --- Tabs --- */
QTabWidget::pane {
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    top: -1px;
}
QTabBar::tab {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
    padding: 6px 14px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1f3d63;
    border-color: #3d8bfd;
}
QTabBar::tab:hover:!selected {
    background-color: #1b2f4a;
}

/* --- Cards / panels --- */
QFrame#card {
    background-color: #12233a;
    border: 1px solid #2a4a6e;
    border-radius: 6px;
}
QWidget#sidebar {
    background-color: #0f1e30;
    border-right: 1px solid #2a4a6e;
}

/* --- Prompt text boxes --- */
QPlainTextEdit#promptBox {
    background-color: #16273f;
    font-family: "Consolas", monospace;
}
QPlainTextEdit#negativePromptBox {
    background-color: #2d1e2a;
    border-color: #5e3a4a;
    font-family: "Consolas", monospace;
}

/* --- Drop zone --- */
QFrame#dropZone {
    background-color: #0f1e30;
    border: 2px dashed #2a4a6e;
    border-radius: 6px;
}
QFrame#dropZone[dragActive="true"] {
    border-color: #3d8bfd;
    background-color: #16304f;
}

/* --- Labels --- */
QLabel {
    background: transparent;
}
QLabel#dimLabel {
    color: #8aa0b8;
}
QLabel#titleLabel {
    font-size: 15pt;
    font-weight: bold;
    color: #5a9ffd;
}
QLabel#sectionLabel {
    font-weight: bold;
    color: #cbd8e6;
}
QLabel#infoNote {
    background-color: #16304f;
    border: 1px solid #2a4a6e;
    border-radius: 4px;
    padding: 8px;
    color: #cbd8e6;
}
QLabel#warnNote {
    background-color: #3a2c18;
    border: 1px solid #6e5a2a;
    border-radius: 4px;
    padding: 8px;
    color: #e6d8b8;
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
QScrollBar:horizontal {
    background: #0d1b2a;
    height: 12px;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background: #2a4a6e;
    min-width: 24px;
    border-radius: 6px;
}
QScrollBar::handle:horizontal:hover {
    background: #3d8bfd;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* --- Sliders (video seek) --- */
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

/* --- Status bar --- */
QStatusBar {
    background-color: #12233a;
    color: #8aa0b8;
    border-top: 1px solid #2a4a6e;
}

/* --- Splitter --- */
QSplitter::handle {
    background-color: #2a4a6e;
    width: 2px;
}

/* --- Scroll areas --- */
QScrollArea {
    border: none;
    background: transparent;
}
"""


def type_badge_style(ptype: str) -> str:
    """Stylesheet for the small colored type badge label."""
    color = TYPE_COLORS.get(ptype, "#8aa0b8")
    return (
        f"background-color: {color}; color: #ffffff; font-weight: bold;"
        "border-radius: 8px; padding: 1px 8px; font-size: 8pt;"
    )


def tag_chip_style() -> str:
    return (
        "background-color: #1b2f4a; color: #9fc6ff; border: 1px solid #2a4a6e;"
        "border-radius: 8px; padding: 1px 8px; font-size: 8pt;"
    )
