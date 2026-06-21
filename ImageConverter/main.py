"""
Image Converter
Version: 1.0.0
Batch-converts images between JPG, PNG, WebP, BMP, and TIFF formats.
"""

import sys
from pathlib import Path

from PIL import Image
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QCheckBox, QProgressBar,
    QListWidget, QListWidgetItem, QFileDialog, QComboBox, QSlider,
    QGroupBox, QStackedWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QIcon, QColor

try:
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ImageConverter.App.1")
except Exception:
    pass

VERSION = "1.0.0"

BG_DARK      = "#0d0d1a"
BG_MEDIUM    = "#1a1a2e"
BG_LIGHT     = "#16213e"
FG_PRIMARY   = "#e0e0ff"
FG_SECONDARY = "#9090cc"
FG_DIM       = "#505080"
ACCENT       = "#5e4bdb"
ACCENT_HOV   = "#7b6cf0"
ACCENT_DARK  = "#3d2fb0"
BORDER       = "#2a2a4a"
SUCCESS      = "#4caf8a"
ERROR        = "#ef5350"
WARNING      = "#ffb74d"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {FG_PRIMARY};
    font-family: "Segoe UI";
    font-size: 10pt;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 4px;
    margin-top: 8px;
    padding-top: 4px;
    color: {FG_SECONDARY};
    font-size: 9pt;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 8px;
    padding: 0 4px;
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
QComboBox {{
    background-color: {BG_LIGHT};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px 10px;
    min-width: 110px;
}}
QComboBox::drop-down {{
    border: none;
    padding-right: 6px;
}}
QComboBox QAbstractItemView {{
    background-color: {BG_MEDIUM};
    color: {FG_PRIMARY};
    border: 1px solid {BORDER};
    selection-background-color: {ACCENT};
}}
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
QSlider::groove:horizontal {{
    height: 6px;
    background: {BG_MEDIUM};
    border: 1px solid {BORDER};
    border-radius: 3px;
}}
QSlider::handle:horizontal {{
    background: {ACCENT};
    border: 1px solid {ACCENT_HOV};
    width: 14px;
    height: 14px;
    margin: -5px 0;
    border-radius: 7px;
}}
QSlider::handle:horizontal:hover {{ background: {ACCENT_HOV}; }}
QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}

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

# Supported input extensions
INPUT_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".tif", ".tiff", ".gif"}

# Output format definitions
FORMATS = {
    "PNG":  {"ext": ".png",  "pillow": "PNG",  "lossy": False},
    "JPG":  {"ext": ".jpg",  "pillow": "JPEG", "lossy": True},
    "WebP": {"ext": ".webp", "pillow": "WEBP", "lossy": True},
    "BMP":  {"ext": ".bmp",  "pillow": "BMP",  "lossy": False},
    "TIFF": {"ext": ".tif",  "pillow": "TIFF", "lossy": False},
}


def _save_image(img: Image.Image, dst: Path, fmt: dict, quality: int):
    if fmt["lossy"]:
        img.save(dst, fmt["pillow"], quality=quality)
    else:
        img.save(dst, fmt["pillow"])


