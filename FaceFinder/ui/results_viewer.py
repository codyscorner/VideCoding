"""Results viewer dialog with thumbnail grid for FaceFinder"""

import csv
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import List

from PyQt6.QtWidgets import (
    QDialog, QWidget, QLabel, QPushButton,
    QScrollArea, QGridLayout, QVBoxLayout, QHBoxLayout, QSizePolicy,
    QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon
from PyQt6.QtWidgets import QApplication

from ui.styles import COLORS, STYLESHEET

THUMBNAIL_SIZE = 150


class ThumbnailWidget(QWidget):
    selection_changed = pyqtSignal()

    def __init__(self, path: str, parent=None):
        super().__init__(parent)
        self.path = path
        self.selected = False
        self.setFixedSize(THUMBNAIL_SIZE + 20, THUMBNAIL_SIZE + 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(3)

        img_label = QLabel()
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        img_label.setFixedSize(THUMBNAIL_SIZE, THUMBNAIL_SIZE)

        pixmap = QPixmap(path)
        if not pixmap.isNull():
            img_label.setPixmap(pixmap.scaled(
                THUMBNAIL_SIZE, THUMBNAIL_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            ))
        else:
            img_label.setText("[Error]")
            img_label.setStyleSheet(f"color: {COLORS['error']}; background: {COLORS['bg_light']};")

        layout.addWidget(img_label)

        filename = Path(path).name
        if len(filename) > 22:
            filename = filename[:19] + "..."
        name_label = QLabel(filename)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 8pt;")
        name_label.setWordWrap(True)
        layout.addWidget(name_label)

        self._apply_style()

    def _apply_style(self):
        if self.selected:
            self.setStyleSheet(
                f"background-color: {COLORS['thumb_hover']}; border-radius: 4px; "
                f"border: 2px solid {COLORS['accent']};"
            )
        else:
            self.setStyleSheet(f"background-color: {COLORS['bg_medium']}; border-radius: 4px;")

    def set_selected(self, selected: bool):
        self.selected = selected
        self._apply_style()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.set_selected(not self.selected)
            self.selection_changed.emit()
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        if Path(self.path).exists():
            subprocess.Popen(['explorer', '/select,', self.path])

    def enterEvent(self, event):
        if not self.selected:
            self.setStyleSheet(f"background-color: {COLORS['thumb_hover']}; border-radius: 4px; border: 1px solid {COLORS['accent']};")

    def leaveEvent(self, event):
        self._apply_style()


class ResultsViewer(QDialog):
    def __init__(self, parent, matches: List[str]):
        super().__init__(parent)
        self._matches = list(matches)
        self._thumbs: List[ThumbnailWidget] = []
        self.setWindowTitle(f"Match Results — {len(matches)} images found")
        self.setMinimumSize(800, 600)
        self.setStyleSheet(STYLESHEET)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 12)

        self._header = QLabel(f"Found {len(matches)} matching images")
        self._header.setObjectName("header")
        layout.addWidget(self._header)

        hint = QLabel("Click to select  •  Double-click to open location in Explorer")
        hint.setObjectName("subtitle")
        layout.addWidget(hint)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(scroll.Shape.NoFrame)

        grid_widget = QWidget()
        self.grid = QGridLayout(grid_widget)
        self.grid.setSpacing(8)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet(f"color: {COLORS['accent']}; font-size: 9pt;")

        self._cols = max(1, 760 // (THUMBNAIL_SIZE + 30))
        self._rebuild_grid()

        scroll.setWidget(grid_widget)
        layout.addWidget(scroll, stretch=1)

        layout.addWidget(self._status_label)

        btn_row = QHBoxLayout()

        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self._select_all)
        btn_row.addWidget(select_all_btn)

        clear_sel_btn = QPushButton("Clear Selection")
        clear_sel_btn.setObjectName("secondary_btn")
        clear_sel_btn.clicked.connect(self._clear_selection)
        btn_row.addWidget(clear_sel_btn)

        btn_row.addStretch()

        has_matches = bool(self._matches)

        self._copy_folder_btn = QPushButton("Copy to Folder...")
        self._copy_folder_btn.setEnabled(has_matches)
        self._copy_folder_btn.clicked.connect(lambda: self._copy_or_move_to_folder(move=False))
        btn_row.addWidget(self._copy_folder_btn)

        self._move_folder_btn = QPushButton("Move to Folder...")
        self._move_folder_btn.setEnabled(has_matches)
        self._move_folder_btn.clicked.connect(lambda: self._copy_or_move_to_folder(move=True))
        btn_row.addWidget(self._move_folder_btn)

        export_btn = QPushButton("Export CSV")
        export_btn.setEnabled(has_matches)
        export_btn.clicked.connect(self._export_csv)
        btn_row.addWidget(export_btn)

        copy_btn = QPushButton("Copy All Paths")
        copy_btn.setEnabled(has_matches)
        copy_btn.clicked.connect(self._copy_paths)
        btn_row.addWidget(copy_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    # ------------------------------------------------------------------ #
    # Grid / selection
    # ------------------------------------------------------------------ #

    def _rebuild_grid(self):
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._thumbs = []
        for i, path in enumerate(self._matches):
            row, col = divmod(i, self._cols)
            thumb = ThumbnailWidget(path)
            thumb.selection_changed.connect(self._update_status)
            self.grid.addWidget(thumb, row, col)
            self._thumbs.append(thumb)
        self._update_status()

    def _selected_paths(self) -> List[str]:
        return [t.path for t in self._thumbs if t.selected]

    def _select_all(self):
        for t in self._thumbs:
            t.set_selected(True)
        self._update_status()

    def _clear_selection(self):
        for t in self._thumbs:
            t.set_selected(False)
        self._update_status()

    def _update_status(self):
        n = len(self._selected_paths())
        if n:
            self._status_label.setText(f"{n} selected")
        else:
            self._status_label.setText("")

    # ------------------------------------------------------------------ #
    # Copy / move to folder
    # ------------------------------------------------------------------ #

    def _unique_dest(self, dest_dir: Path, name: str) -> Path:
        dest = dest_dir / name
        if not dest.exists():
            return dest
        stem, suffix = Path(name).stem, Path(name).suffix
        i = 1
        while True:
            candidate = dest_dir / f"{stem} ({i}){suffix}"
            if not candidate.exists():
                return candidate
            i += 1

    def _copy_or_move_to_folder(self, move: bool):
        targets = self._selected_paths() or list(self._matches)
        if not targets:
            return
        dest_dir = QFileDialog.getExistingDirectory(self, "Select Destination Folder")
        if not dest_dir:
            return
        dest_dir = Path(dest_dir)

        verb = "Move" if move else "Copy"
        reply = QMessageBox.question(
            self, f"{verb} to Folder",
            f"{verb} {len(targets)} image{'s' if len(targets) != 1 else ''} to:\n{dest_dir}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        moved = []
        errors = []
        for src in targets:
            src_path = Path(src)
            if not src_path.exists():
                errors.append(f"{src_path.name}: not found")
                continue
            try:
                dest = self._unique_dest(dest_dir, src_path.name)
                if move:
                    shutil.move(str(src_path), str(dest))
                    moved.append(src)
                else:
                    shutil.copy2(str(src_path), str(dest))
            except OSError as e:
                errors.append(f"{src_path.name}: {e}")

        if move and moved:
            moved_set = set(moved)
            self._matches = [m for m in self._matches if m not in moved_set]
            self._rebuild_grid()
            self._header.setText(f"Found {len(self._matches)} matching images")
            has_matches = bool(self._matches)
            self._copy_folder_btn.setEnabled(has_matches)
            self._move_folder_btn.setEnabled(has_matches)

        n_done = len(moved) if move else (len(targets) - len(errors))
        self._status_label.setText(f"{verb}d {n_done} image{'s' if n_done != 1 else ''} to {dest_dir.name}")
        if errors:
            QMessageBox.warning(self, f"{verb} Errors", "\n".join(errors))

    def _export_csv(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Export Results", "facefinder_results.csv",
            "CSV Files (*.csv)"
        )
        if not path:
            return
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["File Name", "Full Path", "File Size (bytes)", "Modified Date"])
            for match in self._matches:
                p = Path(match)
                try:
                    stat = p.stat()
                    size = stat.st_size
                    modified = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                except OSError:
                    size = ""
                    modified = ""
                writer.writerow([p.name, str(p), size, modified])
        self._status_label.setText(f"Exported {len(self._matches)} rows to {Path(path).name}")

    def _copy_paths(self):
        text = "\n".join(self._matches)
        QApplication.clipboard().setText(text)
        count = len(self._matches)
        self._status_label.setText(f"Copied {count} path{'s' if count != 1 else ''} to clipboard")
