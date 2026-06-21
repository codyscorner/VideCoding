"""Preview dialog — shows files that would be copied before execution"""

import os

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
)
from PyQt6.QtCore import Qt

from ui.styles import STYLESHEET


class PreviewDialog(QDialog):
    """Shows the list of files that would be copied and lets the user confirm."""

    def __init__(self, files: list, parent=None):
        """
        Args:
            files: list of (full_path, rel_path, size_bytes) tuples from FileScanner
        """
        super().__init__(parent)
        self.setWindowTitle("Preview — Files to Copy")
        self.setMinimumSize(750, 450)
        self.resize(950, 560)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)

        title = QLabel(f"Files that will be copied  ({len(files)} total)")
        title.setObjectName("section_label")
        layout.addWidget(title)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Filename", "Size", "Full Source Path"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.setSortingEnabled(True)

        total_bytes = 0
        self.table.setRowCount(len(files))
        for row, (full_path, _rel_path, size) in enumerate(files):
            name_item = QTableWidgetItem(os.path.basename(full_path))
            size_item = QTableWidgetItem(self._fmt_size(size))
            size_item.setData(Qt.ItemDataRole.UserRole, size)  # for correct numeric sort
            path_item = QTableWidgetItem(full_path)
            self.table.setItem(row, 0, name_item)
            self.table.setItem(row, 1, size_item)
            self.table.setItem(row, 2, path_item)
            total_bytes += size

        layout.addWidget(self.table)

        # Summary
        summary = QLabel(f"Total: {len(files)} file{'s' if len(files) != 1 else ''}  ·  {self._fmt_size(total_bytes)}")
        summary.setObjectName("dim_label")
        layout.addWidget(summary)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.clicked.connect(self.reject)
        proceed_btn = QPushButton("Proceed to Copy")
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
