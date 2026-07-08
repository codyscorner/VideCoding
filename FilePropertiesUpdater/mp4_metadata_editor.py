"""
MP4 Metadata Editor
Drag and drop one or more MP4/M4A/MKV files to update their metadata.
Only fields that are filled in will be written — blank fields are ignored.
Version: 1.2.0
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QLabel, QPushButton,
    QLineEdit, QTextEdit, QListWidget, QListWidgetItem,
    QGroupBox, QVBoxLayout, QHBoxLayout, QGridLayout,
    QScrollArea, QSizePolicy, QStatusBar, QComboBox, QCheckBox,
    QFileDialog, QMessageBox, QDialog, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal
from PyQt6.QtGui import QIcon, QColor, QDragEnterEvent, QDropEvent

try:
    import mutagen.mp4
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "mutagen"])
    import mutagen.mp4

APP_TITLE = "MP4 Metadata Editor"
VERSION = "1.2.0"

SUPPORTED_EXTS = (".mp4", ".m4a", ".mkv")
PRESETS_FILE = Path(__file__).parent / "tag_presets.json"

_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# Metadata field definitions: (label, mutagen_key, is_integer, multiline)
FIELDS = [
    ("Title",            "\xa9nam", False, False),
    ("Artist",           "\xa9ART", False, False),
    ("Album Artist",     "aART",    False, False),
    ("Album",            "\xa9alb", False, False),
    ("Year",             "\xa9day", False, False),
    ("Genre",            "\xa9gen", False, False),
    ("Composer",         "\xa9wrt", False, False),
    ("Grouping",         "\xa9grp", False, False),
    ("Copyright",        "cprt",    False, False),
    ("Show",             "tvsh",    False, False),
    ("Episode ID",       "tven",    False, False),
    ("Episode Number",   "tves",    True,  False),
    ("Season Number",    "tvsn",    True,  False),
    ("Category",         "catg",    False, False),
    ("Keywords",         "keyw",    False, False),
    ("Comment",          "\xa9cmt", False, True),
    ("Description",      "desc",    False, True),
    ("Long Description", "ldes",    False, True),
    ("Lyrics",           "\xa9lyr", False, True),
]

# Dark slate-blue color scheme
COLORS = {
    'bg_dark':      '#0d1117',
    'bg_medium':    '#161b22',
    'bg_light':     '#21262d',
    'fg_primary':   '#e6edf3',
    'fg_secondary': '#8b949e',
    'fg_dim':       '#484f58',
    'accent':       '#1f6feb',
    'accent_hover': '#388bfd',
    'accent_dark':  '#0d419d',
    'border':       '#30363d',
    'success':      '#3fb950',
    'error':        '#f85149',
    'warning':      '#e3b341',
    'drop_bg':      '#0a1628',
    'drop_border':  '#1f6feb',
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
QLabel#drop_zone {{
    background-color: {COLORS['drop_bg']};
    color: {COLORS['accent_hover']};
    border: 2px dashed {COLORS['drop_border']};
    border-radius: 6px;
    font-size: 10pt;
    font-style: italic;
    padding: 16px;
}}
QLabel#drop_zone:hover {{
    background-color: {COLORS['bg_medium']};
    border-color: {COLORS['accent_hover']};
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
    padding: 5px;
    font-size: 10pt;
}}
QLineEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QTextEdit {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    padding: 4px;
    font-size: 10pt;
}}
QTextEdit:focus {{
    border: 1px solid {COLORS['accent']};
}}
QPushButton {{
    background-color: {COLORS['accent']};
    color: white;
    font-weight: bold;
    border: none;
    border-radius: 4px;
    padding: 8px 18px;
    font-size: 10pt;
}}
QPushButton:hover {{
    background-color: {COLORS['accent_hover']};
}}
QPushButton:disabled {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_dim']};
}}
QPushButton#secondary_btn {{
    background-color: {COLORS['bg_light']};
    color: {COLORS['fg_primary']};
    font-weight: normal;
    padding: 6px 14px;
    font-size: 9pt;
}}
QPushButton#secondary_btn:hover {{
    background-color: {COLORS['accent_dark']};
    color: white;
}}
QListWidget {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_primary']};
    border: 1px solid {COLORS['border']};
    border-radius: 3px;
    font-family: Consolas;
    font-size: 9pt;
}}
QListWidget::item:selected {{
    background-color: {COLORS['accent']};
    color: white;
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
QStatusBar {{
    background-color: {COLORS['bg_medium']};
    color: {COLORS['fg_secondary']};
    border-top: 1px solid {COLORS['border']};
    font-size: 9pt;
    padding: 3px 8px;
}}
"""


