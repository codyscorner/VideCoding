"""Preview dialog — shows files that would be copied/moved before execution"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from ui.styles import STYLESHEET
from folder_organization import FolderOrganizer, FolderStructure


class _NumericItem(QTableWidgetItem):
    """QTableWidgetItem that sorts by its UserRole numeric value instead of display text."""
    def __lt__(self, other):
        return (self.data(Qt.ItemDataRole.UserRole) or 0) < (other.data(Qt.ItemDataRole.UserRole) or 0)


class PreviewDialog(QDialog):
    """Shows the list of files that would be copied/moved and lets the user confirm."""

    def __init__(self, files: list, options: dict, parent=None):
        """
        Args:
            files:   list of (full_path, rel_path, size_bytes) tuples from FileScanner
            options: the same options dict passed to FileCopier (dest_folder, preserve_structure, etc.)
        """
        super().__init__(parent)
        mode = options.get('operation_mode', 'copy')
        verb = "Move" if mode == 'move' else "Copy"
        self.setWindowTitle(f"Preview — Files to {verb}")
        self.setMinimumSize(1000, 450)
        self.resize(1400, 580)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(f"Files that will be {verb.lower()}d  ({len(files)} total)")
        title.setObjectName("section_label")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Filename", "Size", "Source Path", "Destination Path"])
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        hdr.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)

        organizer = FolderOrganizer()
        dest_folder = options.get('dest_folder', '')
        source_folder = options.get('source_folder', '')
        preserve = options.get('preserve_structure', True)
        try:
            folder_structure = FolderStructure(options.get('folder_structure', 'flat'))
        except ValueError:
            folder_structure = FolderStructure.FLAT
        structure = FolderStructure.PRESERVE if preserve else folder_structure

        total_bytes = 0
        self.table.setRowCount(len(files))
        for row, (full_path, rel_path, size) in enumerate(files):
            filename = os.path.basename(full_path)

            # Compute destination folder (mirrors FileCopier logic, no duplicate resolution)
            if structure == FolderStructure.PRESERVE:
                rel_dir = os.path.dirname(rel_path)
                final_dest = os.path.join(dest_folder, rel_dir) if rel_dir else dest_folder
            else:
                subfolder = organizer.get_destination_subfolder(
                    full_path, structure, source_folder, use_file_date=True
                )
                final_dest = os.path.join(dest_folder, subfolder) if subfolder else dest_folder
            dest_path = os.path.join(final_dest, filename)

            name_item = QTableWidgetItem(filename)
            size_item = _NumericItem(self._fmt_size(size))
            size_item.setData(Qt.ItemDataRole.UserRole, size)
            src_item  = QTableWidgetItem(full_path)
            dst_item  = QTableWidgetItem(dest_path)
            src_item.setToolTip(full_path)
            dst_item.setToolTip(dest_path)

            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, size_item)
            self.table.setItem(row, 2, src_item)
            self.table.setItem(row, 3, dst_item)
            total_bytes += size

        layout.addWidget(self.table)

        summary = QLabel(f"Total: {len(files)} file{'s' if len(files) != 1 else ''}  ·  {self._fmt_size(total_bytes)}")
        summary.setObjectName("dim_label")
        layout.addWidget(summary)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        proceed_btn = QPushButton(f"Proceed to {verb}")
        proceed_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addSpacing(10)
        btn_row.addWidget(proceed_btn)
        layout.addLayout(btn_row)

    @staticmethod
    def _fmt_size(size_bytes: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} PB"
