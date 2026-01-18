"""Save Template dialog for File Rename Mover application (PySide6 version)"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QMessageBox
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window_qt import MainWindowQt


class SaveTemplateDialogQt(QDialog):
    """Dialog for saving current settings as a template (PySide6 version)"""

    def __init__(self, parent, app: 'MainWindowQt'):
        """
        Initialize save template dialog

        Args:
            parent: Parent window
            app: Main application window instance
        """
        super().__init__(parent)
        self.app = app

        self.setWindowTitle("Save Template")
        self.setFixedSize(450, 180)
        self.setModal(True)

        # Apply same stylesheet as parent
        self.setStyleSheet(app.theme.get_stylesheet())

        self._setup_ui()

        # Focus the name entry
        self.name_entry.setFocus()

    def _setup_ui(self) -> None:
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Save Current Settings as Template")
        title_font = QFont("Arial", 12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Template name input
        layout.addWidget(QLabel("Template Name:"))
        self.name_entry = QLineEdit()
        self.name_entry.returnPressed.connect(self._save_template)
        layout.addWidget(self.name_entry)

        # Add stretch
        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_template)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        button_layout.addStretch()
        layout.addLayout(button_layout)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Escape:
            self.reject()
        else:
            super().keyPressEvent(event)

    @Slot()
    def _save_template(self) -> None:
        """Save the template and close dialog"""
        name = self.name_entry.text().strip()

        if not name:
            QMessageBox.warning(
                self,
                "Name Required",
                "Please enter a name for the template."
            )
            return

        # Check if template already exists
        if self.app.template_manager.template_exists(name):
            reply = QMessageBox.question(
                self,
                "Template Exists",
                f"A template named '{name}' already exists.\nDo you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return

        # Get current settings and save template
        settings = self.app._get_current_settings()
        if self.app.template_manager.save_template(name, settings):
            self.app._refresh_template_list()
            # Set the combo to the new template
            idx = self.app.template_combo.findText(name)
            if idx >= 0:
                self.app.template_combo.setCurrentIndex(idx)
            self.app.add_status(f"Template '{name}' saved successfully.")
            self.accept()
        else:
            QMessageBox.critical(
                self,
                "Save Failed",
                "Failed to save template. Please try again."
            )
