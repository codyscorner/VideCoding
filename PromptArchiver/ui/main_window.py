"""Main window: menus, splitter (sidebar | content), status feedback."""

import json
import os
from pathlib import Path

from PyQt6.QtCore import QSettings, Qt
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QLabel, QMainWindow, QMessageBox, QPushButton,
    QSplitter, QToolBar, QWidget,
)

from archive import PromptArchive
from ui.content_area import ContentArea
from ui.prompt_dialog import PromptDialog
from ui.settings_dialog import SettingsDialog
from ui.sidebar import Sidebar

STATUS_MS = 6000

ABOUT_TEXT = (
    "A desktop application for storing, organizing, and viewing AI prompts "
    "alongside their generated outputs (text, images, or videos).\n\n"
    "Features:\n"
    "• Local-first storage with no cloud dependency\n"
    "• Automatic organization by content type\n"
    "• Built-in viewers for text, images, and videos\n"
    "• Search and filter capabilities\n"
    "• Export and backup functionality"
)


class MainWindow(QMainWindow):
    def __init__(self, version: str):
        super().__init__()
        self._version = version
        self.setWindowTitle(f"Prompt Archiver (v{version})")
        self.resize(1200, 800)

        self._settings = QSettings("VibeCoded", "Prompt Archiver")
        self._archive: PromptArchive | None = None

        self._build_menu()
        self._build_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.sidebar = Sidebar()
        self.sidebar.setMinimumWidth(280)
        splitter.addWidget(self.sidebar)

        self.content = ContentArea(lambda: self._archive)
        splitter.addWidget(self.content)
        splitter.setSizes([300, 900])
        splitter.setStretchFactor(1, 1)
        self.setCentralWidget(splitter)

        self._count_label = QLabel("0 prompts")
        self.statusBar().addPermanentWidget(self._count_label)

        self.sidebar.promptSelected.connect(self.content.show_prompt)
        self.sidebar.settingsRequested.connect(self._open_settings)
        self.sidebar.exportRequested.connect(self._export_prompts)
        self.content.statusMessage.connect(self._status)
        self.content.mutated.connect(self._on_mutated)
        self.content.editRequested.connect(self._edit_prompt)

        self._initialize_archive()

    # ---- chrome -----------------------------------------------------------

    def _build_menu(self) -> None:
        file_menu = self.menuBar().addMenu("&File")

        new_action = QAction("New Prompt", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._add_prompt)
        file_menu.addAction(new_action)
        file_menu.addSeparator()

        settings_action = QAction("Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+,"))
        settings_action.triggered.connect(self._open_settings)
        file_menu.addAction(settings_action)
        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut(QKeySequence("Ctrl+Q"))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = self.menuBar().addMenu("&Help")
        about_action = QAction("About Prompt Archiver", self)
        about_action.triggered.connect(lambda: QMessageBox.information(
            self, "About Prompt Archiver",
            f"Prompt Archiver v{self._version}\n\n{ABOUT_TEXT}"))
        help_menu.addAction(about_action)

        guide_action = QAction("Usage Guide", self)
        guide_action.triggered.connect(self._show_usage_guide)
        help_menu.addAction(guide_action)

    def _build_toolbar(self) -> None:
        toolbar = QToolBar()
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        new_btn = QPushButton("+ New Prompt")
        new_btn.setObjectName("primaryBtn")
        new_btn.clicked.connect(self._add_prompt)
        toolbar.addWidget(new_btn)

    def _show_usage_guide(self) -> None:
        from ui.settings_dialog import HELP_TEXT
        QMessageBox.information(self, "How to Use Prompt Archiver", HELP_TEXT)

    def _status(self, message: str) -> None:
        self.statusBar().showMessage(message, STATUS_MS)

    # ---- archive lifecycle ---------------------------------------------------

    def _initialize_archive(self) -> None:
        path = self._settings.value("archivePath", "", type=str)
        if not path:
            path = self._migrate_electron_setting()
        if not path:
            self._status("Please select an archive folder to get started")
            self._open_settings(first_run=True)
            return
        self._set_archive(path)

    @staticmethod
    def _migrate_electron_setting() -> str:
        """One-time pickup of the v1.x electron-store archive path."""
        config = (Path(os.environ.get("APPDATA", "")) / "prompt-archiver"
                  / "config.json")
        try:
            data = json.loads(config.read_text(encoding="utf-8"))
            path = data.get("archivePath", "")
            return path if path and Path(path).is_dir() else ""
        except (OSError, json.JSONDecodeError):
            return ""

    def _set_archive(self, path: str) -> None:
        self._archive = PromptArchive(path)
        try:
            self._archive.ensure_structure()
        except OSError as exc:
            QMessageBox.warning(self, "Archive",
                                f"Could not create archive folders:\n{exc}")
            self._archive = None
            return
        self._settings.setValue("archivePath", path)
        self._reload()

    def _reload(self, reselect_folder: str | None = None) -> None:
        if self._archive is None:
            return
        prompts = self._archive.load_prompts()
        self.sidebar.set_prompts(prompts)
        self._count_label.setText(
            f"{len(prompts)} prompt{'s' if len(prompts) != 1 else ''}")
        if reselect_folder:
            self.sidebar.select_folder(reselect_folder)
            for p in prompts:
                if p["folderName"] == reselect_folder:
                    self.content.show_prompt(p)
                    break

    def _on_mutated(self, folder_name: str) -> None:
        self._reload(reselect_folder=folder_name or None)
        if not folder_name:
            self.content.show_prompt(None)

    # ---- actions -----------------------------------------------------------

    def _add_prompt(self) -> None:
        if self._archive is None:
            self._status("Please select an archive folder first")
            self._open_settings()
            return
        dialog = PromptDialog(mode="add", parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        data = dialog.data()
        try:
            folder = self._archive.save_prompt(data)
        except OSError as exc:
            QMessageBox.warning(self, "Save Prompt", f"Error saving prompt:\n{exc}")
            return
        self._status("Prompt saved successfully")
        self._reload(reselect_folder=Path(folder).name)

    def _edit_prompt(self, prompt: dict) -> None:
        if self._archive is None:
            return
        dialog = PromptDialog(mode="edit", prompt=prompt, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self._archive.update_prompt(prompt["path"], dialog.data())
            if dialog.file_mode() == "replace":
                self._archive.replace_files(prompt["path"], dialog.staged_files())
            elif dialog.file_mode() == "add":
                self._archive.append_files(prompt["path"], dialog.staged_files())
        except OSError as exc:
            QMessageBox.warning(self, "Edit Prompt", f"Error updating prompt:\n{exc}")
            return
        self._status("Prompt updated successfully")
        self._reload(reselect_folder=prompt["folderName"])

    def _export_prompts(self, prompts: list[dict]) -> None:
        if not prompts:
            self._status("No prompts selected for export")
            return
        zip_path, _ = QFileDialog.getSaveFileName(
            self, "Export Prompts", "prompt_export.zip", "ZIP Files (*.zip)")
        if not zip_path:
            return
        try:
            size = PromptArchive.export_zip([p["path"] for p in prompts], zip_path)
        except OSError as exc:
            QMessageBox.warning(self, "Export", f"Export failed:\n{exc}")
            return
        self._status(
            f"Exported {len(prompts)} prompt{'s' if len(prompts) != 1 else ''} "
            f"({size // 1024} KB)")
        self.sidebar.clear_export_selection()

    def _open_settings(self, first_run: bool = False) -> None:
        current = self._settings.value("archivePath", "", type=str)
        if first_run and not current:
            current = str(Path.home() / "Prompt_Archive")
        dialog = SettingsDialog(current, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        new_path = dialog.archive_path()
        if new_path and (dialog.path_changed() or self._archive is None):
            self._set_archive(new_path)
            self._status("Archive location updated")