def _mkv_tag_name(label: str) -> str:
    return label.lower().replace(" ", "_")


def derive_title_from_filename(path: str) -> str:
    name = os.path.splitext(os.path.basename(path))[0]
    name = re.sub(r"^\s*\d+[\s._-]+", "", name)
    name = re.sub(r"[_\-.]+", " ", name)
    return re.sub(r"\s+", " ", name).strip()


def write_metadata(filepath: str, fields: dict) -> tuple[bool, str]:
    if filepath.lower().endswith(".mkv"):
        return _write_metadata_mkv(filepath, fields)
    return _write_metadata_mp4(filepath, fields)


def _write_metadata_mp4(filepath: str, fields: dict) -> tuple[bool, str]:
    try:
        audio = mutagen.mp4.MP4(filepath)
        if audio.tags is None:
            audio.add_tags()
        changed = 0
        for label, key, is_int, _ in FIELDS:
            value = fields.get(key, "").strip()
            if not value:
                continue
            if is_int:
                try:
                    audio.tags[key] = [int(value)]
                except ValueError:
                    return False, f"'{label}' must be a whole number."
            else:
                audio.tags[key] = [value]
            changed += 1
        if changed == 0:
            return False, "No fields to write (all blank)."
        audio.save()
        return True, f"Updated {changed} field(s)."
    except Exception as exc:
        return False, str(exc)


def _write_metadata_mkv(filepath: str, fields: dict) -> tuple[bool, str]:
    metadata_args = []
    changed = 0
    for label, key, is_int, _ in FIELDS:
        value = fields.get(key, "").strip()
        if not value:
            continue
        if is_int:
            try:
                int(value)
            except ValueError:
                return False, f"'{label}' must be a whole number."
        metadata_args += ["-metadata", f"{_mkv_tag_name(label)}={value}"]
        changed += 1
    if changed == 0:
        return False, "No fields to write (all blank)."

    fd, tmp_path = tempfile.mkstemp(suffix=".mkv")
    os.close(fd)
    try:
        cmd = ["ffmpeg", "-y", "-i", filepath, "-map", "0", "-c", "copy"] + metadata_args + [tmp_path]
        result = subprocess.run(cmd, capture_output=True, text=True, creationflags=_NO_WINDOW)
        if result.returncode != 0:
            return False, "ffmpeg error: " + result.stderr.strip()[-300:]
        shutil.move(tmp_path, filepath)
        return True, f"Updated {changed} field(s)."
    except FileNotFoundError:
        return False, "ffmpeg not found — install ffmpeg and add it to PATH to edit MKV files."
    except Exception as exc:
        return False, str(exc)
    finally:
        if os.path.exists(tmp_path):
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def read_metadata(filepath: str) -> dict:
    if filepath.lower().endswith(".mkv"):
        return _read_metadata_mkv(filepath)
    return _read_metadata_mp4(filepath)


def _read_metadata_mp4(filepath: str) -> dict:
    result = {}
    try:
        audio = mutagen.mp4.MP4(filepath)
        tags = audio.tags or {}
        for _, key, _, _ in FIELDS:
            if key in tags and tags[key]:
                result[key] = str(tags[key][0])
    except Exception:
        pass
    return result


def _read_metadata_mkv(filepath: str) -> dict:
    result = {}
    try:
        cmd = ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_entries", "format_tags", filepath]
        proc = subprocess.run(cmd, capture_output=True, text=True, creationflags=_NO_WINDOW)
        data = json.loads(proc.stdout or "{}")
        tags = data.get("format", {}).get("tags", {}) or {}
        lower_tags = {k.lower(): v for k, v in tags.items()}
        for label, key, _, _ in FIELDS:
            tag_name = _mkv_tag_name(label)
            if tag_name in lower_tags:
                result[key] = lower_tags[tag_name]
    except Exception:
        pass
    return result


def load_presets() -> dict:
    if PRESETS_FILE.exists():
        try:
            return json.loads(PRESETS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}


def save_presets(presets: dict) -> None:
    PRESETS_FILE.write_text(json.dumps(presets, indent=2), encoding="utf-8")


class DropZoneLabel(QLabel):
    files_dropped = pyqtSignal(list)

    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setObjectName("drop_zone")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(SUPPORTED_EXTS)
        ]
        if paths:
            self.files_dropped.emit(paths)


