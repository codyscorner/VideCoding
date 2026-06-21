import os
import sys
import shutil
import tarfile
import zipfile
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QLineEdit,
    QPushButton, QTextEdit, QGridLayout, QVBoxLayout,
    QHBoxLayout, QFrame, QFileDialog, QMessageBox,
)
from PyQt6.QtGui import QIcon, QColor, QTextCharFormat
from PyQt6.QtCore import Qt

try:
    import py7zr
    HAS_7Z = True
except ImportError:
    HAS_7Z = False

BG_DARK      = "#0d1f0d"
BG_MID       = "#122112"
BG_PANEL     = "#1a3a1a"
ACCENT       = "#39d353"
ACCENT_HOVER = "#57e870"
ACCENT_DIM   = "#1a6b1a"
TEXT_BRIGHT  = "#d4f5d4"
TEXT_DIM     = "#7aaa7a"
BORDER       = "#2d5a2d"
SUCCESS      = "#39d353"
ERROR_COL    = "#e05c5c"
WARNING_COL  = "#e0a020"

STYLESHEET = f"""
QMainWindow, QWidget {{
    background-color: {BG_DARK};
    color: {TEXT_BRIGHT};
    font-family: "Segoe UI";
    font-size: 9pt;
}}
QLabel {{
    background-color: transparent;
    color: {TEXT_DIM};
}}
QLabel#title {{
    font-size: 13pt;
    font-weight: bold;
    color: {TEXT_BRIGHT};
}}
QLabel#version {{
    font-size: 8pt;
    color: {TEXT_DIM};
}}
QLineEdit {{
    background-color: {BG_PANEL};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    padding: 5px;
    font-size: 9pt;
}}
QLineEdit:focus {{
    border: 1px solid {ACCENT};
}}
QPushButton {{
    background-color: {ACCENT};
    color: {TEXT_BRIGHT};
    font-weight: bold;
    border: none;
    border-radius: 3px;
    padding: 6px 14px;
    font-size: 9pt;
}}
QPushButton:hover {{
    background-color: {ACCENT_HOVER};
}}
QPushButton#secondary {{
    background-color: {BG_PANEL};
}}
QPushButton#secondary:hover {{
    background-color: {BORDER};
}}
QTextEdit {{
    background-color: {BG_MID};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 8pt;
}}
QFrame#divider {{
    background-color: {BORDER};
}}
QFrame#titlebar {{
    background-color: {ACCENT_DIM};
}}
"""


def _archive_type(filename: str) -> str:
    """Return archive type tag or empty string if not a supported archive."""
    lower = filename.lower()
    if lower.endswith(".zip"):
        return "ZIP"
    if lower.endswith(".7z"):
        return "7Z"
    if lower.endswith(".tar.gz") or lower.endswith(".tgz"):
        return "TAR.GZ"
    return ""


def _list_archives(folder: str) -> list[tuple[str, str]]:
    """Return (filename, type_tag) for all supported archives in folder."""
    results = []
    for f in os.listdir(folder):
        tag = _archive_type(f)
        if tag:
            results.append((f, tag))
    return results


class UnzipperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Unzipper  V-1.2.0")
        self.setFixedSize(660, 480)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        outer = QVBoxLayout(central)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Title bar
        titlebar = QFrame()
        titlebar.setObjectName("titlebar")
        titlebar.setFixedHeight(42)
        tb_layout = QHBoxLayout(titlebar)
        tb_layout.setContentsMargins(16, 0, 16, 0)
        lbl_title = QLabel("⚡  Unzipper")
        lbl_title.setObjectName("title")
        lbl_ver = QLabel("V-1.2.0")
        lbl_ver.setObjectName("version")
        tb_layout.addWidget(lbl_title)
        tb_layout.addWidget(lbl_ver)
        tb_layout.addStretch()
        outer.addWidget(titlebar)

        # Body
        body = QWidget()
        body_layout = QGridLayout(body)
        body_layout.setContentsMargins(20, 14, 20, 14)
        body_layout.setSpacing(6)
        body_layout.setColumnStretch(0, 1)
        outer.addWidget(body)

        # Source row
        body_layout.addWidget(QLabel("Source Folder"), 0, 0, 1, 3)
        self.source_edit = QLineEdit()
        browse_src = QPushButton("Browse")
        browse_src.setFixedWidth(80)
        browse_src.setObjectName("secondary")
        browse_src.clicked.connect(self.browse_source)
        body_layout.addWidget(self.source_edit, 1, 0, 1, 2)
        body_layout.addWidget(browse_src, 1, 2)

        # Dest row
        body_layout.addWidget(QLabel("Destination Folder"), 2, 0, 1, 3)
        self.dest_edit = QLineEdit()
        browse_dst = QPushButton("Browse")
        browse_dst.setFixedWidth(80)
        browse_dst.setObjectName("secondary")
        browse_dst.clicked.connect(self.browse_dest)
        body_layout.addWidget(self.dest_edit, 3, 0, 1, 2)
        body_layout.addWidget(browse_dst, 3, 2)

        # Filename row
        body_layout.addWidget(QLabel("Filename  (Flat Unzip)"), 4, 0, 1, 3)
        self.filename_edit = QLineEdit("UnzippedFile")
        body_layout.addWidget(self.filename_edit, 5, 0, 1, 3)

        # Action buttons
        btn_layout = QHBoxLayout()
        btn_flat = QPushButton("Unzip  —  Flat")
        btn_struct = QPushButton("Unzip  —  Keep Structure")
        btn_struct.setObjectName("secondary")
        btn_flat.clicked.connect(self.unzip_flat)
        btn_struct.clicked.connect(self.unzip_with_structure)
        btn_layout.addWidget(btn_flat)
        btn_layout.addWidget(btn_struct)
        body_layout.addLayout(btn_layout, 6, 0, 1, 3)

        # Divider
        divider = QFrame()
        divider.setObjectName("divider")
        divider.setFixedHeight(1)
        body_layout.addWidget(divider, 7, 0, 1, 3)

        # Status
        body_layout.addWidget(QLabel("Status"), 8, 0)
        self.status_box = QTextEdit()
        self.status_box.setReadOnly(True)
        body_layout.addWidget(self.status_box, 9, 0, 1, 3)
        body_layout.setRowStretch(9, 1)

    def browse_source(self):
        existing = self.source_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Source Folder", start)
        if folder:
            self.source_edit.setText(folder)

    def browse_dest(self):
        existing = self.dest_edit.text().strip()
        start = existing if existing and os.path.isdir(existing) else ""
        folder = QFileDialog.getExistingDirectory(self, "Select Destination Folder", start)
        if folder:
            self.dest_edit.setText(folder)

    def _log(self, message: str, color: str = TEXT_BRIGHT):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.status_box.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.status_box.setTextCursor(cursor)
        self.status_box.ensureCursorVisible()

    def _validate_folders(self, source: str, dest: str) -> bool:
        if not source or not dest:
            QMessageBox.critical(self, "Error", "Please select source and destination folders.")
            return False
        if not os.path.exists(source):
            QMessageBox.critical(self, "Error", f"Source folder does not exist:\n{source}")
            return False
        if not os.path.exists(dest):
            os.makedirs(dest)
        return True

    def unzip_flat(self):
        source   = self.source_edit.text().strip()
        dest     = self.dest_edit.text().strip()
        filename = self.filename_edit.text().strip()
        if not filename:
            QMessageBox.critical(self, "Error", "Please provide a filename for flat unzip.")
            return
        if not self._validate_folders(source, dest):
            return

        archives = _list_archives(source)
        if not archives:
            self._log("No ZIP / 7Z / TAR.GZ files found in source folder.", ERROR_COL)
            return

        self._log(f"Starting flat unzip — {len(archives)} archive(s) found…", ACCENT)
        counter = 1

        for archive_file, tag in archives:
            archive_path = os.path.join(source, archive_file)

            if tag == "ZIP":
                try:
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        for file_info in zf.filelist:
                            if not file_info.is_dir():
                                ext = os.path.splitext(file_info.filename)[1]
                                new_name = f"{filename}_{counter:06d}{ext}"
                                new_path = os.path.join(dest, new_name)
                                with zf.open(file_info) as src, open(new_path, "wb") as dst:
                                    shutil.copyfileobj(src, dst)
                                self._log(f"  [ZIP] Extracted: {new_name}", SUCCESS)
                                counter += 1
                except Exception as e:
                    self._log(f"  [ZIP] Error extracting {archive_file}: {e}", ERROR_COL)

            elif tag == "7Z":
                if not HAS_7Z:
                    self._log("  [7Z] py7zr not installed — skipping .7z files", WARNING_COL)
                    continue
                try:
                    with py7zr.SevenZipFile(archive_path, mode="r") as zf:
                        for info in zf.list():
                            if not info.is_directory:
                                ext = os.path.splitext(info.filename)[1]
                                new_name = f"{filename}_{counter:06d}{ext}"
                                new_path = os.path.join(dest, new_name)
                                zf.extract(targets=[info.filename], path=dest)
                                extracted = os.path.join(dest, info.filename)
                                os.rename(extracted, new_path)
                                self._log(f"  [7Z] Extracted: {new_name}", SUCCESS)
                                counter += 1
                except Exception as e:
                    self._log(f"  [7Z] Error extracting {archive_file}: {e}", ERROR_COL)

            elif tag == "TAR.GZ":
                try:
                    with tarfile.open(archive_path, "r:*") as tf:
                        for member in tf.getmembers():
                            if member.isfile():
                                ext = os.path.splitext(member.name)[1]
                                new_name = f"{filename}_{counter:06d}{ext}"
                                new_path = os.path.join(dest, new_name)
                                src = tf.extractfile(member)
                                if src:
                                    with open(new_path, "wb") as dst:
                                        shutil.copyfileobj(src, dst)
                                    self._log(f"  [TAR.GZ] Extracted: {new_name}", SUCCESS)
                                    counter += 1
                except Exception as e:
                    self._log(f"  [TAR.GZ] Error extracting {archive_file}: {e}", ERROR_COL)

        self._log("Flat unzip completed.", ACCENT)

    def unzip_with_structure(self):
        source = self.source_edit.text().strip()
        dest   = self.dest_edit.text().strip()
        if not self._validate_folders(source, dest):
            return

        archives = _list_archives(source)
        if not archives:
            self._log("No ZIP / 7Z / TAR.GZ files found in source folder.", ERROR_COL)
            return

        self._log(f"Starting structured unzip — {len(archives)} archive(s) found…", ACCENT)

        for archive_file, tag in archives:
            # Strip all archive extensions to get base name
            base = archive_file
            for ext in (".tar.gz", ".tgz", ".7z", ".zip"):
                if base.lower().endswith(ext):
                    base = base[: len(base) - len(ext)]
                    break
            folder_name = base
            counter = 0
            while os.path.exists(os.path.join(dest, folder_name)):
                counter += 1
                folder_name = f"{base}_{counter:06d}"
            folder_path = os.path.join(dest, folder_name)
            archive_path = os.path.join(source, archive_file)

            if tag == "ZIP":
                try:
                    with zipfile.ZipFile(archive_path, "r") as zf:
                        zf.extractall(folder_path)
                    self._log(f"  [ZIP] Extracted  {archive_file}  →  {folder_name}", SUCCESS)
                except Exception as e:
                    self._log(f"  [ZIP] Error extracting {archive_file}: {e}", ERROR_COL)

            elif tag == "7Z":
                if not HAS_7Z:
                    self._log("  [7Z] py7zr not installed — skipping .7z files", WARNING_COL)
                    continue
                try:
                    with py7zr.SevenZipFile(archive_path, mode="r") as zf:
                        zf.extractall(path=folder_path)
                    self._log(f"  [7Z] Extracted  {archive_file}  →  {folder_name}", SUCCESS)
                except Exception as e:
                    self._log(f"  [7Z] Error extracting {archive_file}: {e}", ERROR_COL)

            elif tag == "TAR.GZ":
                try:
                    with tarfile.open(archive_path, "r:*") as tf:
                        tf.extractall(folder_path)
                    self._log(f"  [TAR.GZ] Extracted  {archive_file}  →  {folder_name}", SUCCESS)
                except Exception as e:
                    self._log(f"  [TAR.GZ] Error extracting {archive_file}: {e}", ERROR_COL)

        self._log("Structured unzip completed.", ACCENT)


def main():
    app = QApplication(sys.argv)
    window = UnzipperApp()
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
