"""Dry-run preview dialog for Bulk File Randomizer"""

from pathlib import Path
from typing import List, Tuple

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QVBoxLayout,
)

_MAX_ROWS = 500


class PreviewDialog(QDialog):
    def __init__(self, pairs: List[Tuple[Path, str]], mode: str, seed: int, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Preview")
        self.resize(720, 520)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        verb = "moved" if mode == "move" else "copied"
        header = QLabel(
            f"{len(pairs)} file(s) will be {verb}.   Seed: {seed}"
        )
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)

        if len(pairs) > _MAX_ROWS:
            note = QLabel(f"Showing the first {_MAX_ROWS} of {len(pairs)} files.")
            note.setObjectName("dim_label")
            layout.addWidget(note)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Source File", "New Name"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().setVisible(False)

        shown = pairs[:_MAX_ROWS]
        table.setRowCount(len(shown))
        for row, (src, new_name) in enumerate(shown):
            table.setItem(row, 0, QTableWidgetItem(src.name))
            table.setItem(row, 1, QTableWidgetItem(new_name))
        layout.addWidget(table, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
