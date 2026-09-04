from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QLineEdit, QDialogButtonBox,
)
from PyQt6.QtCore import Qt

from config import ConfigManager
from providers import PROVIDERS
from ui.styles import COLORS


class SettingsDialog(QDialog):
    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(620)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        group = QGroupBox("API Keys")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(10)

        self._key_edits: dict[str, QLineEdit] = {}
        for provider_id, info in PROVIDERS.items():
            edit, _ = self._key_row(
                group_layout, info["label"] + ":",
                config.get(info["key_config"], ""),
                info["key_hint"], info["key_url"],
            )
            self._key_edits[provider_id] = edit

        layout.addWidget(group)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._save)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _key_row(self, parent_layout, label: str, value: str, hint: str, url: str):
        row = QHBoxLayout()
        lbl = QLabel(label)
        lbl.setFixedWidth(150)
        lbl.setStyleSheet(f"color: {COLORS['fg_primary']};")
        edit = QLineEdit(value)
        edit.setPlaceholderText(hint)
        edit.setEchoMode(QLineEdit.EchoMode.Password)
        row.addWidget(lbl)
        row.addWidget(edit, stretch=1)
        parent_layout.addLayout(row)

        hint_lbl = QLabel(f'<a href="{url}" style="color:{COLORS["accent_hover"]};">{hint}</a>')
        hint_lbl.setObjectName("subtitle")
        hint_lbl.setOpenExternalLinks(True)
        hint_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        hint_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        hint_row = QHBoxLayout()
        hint_row.addSpacing(150)
        hint_row.addWidget(hint_lbl)
        parent_layout.addLayout(hint_row)
        return edit, None

    def _save(self):
        for provider_id, edit in self._key_edits.items():
            self._config.set(PROVIDERS[provider_id]["key_config"], edit.text().strip())
        self._config.save()
        self.accept()
