"""Save Profile dialog for File Copy Move Manager"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window import MainWindow


class SaveProfileDialog(QDialog):
    def __init__(self, parent: 'MainWindow'):
        super().__init__(parent)
        self.app = parent

        self.setWindowTitle("Save Profile")
        self.setFixedSize(420, 160)
        self.setModal(True)
        self.setStyleSheet(parent.styleSheet())

        self._setup_ui()
        self.name_edit.setFocus()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Save Current Settings as Profile")
        font = QFont("Arial", 11)
        font.setBold(True)
        title.setFont(font)
        layout.addWidget(title)

        layout.addWidget(QLabel("Profile Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.returnPressed.connect(self._save)
        layout.addWidget(self.name_edit)

        layout.addStretch()

        btn_row = QHBoxLayout()
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    def _save(self):
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "Name Required", "Please enter a name for the profile.")
            return

        if self.app.profile_manager.profile_exists(name):
            reply = QMessageBox.question(
                self, "Profile Exists",
                f"A profile named '{name}' already exists.\nDo you want to overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return

        settings = self.app._get_current_settings()
        if self.app.profile_manager.save_profile(name, settings):
            self.app._refresh_profile_list(select=name)
            self.app._add_status(f"Profile '{name}' saved.")
            self.accept()
        else:
            QMessageBox.critical(self, "Save Failed", "Failed to save profile. Please try again.")
