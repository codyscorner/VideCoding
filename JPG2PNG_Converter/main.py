"""
JPG to PNG Converter
Version: 1.0.0
"""

import sys
from pathlib import Path

from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QProgressBar,
    QListWidget, QListWidgetItem, QFileDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon

try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("JPG2PNG.Converter.1")
except Exception:
    pass

VERSION = "1.0.0"

BG_DARK     = "#0d0d1a"
BG_MEDIUM   = "#1a1a2e"
BG_LIGHT    = "#16213e"
FG_PRIMARY  = "#e0e0ff"
FG_SECONDARY= "#9090cc"
FG_DIM      = "#505080"
ACCENT      = "#5e4bdb"
ACCENT_HOV  = "#7b6cf0"
ACCENT_DARK = "#3d2fb0"
BORDER      = "#2a2a4a"
SUCCESS     = "#4caf8a"
ERROR       = "#ef5350"
WARNING     = "#ffb74d"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {FG_PRIMARY};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QLabel {{ background: transparent; color: {FG_PRIMARY}; }}
QLineEdit {{
    background-color: {BG_LIGHT};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 6px 10px;
}}
QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
QPushButton {{
    background-color: {ACCENT};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 10px 28px;
    font-size: 11pt;
}}
QPushButton:hover {{ background-color: {ACCENT_HOV}; }}
QPushButton:disabled {{ background-color: {BG_LIGHT}; color: {FG_DIM}; }}
QPushButton#browse_btn {{ padding: 6px 12px; font-size: 10pt; }}
QPushButton#cancel_btn {{
    background-color: {ACCENT_DARK};
    color: {FG_PRIMARY};
}}
QPushButton#cancel_btn:hover {{ background-color: {ERROR}; color: white; }}
QCheckBox {{
    color: {FG_SECONDARY};
    spacing: 6px;
}}
QCheckBox::indicator {{
    width: 16px; height: 16px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_LIGHT};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT};
    border: 1px solid {ACCENT_HOV};
}}
QProgressBar {{
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG_MEDIUM};
    height: 20px;
    text-align: center;
    color: {FG_PRIMARY};
}}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 2px; }}
QListWidget {{
    background: {BG_MEDIUM};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item {{ padding: 1px 4px; }}
QScrollBar:vertical {{
    background: {BG_DARK}; width: 10px; border: none;
}}
QScrollBar::handle:vertical {{
    background: {BORDER}; border-radius: 5px; min-height: 20px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
"""

JPG_EXTS = {".jpg", ".jpeg"}


class ConverterThread(QThread):
    progress   = pyqtSignal(int, int)       # current, total
    file_done  = pyqtSignal(str, bool, str) # filename, success, message
    finished   = pyqtSignal(int, int)       # converted, skipped

    def __init__(self, folder: Path, recursive: bool, delete_originals: bool):
        super().__init__()
        self._folder = folder
        self._recursive = recursive
        self._delete = delete_originals
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        glob = "**/*" if self._recursive else "*"
        files = [p for p in self._folder.glob(glob)
                 if p.is_file() and p.suffix.lower() in JPG_EXTS]
        total = len(files)
        converted = skipped = 0

        for i, src in enumerate(files, 1):
            if self._cancelled:
                break
            self.progress.emit(i, total)
            dst = src.with_suffix(".png")
            counter = 1
            while dst.exists():
                dst = src.with_name(f"{src.stem}_{counter}.png")
                counter += 1
            try:
                with Image.open(src) as img:
                    img.save(dst, "PNG")
                if self._delete:
                    src.unlink()
                self.file_done.emit(src.name, True, f"→ {dst.name}")
                converted += 1
            except Exception as e:
                self.file_done.emit(src.name, False, f"Error: {e}")
                skipped += 1

        self.finished.emit(converted, skipped)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"JPG to PNG Converter  v{VERSION}")
        self.setMinimumSize(620, 520)
        self.resize(700, 580)
        self.setStyleSheet(STYLESHEET)
        self._thread: ConverterThread | None = None

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header
        title = QLabel("JPG → PNG Converter")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {ACCENT_HOV}; font-size: 18pt; font-weight: bold;")
        layout.addWidget(title)

        # Folder picker
        folder_row = QHBoxLayout()
        folder_lbl = QLabel("Folder:")
        folder_lbl.setFixedWidth(52)
        self._folder_edit = QLineEdit()
        self._folder_edit.setPlaceholderText("Select a folder containing JPG/JPEG files...")
        browse_btn = QPushButton("...")
        browse_btn.setObjectName("browse_btn")
        browse_btn.setFixedWidth(36)
        browse_btn.clicked.connect(self._browse)
        folder_row.addWidget(folder_lbl)
        folder_row.addWidget(self._folder_edit, stretch=1)
        folder_row.addWidget(browse_btn)
        layout.addLayout(folder_row)

        # Options
        opts_row = QHBoxLayout()
        self._recursive_chk = QCheckBox("Include subfolders")
        self._recursive_chk.setChecked(False)
        self._delete_chk = QCheckBox("Delete originals after conversion")
        self._delete_chk.setChecked(False)
        opts_row.addWidget(self._recursive_chk)
        opts_row.addSpacing(24)
        opts_row.addWidget(self._delete_chk)
        opts_row.addStretch()
        layout.addLayout(opts_row)

        # Buttons
        btn_row = QHBoxLayout()
        self._convert_btn = QPushButton("Convert")
        self._convert_btn.clicked.connect(self._start)
        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(self._convert_btn)
        btn_row.addWidget(self._cancel_btn)
        layout.addLayout(btn_row)

        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        layout.addWidget(self._progress)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {FG_SECONDARY}; font-size: 9pt;")
        layout.addWidget(self._status_lbl)

        # Log
        self._log = QListWidget()
        layout.addWidget(self._log, stretch=1)

    def _browse(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Folder",
                                                   self._folder_edit.text() or str(Path.home()))
        if folder:
            self._folder_edit.setText(folder)

    def _start(self):
        folder = Path(self._folder_edit.text().strip())
        if not folder.exists() or not folder.is_dir():
            self._status_lbl.setText("Invalid folder — please select a valid directory.")
            self._status_lbl.setStyleSheet(f"color: {ERROR}; font-size: 9pt;")
            return

        self._log.clear()
        self._convert_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._status_lbl.setStyleSheet(f"color: {FG_SECONDARY}; font-size: 9pt;")
        self._status_lbl.setText("Converting...")

        self._thread = ConverterThread(
            folder,
            recursive=self._recursive_chk.isChecked(),
            delete_originals=self._delete_chk.isChecked(),
        )
        self._thread.progress.connect(self._on_progress)
        self._thread.file_done.connect(self._on_file_done)
        self._thread.finished.connect(self._on_finished)
        self._thread.start()

    def _cancel(self):
        if self._thread:
            self._thread.cancel()
        self._cancel_btn.setEnabled(False)
        self._status_lbl.setText("Cancelling...")

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._status_lbl.setText(f"Converting {current} / {total}...")

    def _on_file_done(self, filename: str, success: bool, message: str):
        color = SUCCESS if success else WARNING
        item = QListWidgetItem(f"{'✓' if success else '—'}  {filename}  {message}")
        item.setForeground(__import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(color))
        self._log.addItem(item)
        self._log.scrollToBottom()

    def _on_finished(self, converted: int, skipped: int):
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setValue(self._progress.maximum())
        msg = f"Done — {converted} converted, {skipped} skipped"
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {SUCCESS}; font-size: 9pt;")
        summary = QListWidgetItem(f"── {msg} ──")
        summary.setForeground(__import__("PyQt6.QtGui", fromlist=["QColor"]).QColor(SUCCESS))
        self._log.addItem(summary)
        self._log.scrollToBottom()


def _find_icon() -> Path | None:
    script_dir = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    candidate = script_dir / "app_icon.ico"
    if candidate.exists():
        return candidate
    if getattr(sys, "frozen", False):
        bundled = Path(sys._MEIPASS) / "app_icon.ico"
        if bundled.exists():
            return bundled
    return None


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("JPG to PNG Converter")
    icon_path = _find_icon()
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
