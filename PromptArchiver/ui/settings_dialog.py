"""Settings dialog: archive location tab + static help tab."""

from PyQt6.QtWidgets import (
    QDialog, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QPlainTextEdit,
    QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

FOLDER_DIAGRAM = """Prompt_Archive/
├── text/
│   └── prompt_2026-01-01T10-00-00/
│       ├── prompt.txt
│       ├── negative_prompt.txt (optional)
│       ├── metadata.json
│       └── output files...
├── image/
└── video/"""

HELP_TEXT = """Adding Prompts
1. Click "+ New Prompt" (or Ctrl+N)
2. Enter your prompt text (required)
3. Select content type (text, image, or video)
4. Add tags, model info, and negative prompt (optional)
5. Attach output files via Select Files or drag & drop
6. Click "Save Prompt"

Browsing Prompts
• Use the sidebar to browse all saved prompts
• Filter by type or rating using the dropdowns
• Search by prompt content, title, or tags
• Click on any prompt to view its details

Viewing Content
• Output files appear as tabs below the prompt details
• Images, videos, and text files preview in-app
• Use the ⋮ menu to Edit, Clone, Change Type, or Delete

Exporting
1. Select prompts using checkboxes in the sidebar
2. Click "Export Selected" to create a ZIP backup
3. Choose the export location

Settings
• The default archive location is ~/Prompt_Archive
• All data is stored locally in organized folders"""


class SettingsDialog(QDialog):
    """Returns the chosen archive path via archive_path() after accept."""

    def __init__(self, archive_path: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.setMinimumSize(560, 480)
        self._original = archive_path

        layout = QVBoxLayout(self)
        tabs = QTabWidget()
        layout.addWidget(tabs, stretch=1)

        # --- Settings tab ---
        settings_tab = QWidget()
        s_layout = QVBoxLayout(settings_tab)

        heading = QLabel("Archive Location")
        heading.setObjectName("sectionLabel")
        s_layout.addWidget(heading)
        s_layout.addWidget(QLabel(
            "Choose where your prompts are stored. The app creates a "
            "\"Prompt_Archive\" folder with subfolders for each content type."))

        path_row = QHBoxLayout()
        self.path_edit = QLineEdit(archive_path)
        self.path_edit.setPlaceholderText("No archive folder selected…")
        path_row.addWidget(self.path_edit, stretch=1)
        browse = QPushButton("Browse…")
        browse.clicked.connect(self._browse)
        path_row.addWidget(browse)
        s_layout.addLayout(path_row)

        note = QLabel("Changing the archive path will not move existing prompts. "
                      "Move the folder manually if you want to relocate your data.")
        note.setObjectName("infoNote")
        note.setWordWrap(True)
        s_layout.addWidget(note)

        structure_label = QLabel("Folder Structure")
        structure_label.setObjectName("sectionLabel")
        s_layout.addWidget(structure_label)
        diagram = QPlainTextEdit(FOLDER_DIAGRAM)
        diagram.setObjectName("promptBox")
        diagram.setReadOnly(True)
        s_layout.addWidget(diagram, stretch=1)
        tabs.addTab(settings_tab, "Settings")

        # --- Help tab ---
        help_tab = QWidget()
        h_layout = QVBoxLayout(help_tab)
        help_box = QPlainTextEdit(HELP_TEXT)
        help_box.setReadOnly(True)
        h_layout.addWidget(help_box)
        tabs.addTab(help_tab, "Help")

        # --- actions ---
        action_row = QHBoxLayout()
        action_row.addStretch()
        cancel = QPushButton("Cancel")
        cancel.clicked.connect(self.reject)
        action_row.addWidget(cancel)
        save = QPushButton("Save Settings")
        save.setObjectName("primaryBtn")
        save.clicked.connect(self.accept)
        action_row.addWidget(save)
        layout.addLayout(action_row)

    def _browse(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Archive Location")
        if folder:
            # parity with v1.x: chosen dir gets a Prompt_Archive subfolder
            from pathlib import Path
            self.path_edit.setText(str(Path(folder) / "Prompt_Archive"))

    def archive_path(self) -> str:
        return self.path_edit.text().strip()

    def path_changed(self) -> bool:
        return self.archive_path() != self._original