class ConverterThread(QThread):
    progress  = pyqtSignal(int, int)        # current, total
    file_done = pyqtSignal(str, bool, str)  # filename, success, message
    finished  = pyqtSignal(int, int)        # converted, skipped

    def __init__(
        self,
        src_folder: Path,
        out_folder: Path,
        fmt: dict,
        fmt_name: str,
        quality: int,
        recursive: bool,
        delete_originals: bool,
        skip_same_fmt: bool,
    ):
        super().__init__()
        self._src = src_folder
        self._out = out_folder
        self._fmt = fmt
        self._fmt_name = fmt_name
        self._quality = quality
        self._recursive = recursive
        self._delete = delete_originals
        self._skip_same = skip_same_fmt
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        glob = "**/*" if self._recursive else "*"
        files = [
            p for p in self._src.glob(glob)
            if p.is_file() and p.suffix.lower() in INPUT_EXTS
        ]

        if self._skip_same:
            target_ext = self._fmt["ext"]
            files = [p for p in files if p.suffix.lower() != target_ext]

        total = len(files)
        converted = skipped = 0

        for i, src in enumerate(files, 1):
            if self._cancelled:
                break
            self.progress.emit(i, total)

            # Mirror subfolder structure under output folder
            try:
                rel = src.relative_to(self._src)
            except ValueError:
                rel = Path(src.name)

            dst = self._out / rel.with_suffix(self._fmt["ext"])
            dst.parent.mkdir(parents=True, exist_ok=True)

            # Avoid collision
            counter = 1
            base_dst = dst
            while dst.exists() and dst != src.with_suffix(self._fmt["ext"]):
                dst = base_dst.with_stem(f"{base_dst.stem}_{counter}")
                counter += 1

            try:
                with Image.open(src) as img:
                    out_img = img
                    # JPEG doesn't support alpha; flatten to white background
                    if self._fmt["pillow"] == "JPEG" and img.mode in ("RGBA", "LA", "P"):
                        bg = Image.new("RGB", img.size, (255, 255, 255))
                        if img.mode == "P":
                            img = img.convert("RGBA")
                        bg.paste(img, mask=img.split()[-1] if img.mode in ("RGBA", "LA") else None)
                        out_img = bg
                    elif img.mode == "P":
                        out_img = img.convert("RGBA")

                    _save_image(out_img, dst, self._fmt, self._quality)

                if self._delete and src != dst:
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
        self.setWindowTitle(f"Image Converter  v{VERSION}")
        self.setMinimumSize(680, 600)
        self.resize(760, 660)
        self.setStyleSheet(STYLESHEET)
        self._thread: ConverterThread | None = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(20, 16, 20, 20)
        root.setSpacing(12)

        # Header
        title = QLabel("Image Converter")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"color: {ACCENT_HOV}; font-size: 18pt; font-weight: bold;")
        root.addWidget(title)

        subtitle = QLabel("Batch-convert images between PNG, JPG, WebP, BMP, and TIFF")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"color: {FG_SECONDARY}; font-size: 9pt;")
        root.addWidget(subtitle)

        # Source folder
        src_grp = QGroupBox("Source Folder")
        src_lay = QHBoxLayout(src_grp)
        src_lay.setContentsMargins(8, 12, 8, 8)
        self._src_edit = QLineEdit()
        self._src_edit.setPlaceholderText("Folder containing images to convert...")
        src_browse = QPushButton("...")
        src_browse.setObjectName("browse_btn")
        src_browse.setFixedWidth(36)
        src_browse.clicked.connect(self._browse_src)
        src_lay.addWidget(self._src_edit, stretch=1)
        src_lay.addWidget(src_browse)
        root.addWidget(src_grp)

        # Output folder
        out_grp = QGroupBox("Output Folder")
        out_lay = QVBoxLayout(out_grp)
        out_lay.setContentsMargins(8, 12, 8, 8)
        out_lay.setSpacing(6)
        self._same_chk = QCheckBox("Save converted files in the same folder as source")
        self._same_chk.setChecked(True)
        self._same_chk.toggled.connect(self._on_same_toggled)
        out_lay.addWidget(self._same_chk)
        out_row = QHBoxLayout()
        self._out_edit = QLineEdit()
        self._out_edit.setPlaceholderText("Select a different output folder...")
        self._out_edit.setEnabled(False)
        out_browse = QPushButton("...")
        out_browse.setObjectName("browse_btn")
        out_browse.setObjectName("out_browse")
        out_browse.setFixedWidth(36)
        out_browse.clicked.connect(self._browse_out)
        self._out_browse_btn = out_browse
        self._out_browse_btn.setEnabled(False)
        out_row.addWidget(self._out_edit, stretch=1)
        out_row.addWidget(out_browse)
        out_lay.addLayout(out_row)
        root.addWidget(out_grp)

        # Format + quality row
        fmt_grp = QGroupBox("Conversion Settings")
        fmt_lay = QHBoxLayout(fmt_grp)
        fmt_lay.setContentsMargins(8, 12, 8, 8)
        fmt_lay.setSpacing(16)

        fmt_lbl = QLabel("Output format:")
        self._fmt_combo = QComboBox()
        for name in FORMATS:
            self._fmt_combo.addItem(name)
        self._fmt_combo.currentTextChanged.connect(self._on_fmt_changed)
        self._fmt_combo.setCurrentText("PNG")

        # Quality controls — slider shown for lossy, label for lossless
        self._quality_lbl = QLabel("Quality:")

        self._quality_stack = QStackedWidget()
        self._quality_stack.setFixedHeight(28)

        # Page 0: slider row (lossy)
        slider_page = QWidget()
        slider_row = QHBoxLayout(slider_page)
        slider_row.setContentsMargins(0, 0, 0, 0)
        slider_row.setSpacing(6)
        self._quality_slider = QSlider(Qt.Orientation.Horizontal)
        self._quality_slider.setRange(1, 100)
        self._quality_slider.setValue(85)
        self._quality_slider.setFixedWidth(140)
        self._quality_slider.valueChanged.connect(self._on_quality_changed)
        self._quality_val = QLabel("85")
        self._quality_val.setFixedWidth(28)
        slider_row.addWidget(self._quality_slider)
        slider_row.addWidget(self._quality_val)
        self._quality_stack.addWidget(slider_page)

        # Page 1: "Not available" label (lossless)
        na_page = QWidget()
        na_row = QHBoxLayout(na_page)
        na_row.setContentsMargins(0, 0, 0, 0)
        na_lbl = QLabel("Not available")
        na_lbl.setStyleSheet(f"color: {FG_DIM}; font-style: italic;")
        na_row.addWidget(na_lbl)
        na_row.addStretch()
        self._quality_stack.addWidget(na_page)

        fmt_lay.addWidget(fmt_lbl)
        fmt_lay.addWidget(self._fmt_combo)
        fmt_lay.addSpacing(24)
        fmt_lay.addWidget(self._quality_lbl)
        fmt_lay.addWidget(self._quality_stack)
        fmt_lay.addStretch()
        root.addWidget(fmt_grp)

        # Options
        opts_grp = QGroupBox("Options")
        opts_lay = QHBoxLayout(opts_grp)
        opts_lay.setContentsMargins(8, 12, 8, 8)
        self._recursive_chk = QCheckBox("Include subfolders")
        self._skip_same_chk = QCheckBox("Skip files already in target format")
        self._skip_same_chk.setChecked(True)
        self._delete_chk = QCheckBox("Delete originals after conversion")
        opts_lay.addWidget(self._recursive_chk)
        opts_lay.addSpacing(16)
        opts_lay.addWidget(self._skip_same_chk)
        opts_lay.addSpacing(16)
        opts_lay.addWidget(self._delete_chk)
        opts_lay.addStretch()
        root.addWidget(opts_grp)

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
        root.addLayout(btn_row)

        # Progress
        self._progress = QProgressBar()
        self._progress.setRange(0, 1)
        self._progress.setValue(0)
        root.addWidget(self._progress)

        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {FG_SECONDARY}; font-size: 9pt;")
        root.addWidget(self._status_lbl)

        # Log
        self._log = QListWidget()
        root.addWidget(self._log, stretch=1)

        # Initialize quality widget state to match default format
        self._on_fmt_changed(self._fmt_combo.currentText())

    # ------------------------------------------------------------------
    def _browse_src(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Source Folder",
            self._src_edit.text() or str(Path.home()),
        )
        if folder:
            self._src_edit.setText(folder)

    def _browse_out(self):
        folder = QFileDialog.getExistingDirectory(
            self, "Select Output Folder",
            self._out_edit.text() or self._src_edit.text() or str(Path.home()),
        )
        if folder:
            self._out_edit.setText(folder)

    def _on_same_toggled(self, checked: bool):
        self._out_edit.setEnabled(not checked)
        self._out_browse_btn.setEnabled(not checked)

    def _on_fmt_changed(self, name: str):
        lossy = FORMATS.get(name, {}).get("lossy", False)
        self._quality_lbl.setEnabled(lossy)
        self._quality_stack.setCurrentIndex(0 if lossy else 1)

    def _on_quality_changed(self, value: int):
        self._quality_val.setText(str(value))

    # ------------------------------------------------------------------
    def _start(self):
        src_path = Path(self._src_edit.text().strip())
        if not src_path.exists() or not src_path.is_dir():
            self._set_status("Invalid source folder — please select a valid directory.", ERROR)
            return

        if self._same_chk.isChecked():
            out_path = src_path
        else:
            out_text = self._out_edit.text().strip()
            if not out_text:
                self._set_status("Please select an output folder (or check 'same as source').", ERROR)
                return
            out_path = Path(out_text)
            out_path.mkdir(parents=True, exist_ok=True)

        fmt_name = self._fmt_combo.currentText()
        fmt = FORMATS[fmt_name]

        self._log.clear()
        self._convert_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)
        self._set_status("Converting...", FG_SECONDARY)

        self._thread = ConverterThread(
            src_folder=src_path,
            out_folder=out_path,
            fmt=fmt,
            fmt_name=fmt_name,
            quality=self._quality_slider.value(),
            recursive=self._recursive_chk.isChecked(),
            delete_originals=self._delete_chk.isChecked(),
            skip_same_fmt=self._skip_same_chk.isChecked(),
        )
        self._thread.progress.connect(self._on_progress)
        self._thread.file_done.connect(self._on_file_done)
        self._thread.finished.connect(self._on_finished)
        self._thread.start()

    def _cancel(self):
        if self._thread:
            self._thread.cancel()
        self._cancel_btn.setEnabled(False)
        self._set_status("Cancelling...", WARNING)

    def _on_progress(self, current: int, total: int):
        self._progress.setRange(0, total)
        self._progress.setValue(current)
        self._set_status(f"Converting {current} / {total}...", FG_SECONDARY)

    def _on_file_done(self, filename: str, success: bool, message: str):
        color = SUCCESS if success else WARNING
        icon = "✓" if success else "—"
        item = QListWidgetItem(f"{icon}  {filename}  {message}")
        item.setForeground(QColor(color))
        self._log.addItem(item)
        self._log.scrollToBottom()

    def _on_finished(self, converted: int, skipped: int):
        self._convert_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)
        self._progress.setValue(self._progress.maximum())
        msg = f"Done — {converted} converted, {skipped} skipped"
        self._set_status(msg, SUCCESS)
        summary = QListWidgetItem(f"── {msg} ──")
        summary.setForeground(QColor(SUCCESS))
        self._log.addItem(summary)
        self._log.scrollToBottom()

    def _set_status(self, msg: str, color: str):
        self._status_lbl.setText(msg)
        self._status_lbl.setStyleSheet(f"color: {color}; font-size: 9pt;")


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
    app.setApplicationName("Image Converter")
    icon_path = _find_icon()
    if icon_path:
        app.setWindowIcon(QIcon(str(icon_path)))
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
