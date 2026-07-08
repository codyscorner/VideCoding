"""Dialog collecting export options: destination, structure, overwrite, .m3u."""

from __future__ import annotations

from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
)


class ExportDialog(QDialog):
    def __init__(self, playlist_name: str, track_count: int, start_dir: str = "", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Export “{playlist_name}”")
        self.setMinimumWidth(460)
        self._start_dir = start_dir
        self._build(playlist_name, track_count)

    def _build(self, playlist_name: str, track_count: int) -> None:
        layout = QVBoxLayout(self)

        layout.addWidget(QLabel(
            f"Copy {track_count} file(s) from “{playlist_name}” to a folder:"
        ))

        # Destination row
        dest_row = QHBoxLayout()
        self.dest_edit = QLineEdit()
        self.dest_edit.setPlaceholderText("Choose a destination folder (e.g. a USB drive)…")
        self.dest_edit.textChanged.connect(self._update_ok)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        dest_row.addWidget(self.dest_edit, 1)
        dest_row.addWidget(browse)
        layout.addLayout(dest_row)

        # Folder structure
        struct_box = QGroupBox("Folder structure")
        sv = QVBoxLayout(struct_box)
        self.flat_radio = QRadioButton("Flat — all files in one folder")
        self.preserve_radio = QRadioButton("Preserve original subfolders")
        self.flat_radio.setChecked(True)
        self._struct = QButtonGroup(self)
        self._struct.addButton(self.flat_radio)
        self._struct.addButton(self.preserve_radio)
        sv.addWidget(self.flat_radio)
        sv.addWidget(self.preserve_radio)
        layout.addWidget(struct_box)

        # If a file already exists
        exist_box = QGroupBox("If a file already exists")
        ev = QVBoxLayout(exist_box)
        self.skip_radio = QRadioButton("Skip it")
        self.overwrite_radio = QRadioButton("Overwrite it")
        self.skip_radio.setChecked(True)
        self._exist = QButtonGroup(self)
        self._exist.addButton(self.skip_radio)
        self._exist.addButton(self.overwrite_radio)
        ev.addWidget(self.skip_radio)
        ev.addWidget(self.overwrite_radio)
        layout.addWidget(exist_box)

        # .m3u option
        self.m3u_check = QCheckBox("Also write an .m3u playlist file in the folder")
        self.m3u_check.setChecked(True)
        layout.addWidget(self.m3u_check)

        self.buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setText("Export")
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        layout.addWidget(self.buttons)
        self._update_ok()

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Choose export destination", self.dest_edit.text() or self._start_dir
        )
        if folder:
            self.dest_edit.setText(folder)

    def _update_ok(self) -> None:
        self.buttons.button(QDialogButtonBox.StandardButton.Ok).setEnabled(
            bool(self.dest_edit.text().strip())
        )

    # option getters
    def destination(self) -> str:
        return self.dest_edit.text().strip()

    def preserve(self) -> bool:
        return self.preserve_radio.isChecked()

    def overwrite(self) -> bool:
        return self.overwrite_radio.isChecked()

    def write_m3u(self) -> bool:
        return self.m3u_check.isChecked()
