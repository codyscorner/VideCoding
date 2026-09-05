"""Manage Templates dialog for File Rename Mover application (PySide6 version)"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QListWidget, QTextEdit, QMessageBox,
    QInputDialog, QSizePolicy
)
from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QFont
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ui.main_window_qt import MainWindowQt


class ManageTemplatesDialogQt(QDialog):
    """Dialog for managing saved templates (PySide6 version)"""

    def __init__(self, parent, app: 'MainWindowQt'):
        """
        Initialize manage templates dialog

        Args:
            parent: Parent window
            app: Main application window instance
        """
        super().__init__(parent)
        self.app = app

        self.setWindowTitle("Manage Templates")
        self.setMinimumSize(600, 450)
        self.setModal(True)

        # Apply same stylesheet as parent
        self.setStyleSheet(app.theme.get_stylesheet())

        self._setup_ui()
        self._refresh_list()

    def _setup_ui(self) -> None:
        """Set up the dialog UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)

        # Title
        title_label = QLabel("Manage Templates")
        title_font = QFont("Arial", 14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # Content frame (list + buttons side by side)
        content_layout = QHBoxLayout()

        # Template list
        self.template_listbox = QListWidget()
        self.template_listbox.setMinimumWidth(350)
        self.template_listbox.itemSelectionChanged.connect(self._on_selection_change)
        self.template_listbox.itemDoubleClicked.connect(self._load_and_close)
        content_layout.addWidget(self.template_listbox)

        # Button frame
        button_layout = QVBoxLayout()

        # Action buttons
        buttons = [
            ("Load", self._load_and_close),
            ("Edit", self._edit_template),
            ("Rename", self._rename_template),
            ("Duplicate", self._duplicate_template),
            ("Delete", self._delete_template),
        ]

        for text, callback in buttons:
            btn = QPushButton(text)
            btn.setFixedWidth(120)
            btn.clicked.connect(callback)
            button_layout.addWidget(btn)

        button_layout.addStretch()
        content_layout.addLayout(button_layout)

        layout.addLayout(content_layout)

        # Template details
        details_label = QLabel("Template Details:")
        details_font = QFont("Arial", 12)
        details_font.setBold(True)
        details_label.setFont(details_font)
        layout.addWidget(details_label)

        self.details_text = QTextEdit()
        self.details_text.setReadOnly(True)
        self.details_text.setMaximumHeight(120)
        layout.addWidget(self.details_text)

        # Close button
        close_layout = QHBoxLayout()
        close_layout.addStretch()

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)

        layout.addLayout(close_layout)

    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete:
            self._delete_template()
        elif event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)

    def _refresh_list(self) -> None:
        """Refresh the template list"""
        self.template_listbox.clear()
        for name in self.app.template_manager.get_template_names():
            self.template_listbox.addItem(name)

    def _get_selected_name(self) -> str | None:
        """Get the currently selected template name"""
        current_item = self.template_listbox.currentItem()
        if current_item:
            return current_item.text()
        return None

    @Slot()
    def _on_selection_change(self) -> None:
        """Handle selection change in the listbox"""
        name = self._get_selected_name()
        if name:
            template = self.app.template_manager.get_template(name)
            if template:
                self._show_template_details(template)
        else:
            self._clear_details()

    def _show_template_details(self, template: dict) -> None:
        """Show template details in the details text widget"""
        # Format template details
        details = []
        if template.get('default_source_folder'):
            details.append(f"Source: {template['default_source_folder']}")
        if template.get('default_destination_folder'):
            details.append(f"Destination: {template['default_destination_folder']}")
        if template.get('last_extension'):
            details.append(f"Extension: {template['last_extension']}")
        if template.get('last_rename_to'):
            details.append(f"Base Name: {template['last_rename_to']}")
        if template.get('pattern_type'):
            details.append(f"Pattern: {template['pattern_type']}")
        if template.get('folder_structure'):
            details.append(f"Folder Structure: {template['folder_structure']}")
        if template.get('base_name_folder'):
            details.append("Base Name Folder: yes")

        self.details_text.setText('\n'.join(details))

    def _clear_details(self) -> None:
        """Clear the details text widget"""
        self.details_text.clear()

    @Slot()
    def _load_and_close(self) -> None:
        """Load selected template and close dialog"""
        name = self._get_selected_name()
        if not name:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a template to load."
            )
            return

        template = self.app.template_manager.get_template(name)
        if template:
            self.app._apply_settings(template)
            # Set the combo to the loaded template
            idx = self.app.template_combo.findText(name)
            if idx >= 0:
                self.app.template_combo.setCurrentIndex(idx)
            self.app._refresh_template_list()
            self.app.add_status(f"Template '{name}' loaded successfully.")
            self.accept()

    @Slot()
    def _edit_template(self) -> None:
        """Edit the selected template"""
        name = self._get_selected_name()
        if not name:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a template to edit."
            )
            return

        template = self.app.template_manager.get_template(name)
        if template:
            from ui.edit_template_dialog_qt import EditTemplateDialogQt
            dialog = EditTemplateDialogQt(self, self.app, name, template)
            if dialog.exec():
                # Refresh lists after successful edit
                self._refresh_list()
                self.app._refresh_template_list()
                # Update details display
                updated_template = self.app.template_manager.get_template(name)
                if updated_template:
                    self._show_template_details(updated_template)

    @Slot()
    def _rename_template(self) -> None:
        """Rename the selected template"""
        old_name = self._get_selected_name()
        if not old_name:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a template to rename."
            )
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Rename Template",
            "Enter new name:",
            text=old_name
        )

        if ok and new_name and new_name.strip() and new_name.strip() != old_name:
            new_name = new_name.strip()
            if self.app.template_manager.template_exists(new_name):
                QMessageBox.critical(
                    self,
                    "Name Exists",
                    f"A template named '{new_name}' already exists."
                )
                return

            if self.app.template_manager.rename_template(old_name, new_name):
                self._refresh_list()
                self.app._refresh_template_list()
                # Select the renamed item
                items = self.template_listbox.findItems(new_name, Qt.MatchExactly)
                if items:
                    self.template_listbox.setCurrentItem(items[0])
                self.app.add_status(f"Template renamed from '{old_name}' to '{new_name}'.")
            else:
                QMessageBox.critical(
                    self,
                    "Rename Failed",
                    "Failed to rename template."
                )

    @Slot()
    def _duplicate_template(self) -> None:
        """Duplicate the selected template"""
        source_name = self._get_selected_name()
        if not source_name:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a template to duplicate."
            )
            return

        new_name, ok = QInputDialog.getText(
            self,
            "Duplicate Template",
            "Enter name for the copy:",
            text=f"{source_name} (Copy)"
        )

        if ok and new_name and new_name.strip():
            new_name = new_name.strip()
            if self.app.template_manager.template_exists(new_name):
                QMessageBox.critical(
                    self,
                    "Name Exists",
                    f"A template named '{new_name}' already exists."
                )
                return

            if self.app.template_manager.duplicate_template(source_name, new_name):
                self._refresh_list()
                self.app._refresh_template_list()
                # Select the new item
                items = self.template_listbox.findItems(new_name, Qt.MatchExactly)
                if items:
                    self.template_listbox.setCurrentItem(items[0])
                self.app.add_status(f"Template '{source_name}' duplicated as '{new_name}'.")
            else:
                QMessageBox.critical(
                    self,
                    "Duplicate Failed",
                    "Failed to duplicate template."
                )

    @Slot()
    def _delete_template(self) -> None:
        """Delete the selected template"""
        name = self._get_selected_name()
        if not name:
            QMessageBox.warning(
                self,
                "No Selection",
                "Please select a template to delete."
            )
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete the template '{name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            if self.app.template_manager.delete_template(name):
                self._refresh_list()
                self.app._refresh_template_list()
                self._clear_details()
                # Clear selection in main window if this was the selected template
                if self.app.template_combo.currentText() == name:
                    self.app.template_combo.setCurrentIndex(-1)
                self.app.add_status(f"Template '{name}' deleted.")
            else:
                QMessageBox.critical(
                    self,
                    "Delete Failed",
                    "Failed to delete template."
                )
