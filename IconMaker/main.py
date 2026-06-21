"""
IconMaker GUI — PyQt6 wrapper around make_icons.py
"""

import json
import random
import shutil
import sys
from pathlib import Path

import make_icons

from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QColor, QTextCharFormat
from PyQt6.QtWidgets import (
    QApplication, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMainWindow, QPushButton, QTextEdit, QVBoxLayout,
    QWidget,
)

VERSION = "1.0.0"

BG_DARK      = "#0d0d1a"
BG_MID       = "#12122a"
BG_PANEL     = "#1a1a30"
ACCENT       = "#5e4bdb"
ACCENT_HOVER = "#7a68f0"
TEXT_BRIGHT  = "#d4d0f5"
TEXT_DIM     = "#8880cc"
BORDER       = "#2d2a5a"
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
QLabel#progress {{
    font-size: 9pt;
    color: {TEXT_BRIGHT};
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
    font-weight: normal;
}}
QPushButton#secondary:hover {{
    background-color: {BORDER};
}}
QListWidget {{
    background-color: {BG_PANEL};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-size: 9pt;
}}
QListWidget::item:selected {{
    background-color: {ACCENT};
}}
QTextEdit {{
    background-color: {BG_MID};
    color: {TEXT_BRIGHT};
    border: 1px solid {BORDER};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 8pt;
}}
"""


class IconWorker(QThread):
    log_line  = pyqtSignal(str, str)   # (message, color)
    progress  = pyqtSignal(int, int, str)  # (current, total, name)
    finished  = pyqtSignal()

    def __init__(self, apps: list, comfy_url: str, output_path: str):
        super().__init__()
        self.apps        = apps
        self.comfy_url   = comfy_url
        self.output_path = Path(output_path)

    def run(self):
        # Override module-level globals so helper functions use user config
        make_icons.COMFY_URL    = self.comfy_url
        make_icons.COMFY_OUTPUT = self.output_path

        output_dir = Path(__file__).parent / "output"
        output_dir.mkdir(exist_ok=True)
        projects_root = Path(__file__).parent.parent

        try:
            base_workflow = make_icons.load_workflow()
        except Exception as e:
            self.log_line.emit(f"ERROR loading workflow: {e}", ERROR_COL)
            self.finished.emit()
            return

        total = len(self.apps)
        for idx, app in enumerate(self.apps, 1):
            name           = app["name"]
            project_folder = projects_root / app["project_folder"]
            self.progress.emit(idx, total, name)

            self.log_line.emit(f"\n[{idx}/{total}] {name}", ACCENT)
            self.log_line.emit("-" * 40, TEXT_DIM)

            workflow = json.loads(json.dumps(base_workflow))
            workflow["91"]["inputs"]["value"]             = app["prompt"]
            workflow["86:3"]["inputs"]["seed"]            = random.randint(1, 2**31)
            workflow["86:58"]["inputs"]["width"]          = 512
            workflow["86:58"]["inputs"]["height"]         = 512
            workflow["60"]["inputs"]["filename_prefix"]   = f"icon_{name}"

            try:
                prompt_id = make_icons.submit_prompt(workflow)
            except Exception as e:
                self.log_line.emit(f"  ERROR submitting prompt: {e}", ERROR_COL)
                continue

            self.log_line.emit("  Waiting for ComfyUI…", TEXT_DIM)
            if not make_icons.wait_for_completion(prompt_id):
                self.log_line.emit("  SKIPPED — timed out", WARNING_COL)
                continue

            filename = make_icons.get_output_filename(prompt_id)
            if not filename:
                self.log_line.emit("  SKIPPED — no output filename found", WARNING_COL)
                continue

            src_png = self.output_path / filename
            dst_png = output_dir / f"{name}.png"
            try:
                shutil.copy2(src_png, dst_png)
                self.log_line.emit(f"  PNG  -> {dst_png.name}", SUCCESS)
            except Exception as e:
                self.log_line.emit(f"  ERROR copying PNG: {e}", ERROR_COL)
                continue

            ico_path = output_dir / f"{name}.ico"
            try:
                make_icons.convert_to_ico(dst_png, ico_path)
                self.log_line.emit(f"  ICO  -> {ico_path.name}", SUCCESS)
            except Exception as e:
                self.log_line.emit(f"  ERROR converting ICO: {e}", ERROR_COL)
                continue

            if project_folder.exists():
                project_ico = project_folder / "app_icon.ico"
                shutil.copy2(ico_path, project_ico)
                self.log_line.emit(f"  COPY -> {project_folder.name}/app_icon.ico", SUCCESS)
            else:
                self.log_line.emit(f"  WARN — project folder not found: {project_folder}", WARNING_COL)

        self.log_line.emit(f"\n{'=' * 40}", TEXT_DIM)
        self.log_line.emit(f"Done! {total} icon(s) generated.", ACCENT)
        self.finished.emit()


class IconMakerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"IconMaker  v{VERSION}")
        self.setMinimumSize(700, 600)
        self.setStyleSheet(STYLESHEET)
        self._worker = None
        self._build_ui()

    def _build_ui(self):
        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(8)

        # Title bar
        title_row = QHBoxLayout()
        lbl_title = QLabel("🎨  IconMaker")
        lbl_title.setObjectName("title")
        lbl_ver = QLabel(f"v{VERSION}")
        lbl_ver.setObjectName("version")
        title_row.addWidget(lbl_title)
        title_row.addWidget(lbl_ver)
        title_row.addStretch()
        layout.addLayout(title_row)

        # App list label + Select All / Deselect All
        list_header = QHBoxLayout()
        list_header.addWidget(QLabel("Apps to generate icons for:"))
        list_header.addStretch()
        btn_all = QPushButton("Select All")
        btn_all.setObjectName("secondary")
        btn_all.setFixedWidth(90)
        btn_none = QPushButton("Deselect All")
        btn_none.setObjectName("secondary")
        btn_none.setFixedWidth(90)
        btn_all.clicked.connect(self._select_all)
        btn_none.clicked.connect(self._deselect_all)
        list_header.addWidget(btn_all)
        list_header.addWidget(btn_none)
        layout.addLayout(list_header)

        # App list
        self.app_list = QListWidget()
        self.app_list.setFixedHeight(180)
        for app in make_icons.APPS:
            item = QListWidgetItem(app["name"])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.app_list.addItem(item)
        layout.addWidget(self.app_list)

        # Config row
        cfg_layout = QHBoxLayout()
        cfg_layout.addWidget(QLabel("ComfyUI URL:"))
        self.url_edit = QLineEdit(make_icons.COMFY_URL)
        cfg_layout.addWidget(self.url_edit, 2)
        cfg_layout.addWidget(QLabel("Output Folder:"))
        self.output_edit = QLineEdit(str(make_icons.COMFY_OUTPUT))
        cfg_layout.addWidget(self.output_edit, 3)
        layout.addLayout(cfg_layout)

        # Generate button + progress label
        gen_row = QHBoxLayout()
        self.btn_generate = QPushButton("Generate Icons")
        self.btn_generate.setFixedWidth(150)
        self.btn_generate.clicked.connect(self._start_generation)
        self.lbl_progress = QLabel("")
        self.lbl_progress.setObjectName("progress")
        gen_row.addWidget(self.btn_generate)
        gen_row.addWidget(self.lbl_progress)
        gen_row.addStretch()
        layout.addLayout(gen_row)

        # Log
        layout.addWidget(QLabel("Log:"))
        self.log_box = QTextEdit()
        self.log_box.setReadOnly(True)
        layout.addWidget(self.log_box, 1)

    def _select_all(self):
        for i in range(self.app_list.count()):
            self.app_list.item(i).setCheckState(Qt.CheckState.Checked)

    def _deselect_all(self):
        for i in range(self.app_list.count()):
            self.app_list.item(i).setCheckState(Qt.CheckState.Unchecked)

    def _log(self, message: str, color: str = TEXT_BRIGHT):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.log_box.textCursor()
        cursor.movePosition(cursor.MoveOperation.End)
        cursor.insertText(message + "\n", fmt)
        self.log_box.setTextCursor(cursor)
        self.log_box.ensureCursorVisible()

    def _on_progress(self, current: int, total: int, name: str):
        self.lbl_progress.setText(f"Processing {current} / {total}: {name}…")

    def _on_finished(self):
        self.btn_generate.setEnabled(True)
        self.lbl_progress.setText("Done.")

    def _start_generation(self):
        selected = []
        for i in range(self.app_list.count()):
            item = self.app_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                selected.append(make_icons.APPS[i])

        if not selected:
            self._log("No apps selected.", WARNING_COL)
            return

        self.btn_generate.setEnabled(False)
        self.lbl_progress.setText(f"Starting…")
        self.log_box.clear()

        comfy_url   = self.url_edit.text().strip() or make_icons.COMFY_URL
        output_path = self.output_edit.text().strip() or str(make_icons.COMFY_OUTPUT)

        self._worker = IconWorker(selected, comfy_url, output_path)
        self._worker.log_line.connect(self._log)
        self._worker.progress.connect(self._on_progress)
        self._worker.finished.connect(self._on_finished)
        self._worker.start()


def main():
    app = QApplication(sys.argv)
    window = IconMakerApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
