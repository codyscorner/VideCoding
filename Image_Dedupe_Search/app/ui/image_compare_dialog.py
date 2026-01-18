"""Side-by-side image comparison dialog for duplicate review"""

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QSplitter, QFrame, QFileDialog, QMessageBox,
    QWidget, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, Slot, QSize
from PySide6.QtGui import QPixmap
from typing import Optional
from pathlib import Path
import os
import shutil

from app.core.similarity import DuplicateGroup
from app.core.image_utils import ImageUtils, ImageMetadata


class ImageCompareDialog(QDialog):
    """Side-by-side comparison dialog for duplicate review"""

    # Signals
    action_taken = Signal(str, str)  # action ("delete", "move", "keep"), path
    group_updated = Signal()  # Emitted when group is modified

    def __init__(
        self,
        group: DuplicateGroup,
        parent=None,
        theme=None
    ):
        """
        Initialize compare dialog

        Args:
            group: DuplicateGroup to compare
            parent: Parent widget
            theme: ThemeManager for styling
        """
        super().__init__(parent)
        self.group = group
        self.theme = theme
        self.current_index = 0  # Index in duplicates list

        self.setWindowTitle("Compare Images")
        self.setMinimumSize(900, 600)
        self.resize(1100, 700)

        self._setup_ui()
        self._show_comparison(0)

    def _setup_ui(self) -> None:
        """Build the UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Title
        self.title_label = QLabel()
        self.title_label.setProperty("cssClass", "title")
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)

        # Image comparison area with splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)

        # Left panel (representative)
        self.left_panel = self._create_image_panel("Representative (Keep)")
        splitter.addWidget(self.left_panel)

        # Right panel (duplicate)
        self.right_panel = self._create_image_panel("Duplicate")
        splitter.addWidget(self.right_panel)

        splitter.setSizes([500, 500])
        layout.addWidget(splitter, 1)

        # Similarity score
        self.similarity_label = QLabel()
        self.similarity_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.similarity_label)

        # Action buttons
        action_layout = QHBoxLayout()

        # Swap button
        self.swap_btn = QPushButton("Swap")
        self.swap_btn.setToolTip("Swap representative and duplicate")
        self.swap_btn.clicked.connect(self._swap_representative)
        action_layout.addWidget(self.swap_btn)

        # Delete duplicate button
        self.delete_btn = QPushButton("Delete Duplicate")
        self.delete_btn.setProperty("cssClass", "danger")
        self.delete_btn.clicked.connect(self._delete_duplicate)
        action_layout.addWidget(self.delete_btn)

        # Move duplicate button
        self.move_btn = QPushButton("Move Duplicate To...")
        self.move_btn.setProperty("cssClass", "warning")
        self.move_btn.clicked.connect(self._move_duplicate)
        action_layout.addWidget(self.move_btn)

        # Skip button
        self.skip_btn = QPushButton("Skip")
        self.skip_btn.clicked.connect(self._next_comparison)
        action_layout.addWidget(self.skip_btn)

        layout.addLayout(action_layout)

        # Navigation buttons
        nav_layout = QHBoxLayout()

        self.prev_btn = QPushButton("Previous")
        self.prev_btn.clicked.connect(self._prev_comparison)
        nav_layout.addWidget(self.prev_btn)

        nav_layout.addStretch()

        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.accept)
        nav_layout.addWidget(self.close_btn)

        nav_layout.addStretch()

        self.next_btn = QPushButton("Next")
        self.next_btn.clicked.connect(self._next_comparison)
        nav_layout.addWidget(self.next_btn)

        layout.addLayout(nav_layout)

    def _create_image_panel(self, title: str) -> QWidget:
        """
        Create an image panel with scrollable image and metadata

        Args:
            title: Panel title

        Returns:
            Panel widget
        """
        panel = QFrame()
        panel.setProperty("cssClass", "card")
        layout = QVBoxLayout(panel)

        # Title
        title_label = QLabel(title)
        title_label.setProperty("cssClass", "section-title")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label)

        # Scrollable image area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setAlignment(Qt.AlignmentFlag.AlignCenter)

        image_label = QLabel()
        image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        image_label.setSizePolicy(
            QSizePolicy.Policy.Ignored,
            QSizePolicy.Policy.Ignored
        )
        scroll.setWidget(image_label)

        layout.addWidget(scroll, 1)

        # Metadata labels
        path_label = QLabel()
        path_label.setWordWrap(True)
        path_label.setProperty("cssClass", "status")
        layout.addWidget(path_label)

        info_label = QLabel()
        info_label.setProperty("cssClass", "status")
        layout.addWidget(info_label)

        # Store references
        panel.image_label = image_label
        panel.path_label = path_label
        panel.info_label = info_label

        return panel

    def _show_comparison(self, index: int) -> None:
        """
        Show comparison at given index

        Args:
            index: Index in duplicates list
        """
        if not self.group.duplicates:
            self.title_label.setText("No duplicates to compare")
            return

        # Clamp index
        index = max(0, min(index, len(self.group.duplicates) - 1))
        self.current_index = index

        # Update title
        total = len(self.group.duplicates)
        self.title_label.setText(f"Comparison {index + 1} of {total}")

        # Update navigation buttons
        self.prev_btn.setEnabled(index > 0)
        self.next_btn.setEnabled(index < total - 1)

        # Show representative (left)
        self._load_image_panel(
            self.left_panel,
            self.group.representative
        )

        # Show duplicate (right)
        dup_path = self.group.duplicates[index]
        self._load_image_panel(
            self.right_panel,
            dup_path
        )

        # Show similarity score
        score = self.group.similarity_scores.get(dup_path, 0)
        score_text = f"Similarity: {score:.1%}"

        if score >= 0.98:
            css_class = "similarity-high"
        elif score >= 0.95:
            css_class = "similarity-medium"
        else:
            css_class = "similarity-low"

        self.similarity_label.setText(score_text)
        self.similarity_label.setProperty("cssClass", css_class)
        self.similarity_label.style().unpolish(self.similarity_label)
        self.similarity_label.style().polish(self.similarity_label)

    def _load_image_panel(self, panel: QWidget, path: str) -> None:
        """
        Load image and metadata into panel

        Args:
            panel: Panel widget
            path: Image path
        """
        # Load image
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            # Scale to fit while preserving aspect ratio
            scaled = pixmap.scaled(
                QSize(450, 400),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            panel.image_label.setPixmap(scaled)
        else:
            panel.image_label.setText("Failed to load image")

        # Show path
        panel.path_label.setText(path)

        # Show metadata
        meta = ImageUtils.get_image_metadata(path)
        if meta:
            size_str = ImageUtils.format_file_size(meta.file_size)
            info = f"{meta.width} x {meta.height} | {size_str} | {meta.format}"
            panel.info_label.setText(info)
        else:
            panel.info_label.setText("Unable to read metadata")

    @Slot()
    def _next_comparison(self) -> None:
        """Go to next comparison"""
        if self.current_index < len(self.group.duplicates) - 1:
            self._show_comparison(self.current_index + 1)

    @Slot()
    def _prev_comparison(self) -> None:
        """Go to previous comparison"""
        if self.current_index > 0:
            self._show_comparison(self.current_index - 1)

    @Slot()
    def _delete_duplicate(self) -> None:
        """Delete the current duplicate"""
        if not self.group.duplicates:
            return

        dup_path = self.group.duplicates[self.current_index]

        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete:\n{dup_path}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        # Delete file
        try:
            os.remove(dup_path)

            # Remove from group
            self.group.duplicates.pop(self.current_index)
            if dup_path in self.group.similarity_scores:
                del self.group.similarity_scores[dup_path]

            self.action_taken.emit("delete", dup_path)
            self.group_updated.emit()

            # Show next or close
            if self.group.duplicates:
                # Adjust index if needed
                if self.current_index >= len(self.group.duplicates):
                    self.current_index = len(self.group.duplicates) - 1
                self._show_comparison(self.current_index)
            else:
                QMessageBox.information(
                    self,
                    "Complete",
                    "All duplicates in this group have been processed."
                )
                self.accept()

        except OSError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to delete file:\n{e}"
            )

    @Slot()
    def _move_duplicate(self) -> None:
        """Move the current duplicate to a folder"""
        if not self.group.duplicates:
            return

        dup_path = self.group.duplicates[self.current_index]

        # Select destination folder
        dest_folder = QFileDialog.getExistingDirectory(
            self,
            "Select Destination Folder",
            str(Path(dup_path).parent)
        )

        if not dest_folder:
            return

        # Move file
        try:
            filename = Path(dup_path).name
            dest_path = os.path.join(dest_folder, filename)

            # Handle name collision
            if os.path.exists(dest_path):
                base, ext = os.path.splitext(filename)
                counter = 1
                while os.path.exists(dest_path):
                    dest_path = os.path.join(dest_folder, f"{base}_{counter}{ext}")
                    counter += 1

            shutil.move(dup_path, dest_path)

            # Remove from group
            self.group.duplicates.pop(self.current_index)
            if dup_path in self.group.similarity_scores:
                del self.group.similarity_scores[dup_path]

            self.action_taken.emit("move", dup_path)
            self.group_updated.emit()

            # Show next or close
            if self.group.duplicates:
                if self.current_index >= len(self.group.duplicates):
                    self.current_index = len(self.group.duplicates) - 1
                self._show_comparison(self.current_index)
            else:
                QMessageBox.information(
                    self,
                    "Complete",
                    "All duplicates in this group have been processed."
                )
                self.accept()

        except OSError as e:
            QMessageBox.critical(
                self,
                "Error",
                f"Failed to move file:\n{e}"
            )

    @Slot()
    def _swap_representative(self) -> None:
        """Swap the representative with the current duplicate"""
        if not self.group.duplicates:
            return

        dup_path = self.group.duplicates[self.current_index]
        old_rep = self.group.representative

        # Swap representative and duplicate
        self.group.representative = dup_path
        self.group.duplicates[self.current_index] = old_rep

        # Update similarity scores
        old_score = self.group.similarity_scores.get(dup_path, 0.95)
        if dup_path in self.group.similarity_scores:
            del self.group.similarity_scores[dup_path]
        self.group.similarity_scores[old_rep] = old_score

        self.group_updated.emit()

        # Refresh display
        self._show_comparison(self.current_index)