class ResultDialog(QDialog):
    def __init__(self, parent, summary: str, results: list):
        super().__init__(parent)
        self.setWindowTitle("Results")
        self.setMinimumSize(560, 340)
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)

        title = QLabel(summary)
        title.setObjectName("header")
        layout.addWidget(title)

        txt = QTextEdit()
        txt.setReadOnly(True)
        layout.addWidget(txt, stretch=1)

        for success, name, msg in results:
            icon = "\u2713" if success else "\u2717"
            color = COLORS['success'] if success else COLORS['error']
            txt.append(f'<span style="color:{color}">{icon}  {name}<br>&nbsp;&nbsp;&nbsp;&nbsp;{msg}</span><br>')

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)


class MetadataPreviewDialog(QDialog):
    def __init__(self, parent, filename: str, values: dict):
        super().__init__(parent)
        self.setWindowTitle(f"Current Metadata — {filename}")
        self.setMinimumSize(480, 420)
        self.setStyleSheet(parent.styleSheet())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)

        title = QLabel(filename)
        title.setObjectName("header")
        layout.addWidget(title)

        txt = QTextEdit()
        txt.setReadOnly(True)
        lines = [f"<b>{label}:</b> {values[key]}" for label, key, _, _ in FIELDS if values.get(key)]
        txt.setHtml("<br>".join(lines) if lines else "<i>No metadata tags found.</i>")
        layout.addWidget(txt, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        load_btn = QPushButton("Load Into Fields")
        load_btn.clicked.connect(self.accept)
        btn_row.addWidget(load_btn)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("secondary_btn")
        close_btn.clicked.connect(self.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class MainWindow(QMainWindow):
    _results_ready = pyqtSignal(str, list, str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_TITLE} v{VERSION}")
        self.setMinimumSize(820, 860)
        self.setStyleSheet(STYLESHEET)
        self.setAcceptDrops(True)

        self.queued_files: list[str] = []
        # mutagen_key → QLineEdit or QTextEdit
        self.field_widgets: dict[str, QLineEdit | QTextEdit] = {}

        self._build_ui()
        self._results_ready.connect(self._show_results)

    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(16, 16, 16, 8)
        layout.setSpacing(10)

        # Header
        header = QLabel(APP_TITLE)
        header.setObjectName("header")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)

        subtitle = QLabel("Fill in any fields — blank fields are never overwritten")
        subtitle.setObjectName("subtitle")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(subtitle)

        # Drop zone
        self.drop_label = DropZoneLabel(
            "\u2295  Drag & drop MP4 / M4A / MKV files here  \u2014  or click to browse"
        )
        self.drop_label.setFixedHeight(62)
        self.drop_label.files_dropped.connect(self._add_files)
        self.drop_label.mousePressEvent = lambda _: self._browse()
        layout.addWidget(self.drop_label)

        # File queue
        files_group = QGroupBox("Queued Files")
        files_layout = QVBoxLayout(files_group)
        self.file_list = QListWidget()
        self.file_list.setFixedHeight(100)
        files_layout.addWidget(self.file_list)

        file_btn_row = QHBoxLayout()
        remove_btn = QPushButton("Remove Selected")
        remove_btn.setObjectName("secondary_btn")
        remove_btn.clicked.connect(self._remove_selected)
        file_btn_row.addWidget(remove_btn)

        clear_files_btn = QPushButton("Clear All Files")
        clear_files_btn.setObjectName("secondary_btn")
        clear_files_btn.clicked.connect(self._clear_files)
        file_btn_row.addWidget(clear_files_btn)

        view_meta_btn = QPushButton("View Current Metadata")
        view_meta_btn.setObjectName("secondary_btn")
        view_meta_btn.clicked.connect(self._view_metadata)
        file_btn_row.addWidget(view_meta_btn)
        file_btn_row.addStretch()
        files_layout.addLayout(file_btn_row)
        layout.addWidget(files_group)

        # Presets
        presets_row = QHBoxLayout()
        presets_row.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setEditable(True)
        self.preset_combo.setMinimumWidth(160)
        presets_row.addWidget(self.preset_combo, stretch=1)
        save_preset_btn = QPushButton("Save Preset")
        save_preset_btn.setObjectName("secondary_btn")
        save_preset_btn.clicked.connect(self._save_preset)
        presets_row.addWidget(save_preset_btn)
        load_preset_btn = QPushButton("Load Preset")
        load_preset_btn.setObjectName("secondary_btn")
        load_preset_btn.clicked.connect(self._load_preset)
        presets_row.addWidget(load_preset_btn)
        delete_preset_btn = QPushButton("Delete Preset")
        delete_preset_btn.setObjectName("secondary_btn")
        delete_preset_btn.clicked.connect(self._delete_preset)
        presets_row.addWidget(delete_preset_btn)
        layout.addLayout(presets_row)
        self._refresh_presets()

        # Metadata fields in scrollable area
        fields_group = QGroupBox("Metadata Fields")
        fields_outer = QVBoxLayout(fields_group)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        fields_widget = QWidget()
        fields_grid = QGridLayout(fields_widget)
        fields_grid.setSpacing(6)

        short_fields = [(l, k, n, t) for l, k, n, t in FIELDS if not t]
        long_fields  = [(l, k, n, t) for l, k, n, t in FIELDS if t]

        col_count = 2
        for i, (label, key, is_int, _) in enumerate(short_fields):
            row, col = divmod(i, col_count)
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            hint = " (integer)" if is_int else ""
            lbl = QLabel(f"{label}{hint}")
            lbl.setObjectName("subtitle")
            cell_layout.addWidget(lbl)
            entry = QLineEdit()
            cell_layout.addWidget(entry)
            fields_grid.addWidget(cell, row, col)
            fields_grid.setColumnStretch(col, 1)
            self.field_widgets[key] = entry

        base_row = (len(short_fields) + col_count - 1) // col_count
        for i, (label, key, _, _) in enumerate(long_fields):
            cell = QWidget()
            cell_layout = QVBoxLayout(cell)
            cell_layout.setContentsMargins(0, 0, 0, 0)
            cell_layout.setSpacing(2)
            lbl = QLabel(label)
            lbl.setObjectName("subtitle")
            cell_layout.addWidget(lbl)
            txt = QTextEdit()
            txt.setFixedHeight(80)
            cell_layout.addWidget(txt)
            fields_grid.addWidget(cell, base_row + i, 0, 1, col_count)
            self.field_widgets[key] = txt

        scroll.setWidget(fields_widget)
        fields_outer.addWidget(scroll)
        layout.addWidget(fields_group, stretch=1)

        self.autofill_title_chk = QCheckBox(
            "Auto-fill Title from filename (per file — overrides the Title field above)"
        )
        layout.addWidget(self.autofill_title_chk)

        # Bottom buttons
        bottom_row = QHBoxLayout()
        clear_fields_btn = QPushButton("Clear All Fields")
        clear_fields_btn.setObjectName("secondary_btn")
        clear_fields_btn.clicked.connect(self._clear_fields)
        bottom_row.addWidget(clear_fields_btn)
        bottom_row.addStretch()
        apply_btn = QPushButton("Apply to All Files")
        apply_btn.clicked.connect(self._apply)
        bottom_row.addWidget(apply_btn)
        layout.addLayout(bottom_row)

        # Status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage(
            "Ready — add files and fill in the metadata fields you want to update."
        )

    # ── Drag-drop on main window ──────────────────────────────────────────────
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        paths = [
            u.toLocalFile()
            for u in event.mimeData().urls()
            if u.toLocalFile().lower().endswith(SUPPORTED_EXTS)
        ]
        self._add_files(paths)

    # ── File management ───────────────────────────────────────────────────────
    def _browse(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Select media files", "",
            "Media files (*.mp4 *.m4a *.mkv);;All files (*.*)"
        )
        self._add_files(list(paths))

    def _add_files(self, paths: list[str]):
        added = 0
        for p in paths:
            if p not in self.queued_files:
                self.queued_files.append(p)
                self.file_list.addItem(os.path.basename(p))
                added += 1
        if added:
            self.status_bar.showMessage(
                f"Added {added} file(s).  Total queued: {len(self.queued_files)}."
            )

    def _remove_selected(self):
        for idx in reversed([self.file_list.row(i) for i in self.file_list.selectedItems()]):
            self.file_list.takeItem(idx)
            del self.queued_files[idx]
        self.status_bar.showMessage(f"{len(self.queued_files)} file(s) in queue.")

    def _clear_files(self):
        self.queued_files.clear()
        self.file_list.clear()
        self.status_bar.showMessage("File list cleared.")

    def _clear_fields(self):
        for widget in self.field_widgets.values():
            if isinstance(widget, QTextEdit):
                widget.clear()
            else:
                widget.clear()

    def _load_fields(self, values: dict):
        for key, widget in self.field_widgets.items():
            val = values.get(key, "")
            if isinstance(widget, QTextEdit):
                widget.setPlainText(val)
            else:
                widget.setText(val)

    def _view_metadata(self):
        selected = self.file_list.selectedItems()
        if len(selected) != 1:
            QMessageBox.information(
                self, "Select one file",
                "Select exactly one queued file to view its current metadata."
            )
            return
        idx = self.file_list.row(selected[0])
        path = self.queued_files[idx]
        current = read_metadata(path)
        dlg = MetadataPreviewDialog(self, os.path.basename(path), current)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            self._load_fields(current)
            self.status_bar.showMessage("Loaded current metadata into fields for editing.")

    def _refresh_presets(self):
        presets = load_presets()
        current_text = self.preset_combo.currentText()
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(presets.keys()))
        self.preset_combo.setCurrentText(current_text)

    def _save_preset(self):
        name = self.preset_combo.currentText().strip()
        if not name:
            QMessageBox.warning(self, "Name required", "Enter a name for this preset.")
            return
        fields = {}
        for key, widget in self.field_widgets.items():
            val = widget.toPlainText() if isinstance(widget, QTextEdit) else widget.text()
            if val.strip():
                fields[key] = val
        if not fields:
            QMessageBox.warning(self, "Nothing to save", "Fill in at least one field before saving a preset.")
            return
        presets = load_presets()
        presets[name] = fields
        save_presets(presets)
        self._refresh_presets()
        self.preset_combo.setCurrentText(name)
        self.status_bar.showMessage(f"Saved preset '{name}'.")

    def _load_preset(self):
        name = self.preset_combo.currentText().strip()
        presets = load_presets()
        if name not in presets:
            QMessageBox.warning(self, "Not found", f"No preset named '{name}'.")
            return
        self._load_fields(presets[name])
        self.status_bar.showMessage(f"Loaded preset '{name}'.")

    def _delete_preset(self):
        name = self.preset_combo.currentText().strip()
        presets = load_presets()
        if name not in presets:
            QMessageBox.warning(self, "Not found", f"No preset named '{name}'.")
            return
        if QMessageBox.question(
            self, "Delete preset", f"Delete preset '{name}'?"
        ) != QMessageBox.StandardButton.Yes:
            return
        del presets[name]
        save_presets(presets)
        self._refresh_presets()
        self.status_bar.showMessage(f"Deleted preset '{name}'.")

    # ── Apply metadata ────────────────────────────────────────────────────────
    def _apply(self):
        if not self.queued_files:
            QMessageBox.warning(self, "No files", "Add at least one media file first.")
            return
        fields = {}
        for key, widget in self.field_widgets.items():
            if isinstance(widget, QTextEdit):
                fields[key] = widget.toPlainText()
            else:
                fields[key] = widget.text()
        auto_fill_title = self.autofill_title_chk.isChecked()
        if not auto_fill_title and not any(v.strip() for v in fields.values()):
            QMessageBox.warning(
                self, "Nothing to write",
                "Fill in at least one metadata field before applying."
            )
            return
        self.status_bar.showMessage("Writing metadata\u2026")
        threading.Thread(
            target=self._apply_thread,
            args=(list(self.queued_files), fields, auto_fill_title),
            daemon=True
        ).start()

    def _apply_thread(self, files: list[str], fields: dict, auto_fill_title: bool = False):
        results = []
        ok = fail = 0
        for path in files:
            file_fields = fields
            if auto_fill_title:
                file_fields = dict(fields)
                file_fields["\xa9nam"] = derive_title_from_filename(path)
            success, msg = write_metadata(path, file_fields)
            results.append((success, os.path.basename(path), msg))
            if success:
                ok += 1
            else:
                fail += 1
        summary = f"{ok} file(s) updated"
        if fail:
            summary += f", {fail} failed"
        color = COLORS['success'] if fail == 0 else (COLORS['warning'] if ok > 0 else COLORS['error'])
        self._results_ready.emit(summary, results, color)

    def _show_results(self, summary: str, results: list, color: str):
        self.status_bar.showMessage(summary)
        dlg = ResultDialog(self, summary, results)
        dlg.exec()


def main():
    app = QApplication(sys.argv)
    app.setApplicationName(APP_TITLE)

    from pathlib import Path
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
