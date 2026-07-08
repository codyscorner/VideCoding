import os
import sys
import re
import csv
import json
import string
import fnmatch
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLineEdit, QPushButton, QListWidget, QLabel, QMessageBox, QSpinBox,
    QComboBox, QCheckBox, QFileDialog, QDateEdit, QSizePolicy, QMenu,
    QInputDialog, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QDate, QPoint
from PyQt6.QtGui import QIcon

VERSION = "1.2.0"

CONTENT_MAX_BYTES = 2_000_000  # only the first ~2MB of a file is searched for content matches


def get_presets_file() -> Path:
    if getattr(sys, 'frozen', False):
        exe_name = Path(sys.executable).stem
        return Path(sys.executable).parent / f"{exe_name}_presets.json"
    return Path(__file__).parent / f"{Path(__file__).stem}_presets.json"


def _read_text_snippet(path: str):
    """Read up to CONTENT_MAX_BYTES of a file as text, or None if it looks binary/unreadable"""
    try:
        with open(path, 'rb') as f:
            data = f.read(CONTENT_MAX_BYTES)
        if b'\x00' in data:
            return None
        return data.decode('utf-8', errors='ignore')
    except (OSError, PermissionError):
        return None


class SearchThread(QThread):
    file_found = pyqtSignal(str)
    search_finished = pyqtSignal()
    status_update = pyqtSignal(str)

    def __init__(self, search_term, search_mode="contains", file_types=None,
                 min_size_mb=0, max_size_mb=0, date_after=None, date_before=None,
                 content_search=False, root_folders=None):
        super().__init__()
        self.search_mode = search_mode
        self.min_size_bytes = int(min_size_mb * 1024 * 1024)
        self.max_size_bytes = int(max_size_mb * 1024 * 1024) if max_size_mb > 0 else 0
        self.file_types = set(
            t.lower().strip().lstrip('.')
            for t in (file_types or [])
            if t.strip()
        )
        self.date_after = date_after
        self.date_before = date_before
        self.content_search = content_search
        self.root_folders = root_folders or []
        self.is_running = True

        if search_mode == "contains":
            self._term = search_term.lower()
        elif search_mode == "wildcard":
            self._pattern = search_term.lower()
        elif search_mode == "regex":
            self._regex = re.compile(search_term, re.IGNORECASE)

    def _text_matches(self, text: str) -> bool:
        if self.search_mode == "contains":
            return self._term in text.lower()
        elif self.search_mode == "wildcard":
            return fnmatch.fnmatch(text.lower(), self._pattern)
        elif self.search_mode == "regex":
            return bool(self._regex.search(text))
        return False

    def run(self):
        if self.root_folders:
            roots = self.root_folders
        else:
            roots = ['%s:\\' % d for d in string.ascii_uppercase if os.path.exists('%s:' % d)]

        for root in roots:
            if not self.is_running:
                break
            self.status_update.emit(f"Scanning {root}...")
            self.scan_directory(root)
        if self.is_running:
            self.status_update.emit("Search complete.")
        self.search_finished.emit()

    def scan_directory(self, path):
        try:
            for item in os.scandir(path):
                if not self.is_running:
                    return
                try:
                    if item.is_dir(follow_symlinks=False):
                        self.scan_directory(item.path)
                    elif item.is_file(follow_symlinks=False):
                        if self.content_search:
                            text = _read_text_snippet(item.path)
                            if text is None or not self._text_matches(text):
                                continue
                        else:
                            if not self._text_matches(item.name):
                                continue
                        stat = item.stat()
                        size = stat.st_size
                        if self.min_size_bytes > 0 and size < self.min_size_bytes:
                            continue
                        if self.max_size_bytes > 0 and size > self.max_size_bytes:
                            continue
                        if self.file_types:
                            ext = Path(item.name).suffix.lower().lstrip('.')
                            if ext not in self.file_types:
                                continue
                        if self.date_after is not None or self.date_before is not None:
                            mtime = datetime.fromtimestamp(stat.st_mtime)
                            if self.date_after is not None and mtime < self.date_after:
                                continue
                            if self.date_before is not None and mtime > self.date_before:
                                continue
                        self.file_found.emit(item.path)
                except (PermissionError, OSError):
                    continue
        except (PermissionError, OSError):
            pass

    def stop(self):
        self.is_running = False


class FileFinderApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"File Finder v{VERSION}")
        self.resize(960, 720)
        self.found_count = 0
        self.results = []
        self.presets = self._load_presets()

        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(6)
        main_layout.setContentsMargins(10, 8, 10, 8)

        # --- Row 1: Search input + mode + button ---
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Enter search criteria...")
        self.search_input.returnPressed.connect(self.toggle_search)
        search_layout.addWidget(self.search_input, stretch=1)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Contains", "Wildcard (*?)", "Regex"])
        self.mode_combo.setToolTip(
            "Contains: simple substring match\n"
            "Wildcard: use * and ? (e.g. *.jpg, report_?.txt)\n"
            "Regex: full regular expression (e.g. ^report_\\d+\\.pdf$)"
        )
        self.mode_combo.setFixedWidth(130)
        search_layout.addWidget(self.mode_combo)

        self.search_button = QPushButton("Search")
        self.search_button.clicked.connect(self.toggle_search)
        search_layout.addWidget(self.search_button)
        main_layout.addLayout(search_layout)

        # --- Row 2: Search scope (all drives vs specific root folders) ---
        scope_layout = QHBoxLayout()
        scope_layout.setSpacing(8)
        self.search_all_check = QCheckBox("Search entire computer (all drives)")
        self.search_all_check.setChecked(True)
        self.search_all_check.stateChanged.connect(self._on_scope_toggled)
        scope_layout.addWidget(self.search_all_check)

        self.roots_list = QListWidget()
        self.roots_list.setFixedHeight(50)
        self.roots_list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.roots_list.setEnabled(False)
        scope_layout.addWidget(self.roots_list, stretch=1)

        self.add_root_button = QPushButton("Add Folder")
        self.add_root_button.setEnabled(False)
        self.add_root_button.clicked.connect(self._add_root_folder)
        scope_layout.addWidget(self.add_root_button)

        self.remove_root_button = QPushButton("Remove")
        self.remove_root_button.setEnabled(False)
        self.remove_root_button.clicked.connect(self._remove_selected_roots)
        scope_layout.addWidget(self.remove_root_button)
        main_layout.addLayout(scope_layout)

        # --- Row 3: Filters ---
        filter_layout = QHBoxLayout()
        filter_layout.setSpacing(8)

        filter_layout.addWidget(QLabel("Types:"))
        self.type_input = QLineEdit()
        self.type_input.setPlaceholderText(".jpg .png .pdf")
        self.type_input.setFixedWidth(130)
        self.type_input.setToolTip("Space or comma-separated extensions. Empty = all types.")
        filter_layout.addWidget(self.type_input)

        filter_layout.addWidget(QLabel("Min MB:"))
        self.min_size_spin = QSpinBox()
        self.min_size_spin.setRange(0, 999999)
        self.min_size_spin.setValue(0)
        self.min_size_spin.setFixedWidth(70)
        filter_layout.addWidget(self.min_size_spin)

        filter_layout.addWidget(QLabel("Max MB:"))
        self.max_size_spin = QSpinBox()
        self.max_size_spin.setRange(0, 999999)
        self.max_size_spin.setValue(0)
        self.max_size_spin.setToolTip("0 = no upper limit")
        self.max_size_spin.setFixedWidth(70)
        filter_layout.addWidget(self.max_size_spin)

        self.after_check = QCheckBox("After:")
        self.after_check.stateChanged.connect(lambda s: self.after_date.setEnabled(bool(s)))
        filter_layout.addWidget(self.after_check)
        self.after_date = QDateEdit()
        self.after_date.setCalendarPopup(True)
        self.after_date.setDisplayFormat("yyyy-MM-dd")
        self.after_date.setDate(QDate.currentDate().addYears(-1))
        self.after_date.setEnabled(False)
        self.after_date.setFixedWidth(105)
        filter_layout.addWidget(self.after_date)

        self.before_check = QCheckBox("Before:")
        self.before_check.stateChanged.connect(lambda s: self.before_date.setEnabled(bool(s)))
        filter_layout.addWidget(self.before_check)
        self.before_date = QDateEdit()
        self.before_date.setCalendarPopup(True)
        self.before_date.setDisplayFormat("yyyy-MM-dd")
        self.before_date.setDate(QDate.currentDate())
        self.before_date.setEnabled(False)
        self.before_date.setFixedWidth(105)
        filter_layout.addWidget(self.before_date)

        self.content_search_check = QCheckBox("Search file contents")
        self.content_search_check.setToolTip(
            "Match the search term against each file's text content instead of its name.\n"
            "Binary files are skipped automatically. Only the first ~2MB of each file is searched."
        )
        filter_layout.addWidget(self.content_search_check)

        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # --- Row 4: Saved search presets ---
        preset_layout = QHBoxLayout()
        preset_layout.setSpacing(8)
        preset_layout.addWidget(QLabel("Preset:"))
        self.preset_combo = QComboBox()
        self.preset_combo.setFixedWidth(180)
        self._refresh_preset_combo()
        preset_layout.addWidget(self.preset_combo)

        self.load_preset_button = QPushButton("Load")
        self.load_preset_button.clicked.connect(self._load_preset)
        preset_layout.addWidget(self.load_preset_button)

        self.save_preset_button = QPushButton("Save As...")
        self.save_preset_button.clicked.connect(self._save_preset)
        preset_layout.addWidget(self.save_preset_button)

        self.delete_preset_button = QPushButton("Delete")
        self.delete_preset_button.clicked.connect(self._delete_preset)
        preset_layout.addWidget(self.delete_preset_button)

        preset_layout.addStretch()
        main_layout.addLayout(preset_layout)

        # --- Results list ---
        self.results_list = QListWidget()
        self.results_list.itemClicked.connect(self.copy_to_clipboard)
        self.results_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.results_list.customContextMenuRequested.connect(self._show_results_context_menu)
        main_layout.addWidget(self.results_list)

        # --- Status bar ---
        bottom_layout = QHBoxLayout()
        self.status_label = QLabel("Ready")
        bottom_layout.addWidget(self.status_label, stretch=1)

        self.export_button = QPushButton("Export CSV")
        self.export_button.clicked.connect(self.export_results)
        self.export_button.setEnabled(False)
        bottom_layout.addWidget(self.export_button)

        self.count_label = QLabel("Files found: 0")
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        bottom_layout.addWidget(self.count_label)
        main_layout.addLayout(bottom_layout)

        self._apply_styles()
        self.search_thread = None

    # ---------- Search scope ----------

    def _on_scope_toggled(self, state):
        specific_folders = not bool(state)
        self.roots_list.setEnabled(specific_folders)
        self.add_root_button.setEnabled(specific_folders)
        self.remove_root_button.setEnabled(specific_folders)

    def _add_root_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add Root Folder", str(Path.home()))
        if folder:
            existing = [self.roots_list.item(i).text() for i in range(self.roots_list.count())]
            if folder not in existing:
                self.roots_list.addItem(folder)

    def _remove_selected_roots(self):
        for item in self.roots_list.selectedItems():
            self.roots_list.takeItem(self.roots_list.row(item))

    def _get_root_folders(self):
        return [self.roots_list.item(i).text() for i in range(self.roots_list.count())]

    def _get_file_types(self):
        raw = self.type_input.text().strip()
        if not raw:
            return []
        return re.split(r'[\s,]+', raw)

    def toggle_search(self):
        if self.search_thread is not None and self.search_thread.isRunning():
            self.search_thread.stop()
            self.search_thread.wait()
            self.search_button.setText("Search")
            self.status_label.setText("Search cancelled.")
            return

        search_term = self.search_input.text().strip()
        if not search_term:
            QMessageBox.warning(self, "Input Error", "Please enter a search term.")
            return

        root_folders = []
        if not self.search_all_check.isChecked():
            root_folders = self._get_root_folders()
            if not root_folders:
                QMessageBox.warning(self, "Input Error", "Add at least one root folder, or check 'Search entire computer'.")
                return

        mode_text = self.mode_combo.currentText()
        if mode_text == "Contains":
            mode = "contains"
        elif mode_text.startswith("Wildcard"):
            mode = "wildcard"
        else:
            mode = "regex"
            try:
                re.compile(search_term)
            except re.error as e:
                QMessageBox.critical(self, "Invalid Regex", f"Invalid regular expression:\n{e}")
                return

        date_after = None
        if self.after_check.isChecked():
            qd = self.after_date.date()
            date_after = datetime(qd.year(), qd.month(), qd.day(), 0, 0, 0)

        date_before = None
        if self.before_check.isChecked():
            qd = self.before_date.date()
            date_before = datetime(qd.year(), qd.month(), qd.day(), 23, 59, 59)

        self.results_list.clear()
        self.results.clear()
        self.found_count = 0
        self.count_label.setText("Files found: 0")
        self.export_button.setEnabled(False)
        self.search_button.setText("Stop")
        self.status_label.setText("Initializing search...")

        self.search_thread = SearchThread(
            search_term=search_term,
            search_mode=mode,
            file_types=self._get_file_types(),
            min_size_mb=self.min_size_spin.value(),
            max_size_mb=self.max_size_spin.value(),
            date_after=date_after,
            date_before=date_before,
            content_search=self.content_search_check.isChecked(),
            root_folders=root_folders,
        )
        self.search_thread.file_found.connect(self.on_file_found)
        self.search_thread.status_update.connect(self.on_status_update)
        self.search_thread.search_finished.connect(self.on_search_finished)
        self.search_thread.start()

    def on_file_found(self, path):
        self.results_list.addItem(path)
        self.results.append(path)
        self.found_count += 1
        self.count_label.setText(f"Files found: {self.found_count}")

    def on_status_update(self, message):
        self.status_label.setText(message)

    def on_search_finished(self):
        self.search_button.setText("Search")
        if self.results:
            self.export_button.setEnabled(True)

    def copy_to_clipboard(self, item):
        path = item.text()
        QApplication.clipboard().setText(path)
        self.status_label.setText(f"Copied: {path}")

    # ---------- Results context menu ----------

    def _show_results_context_menu(self, pos: QPoint):
        item = self.results_list.itemAt(pos)
        if item is None:
            return
        path = item.text()

        menu = QMenu(self)
        open_action = menu.addAction("Open")
        open_folder_action = menu.addAction("Open Containing Folder")
        copy_action = menu.addAction("Copy Path")
        menu.addSeparator()
        delete_action = menu.addAction("Delete File")

        chosen = menu.exec(self.results_list.mapToGlobal(pos))
        if chosen is None:
            return

        if chosen == open_action:
            self._open_path(path)
        elif chosen == open_folder_action:
            self._open_containing_folder(path)
        elif chosen == copy_action:
            QApplication.clipboard().setText(path)
            self.status_label.setText(f"Copied: {path}")
        elif chosen == delete_action:
            self._delete_result(item, path)

    def _open_path(self, path):
        try:
            os.startfile(path)
        except OSError as e:
            QMessageBox.critical(self, "Open Failed", f"Could not open file:\n{e}")

    def _open_containing_folder(self, path):
        try:
            subprocess.run(['explorer', '/select,', path])
        except OSError as e:
            QMessageBox.critical(self, "Open Failed", f"Could not open containing folder:\n{e}")

    def _delete_result(self, item, path):
        reply = QMessageBox.warning(
            self, "Delete File",
            f"Permanently delete this file?\n\n{path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            os.remove(path)
            row = self.results_list.row(item)
            self.results_list.takeItem(row)
            if path in self.results:
                self.results.remove(path)
            self.found_count = len(self.results)
            self.count_label.setText(f"Files found: {self.found_count}")
            self.status_label.setText(f"Deleted: {path}")
        except OSError as e:
            QMessageBox.critical(self, "Delete Failed", f"Could not delete file:\n{e}")

    # ---------- Saved search presets ----------

    def _load_presets(self) -> dict:
        presets_file = get_presets_file()
        if presets_file.exists():
            try:
                with open(presets_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _save_presets(self):
        try:
            with open(get_presets_file(), 'w', encoding='utf-8') as f:
                json.dump(self.presets, f, indent=2)
        except OSError:
            pass

    def _refresh_preset_combo(self):
        self.preset_combo.clear()
        self.preset_combo.addItems(sorted(self.presets.keys()))

    def _save_preset(self):
        name, ok = QInputDialog.getText(self, "Save Preset", "Preset name:")
        name = name.strip()
        if not ok or not name:
            return

        self.presets[name] = {
            'search_term': self.search_input.text(),
            'mode': self.mode_combo.currentText(),
            'file_types': self.type_input.text(),
            'min_size_mb': self.min_size_spin.value(),
            'max_size_mb': self.max_size_spin.value(),
            'after_enabled': self.after_check.isChecked(),
            'after_date': self.after_date.date().toString("yyyy-MM-dd"),
            'before_enabled': self.before_check.isChecked(),
            'before_date': self.before_date.date().toString("yyyy-MM-dd"),
            'content_search': self.content_search_check.isChecked(),
            'search_all_drives': self.search_all_check.isChecked(),
            'root_folders': self._get_root_folders(),
        }
        self._save_presets()
        self._refresh_preset_combo()
        self.preset_combo.setCurrentText(name)
        self.status_label.setText(f"Preset saved: {name}")

    def _load_preset(self):
        name = self.preset_combo.currentText()
        if not name or name not in self.presets:
            return
        p = self.presets[name]

        self.search_input.setText(p.get('search_term', ''))
        self.mode_combo.setCurrentText(p.get('mode', 'Contains'))
        self.type_input.setText(p.get('file_types', ''))
        self.min_size_spin.setValue(p.get('min_size_mb', 0))
        self.max_size_spin.setValue(p.get('max_size_mb', 0))

        self.after_check.setChecked(p.get('after_enabled', False))
        after_date = QDate.fromString(p.get('after_date', ''), "yyyy-MM-dd")
        if after_date.isValid():
            self.after_date.setDate(after_date)

        self.before_check.setChecked(p.get('before_enabled', False))
        before_date = QDate.fromString(p.get('before_date', ''), "yyyy-MM-dd")
        if before_date.isValid():
            self.before_date.setDate(before_date)

        self.content_search_check.setChecked(p.get('content_search', False))

        self.roots_list.clear()
        self.roots_list.addItems(p.get('root_folders', []))
        self.search_all_check.setChecked(p.get('search_all_drives', True))

        self.status_label.setText(f"Preset loaded: {name}")

    def _delete_preset(self):
        name = self.preset_combo.currentText()
        if not name or name not in self.presets:
            return
        reply = QMessageBox.question(
            self, "Delete Preset", f"Delete preset '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self.presets[name]
        self._save_presets()
        self._refresh_preset_combo()
        self.status_label.setText(f"Preset deleted: {name}")

    def export_results(self):
        if not self.results:
            QMessageBox.information(self, "No Results", "No results to export.")
            return

        path, selected_filter = QFileDialog.getSaveFileName(
            self, "Export Results", "", "CSV Files (*.csv);;Text Files (*.txt)"
        )
        if not path:
            return

        if path.lower().endswith('.txt'):
            with open(path, 'w', encoding='utf-8') as f:
                for p in self.results:
                    f.write(p + '\n')
        else:
            if not path.lower().endswith('.csv'):
                path += '.csv'
            with open(path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow(['File Name', 'Full Path', 'Size (bytes)', 'Modified'])
                for p in self.results:
                    try:
                        st = os.stat(p)
                        name = Path(p).name
                        size = st.st_size
                        modified = datetime.fromtimestamp(st.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    except OSError:
                        name = Path(p).name
                        size = ''
                        modified = ''
                    writer.writerow([name, p, size, modified])

        self.status_label.setText(f"Exported {len(self.results)} results to: {Path(path).name}")

    def _apply_styles(self):
        self.setStyleSheet("""
            QWidget {
                background-color: #0f2916;
                color: #e8f5e9;
                font-family: Segoe UI, Arial, sans-serif;
                font-size: 13px;
            }
            QLineEdit, QSpinBox, QComboBox, QDateEdit {
                background-color: #1b4324;
                border: 1px solid #2e7d32;
                border-radius: 4px;
                padding: 5px;
                color: #e8f5e9;
            }
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus, QDateEdit:focus {
                border: 1px solid #4caf50;
            }
            QLineEdit:disabled, QSpinBox:disabled, QDateEdit:disabled {
                background-color: #122b18;
                color: #3d6b41;
                border-color: #1b4324;
            }
            QComboBox::drop-down { border: none; }
            QComboBox QAbstractItemView {
                background-color: #1b4324;
                selection-background-color: #2e7d32;
                color: #e8f5e9;
            }
            QDateEdit::drop-down { border: none; }
            QPushButton {
                background-color: #2e7d32;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #388e3c; }
            QPushButton:pressed { background-color: #1b5e20; }
            QPushButton:disabled {
                background-color: #1b3a1e;
                color: #4a7a4d;
            }
            QListWidget {
                background-color: #14361d;
                border: 1px solid #2e7d32;
                border-radius: 4px;
                outline: none;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #1b4324;
            }
            QListWidget::item:selected {
                background-color: #2e7d32;
                color: white;
            }
            QListWidget::item:hover { background-color: #1b4324; }
            QMenu {
                background-color: #1b4324;
                color: #e8f5e9;
                border: 1px solid #2e7d32;
            }
            QMenu::item:selected {
                background-color: #2e7d32;
            }
            QLabel {
                color: #a5d6a7;
                font-size: 12px;
            }
            QCheckBox {
                color: #a5d6a7;
                font-size: 12px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border: 1px solid #2e7d32;
                border-radius: 2px;
                background-color: #1b4324;
            }
            QCheckBox::indicator:checked { background-color: #2e7d32; }
        """)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = FileFinderApp()
    window.show()
    sys.exit(app.exec())
