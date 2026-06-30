"""Manage Profiles dialog for File Copy Move Manager"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QTextEdit, QMessageBox, QInputDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class ManageProfilesDialog(QDialog):
    def __init__(self, parent: 'MainWindow'):
        super().__init__(parent)
        self.app = parent

        self.setWindowTitle("Manage Profiles")
        self.setMinimumSize(580, 420)
        self.setModal(True)
        self.setStyleSheet(parent.styleSheet())

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Manage Profiles")
        font = QFont("Arial", 13)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        content = QHBoxLayout()

        self.profile_list = QListWidget()
        self.profile_list.setMinimumWidth(320)
        self.profile_list.itemSelectionChanged.connect(self._on_selection_change)
        self.profile_list.itemDoubleClicked.connect(self._load_and_close)
        content.addWidget(self.profile_list)

        btn_layout = QVBoxLayout()
        for label, slot in [
            ("Load", self._load_and_close),
            ("Rename", self._rename_profile),
            ("Duplicate", self._duplicate_profile),
            ("Delete", self._delete_profile),
        ]:
            btn = QPushButton(label)
            btn.setFixedWidth(110)
            btn.clicked.connect(slot)
            btn_layout.addWidget(btn)
        btn_layout.addStretch()
        content.addLayout(btn_layout)

        layout.addLayout(content)

        details_lbl = QLabel("Profile Details:")
        details_font = QFont("Arial", 11)
        details_font.setBold(True)
        details_lbl.setFont(details_font)
        layout.addWidget(details_lbl)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(110)
        layout.addWidget(self.details_text)

        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self._delete_profile()
        elif event.key() == Qt.Key.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)

    def _refresh_list(self):
        self.profile_list.clear()
        for name in self.app.profile_manager.get_profile_names():
            self.profile_list.addItem(name)

    def _selected_name(self) -> str | None:
        item = self.profile_list.currentItem()
        return item.text() if item else None

    def _on_selection_change(self):
        name = self._selected_name()
        if name:
            profile = self.app.profile_manager.get_profile(name)
            if profile:
                self._show_details(profile)
        else:
            self.details_text.clear()

    def _show_details(self, profile: dict):
        lines = []
        if profile.get('source_folder'):
            lines.append(f"Source: {profile['source_folder']}")
        if profile.get('dest_folder'):
            lines.append(f"Destination: {profile['dest_folder']}")
        if profile.get('extension'):
            lines.append(f"File Mask: {profile['extension']}")
        workers = profile.get('workers')
        if workers is not None:
            lines.append(f"Workers: {workers}")
        flags = []
        if profile.get('recursive_search'):
            flags.append("recursive")
        if profile.get('incremental'):
            flags.append("incremental")
        if profile.get('verify_checksum'):
            flags.append("verify checksum")
        if flags:
            lines.append(f"Options: {', '.join(flags)}")
        self.details_text.setText('\n'.join(lines))

    def _load_and_close(self):
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "No Selection", "Please select a profile to load.")
            return
        profile = self.app.profile_manager.get_profile(name)
        if profile:
            self.app._apply_settings(profile)
            self.app._refresh_profile_list(select=name)
            self.app._add_status(f"Profile '{name}' loaded.")
            self.accept()

    def _rename_profile(self):
        old_name = self._selected_name()
        if not old_name:
            QMessageBox.warning(self, "No Selection", "Please select a profile to rename.")
            return
        new_name, ok = QInputDialog.getText(self, "Rename Profile", "New name:", text=old_name)
        if not (ok and new_name and new_name.strip() and new_name.strip() != old_name):
            return
        new_name = new_name.strip()
        if self.app.profile_manager.profile_exists(new_name):
            QMessageBox.critical(self, "Name Exists", f"A profile named '{new_name}' already exists.")
            return
        if self.app.profile_manager.rename_profile(old_name, new_name):
            self._refresh_list()
            self.app._refresh_profile_list(select=new_name)
            items = self.profile_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.profile_list.setCurrentItem(items[0])
            self.app._add_status(f"Profile renamed to '{new_name}'.")
        else:
            QMessageBox.critical(self, "Rename Failed", "Failed to rename profile.")

    def _duplicate_profile(self):
        source_name = self._selected_name()
        if not source_name:
            QMessageBox.warning(self, "No Selection", "Please select a profile to duplicate.")
            return
        new_name, ok = QInputDialog.getText(
            self, "Duplicate Profile", "Name for the copy:", text=f"{source_name} (Copy)"
        )
        if not (ok and new_name and new_name.strip()):
            return
        new_name = new_name.strip()
        if self.app.profile_manager.profile_exists(new_name):
            QMessageBox.critical(self, "Name Exists", f"A profile named '{new_name}' already exists.")
            return
        if self.app.profile_manager.duplicate_profile(source_name, new_name):
            self._refresh_list()
            self.app._refresh_profile_list()
            items = self.profile_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
            if items:
                self.profile_list.setCurrentItem(items[0])
            self.app._add_status(f"Profile '{source_name}' duplicated as '{new_name}'.")
        else:
            QMessageBox.critical(self, "Duplicate Failed", "Failed to duplicate profile.")

    def _delete_profile(self):
        name = self._selected_name()
        if not name:
            QMessageBox.warning(self, "No Selection", "Please select a profile to delete.")
            return
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to delete the profile '{name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            if self.app.profile_manager.delete_profile(name):
                self._refresh_list()
                self.app._refresh_profile_list()
                self.details_text.clear()
                self.app._add_status(f"Profile '{name}' deleted.")
            else:
                QMessageBox.critical(self, "Delete Failed", "Failed to delete profile.")
