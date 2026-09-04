from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QPlainTextEdit, QPushButton, QLineEdit, QComboBox, QSpinBox,
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt

from config import ConfigManager
from llm_worker import PromptWorker, ModelListWorker
from providers import PROVIDERS
from worker import PROMPT_SEPARATOR, parse_prompts
from ui.styles import COLORS

SCENE_SYSTEM_PROMPT_TMPL = """You write style-transfer prompts for an image-to-image AI pipeline that batch-restyles photos.
{scenario_block}
The user will give you one scene or theme idea. Generate exactly {n} DISTINCT variations on that idea — vary the angle, lighting, palette, era-specific detail, or mood between them so a batch of photos run through them looks varied, not repetitive.

Output format is strict: each variation is its own block, starting with the exact line:
{separator}
followed immediately by the prompt text. Do not number them, do not add headers or explanations, do not add any text before the first block or after the last one. Output ONLY the {n} blocks, nothing else."""

SCENARIO_BLOCK_TMPL = """
Every prompt must keep this fixed shot/subject description exactly as given, word for word:
"{scenario}"
Wherever it contains a placeholder like <Add scene description> (or similar bracketed text), replace ONLY that placeholder with a vivid, specific scene/setting description built from the user's idea below — vary that scene description across all {n} variations while keeping the rest of the fixed description unchanged. If it has no such placeholder, append the scene description naturally after it instead.
"""

NO_SCENARIO_BLOCK = """
Each prompt is a short, comma-separated list of descriptive phrases (NOT full sentences) covering style/medium, lighting, mood, palette, and setting details. Do not include camera-move or narrative language — these style a single still image, not a video.
"""


class PromptEditorDialog(QDialog):
    def __init__(self, prompts_file: Path, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._file = prompts_file
        self._config = config
        self._worker: PromptWorker | None = None
        self._model_worker: ModelListWorker | None = None
        self.setWindowTitle(f"Edit Prompts — {prompts_file.name}")
        self.setMinimumSize(700, 640)
        self._build_ui()
        self._load()
        self._scenario_edit.setText(config.get("scene_gen_scenario", ""))
        self._on_provider_changed()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # ── AI scene generator ──────────────────────────────────────────
        gen_group = QGroupBox("Generate Scenes with AI")
        gen_v = QVBoxLayout(gen_group)
        gen_v.setSpacing(6)

        scenario_row = QHBoxLayout()
        scenario_lbl = QLabel("Scenario:")
        scenario_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._scenario_edit = QLineEdit()
        self._scenario_edit.setPlaceholderText(
            'Optional fixed shot/subject description, e.g. "Close-up, upper body in frame. '
            'A couple set in <scene description>."'
        )
        self._scenario_edit.setToolTip(
            "Kept word-for-word across every generated prompt — only the <scene description>\n"
            "placeholder (or text following it) varies per generation. Leave blank to let the\n"
            "AI write the whole prompt freely from the Idea below."
        )
        scenario_row.addWidget(scenario_lbl)
        scenario_row.addWidget(self._scenario_edit, stretch=1)
        gen_v.addLayout(scenario_row)

        idea_row = QHBoxLayout()
        idea_lbl = QLabel("Idea:")
        idea_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._idea_edit = QLineEdit()
        self._idea_edit.setPlaceholderText(
            "e.g. 1970s rock concert backstage, moody film grain..."
        )
        idea_row.addWidget(idea_lbl)
        idea_row.addWidget(self._idea_edit, stretch=1)
        gen_v.addLayout(idea_row)

        provider_row = QHBoxLayout()
        provider_lbl = QLabel("Provider:")
        provider_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._provider_combo = QComboBox()
        for provider_id, info in PROVIDERS.items():
            self._provider_combo.addItem(info["label"], provider_id)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._model_combo = QComboBox()
        self._model_combo.setEditable(True)
        self._model_combo.setMinimumWidth(220)

        self._refresh_models_btn = QPushButton("⟳")
        self._refresh_models_btn.setObjectName("small_btn")
        self._refresh_models_btn.setFixedSize(30, 26)
        self._refresh_models_btn.setToolTip("Fetch the live model list from this provider's API")
        self._refresh_models_btn.clicked.connect(self._on_refresh_models)

        count_lbl = QLabel("Count:")
        count_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._count_spin = QSpinBox()
        self._count_spin.setRange(1, 30)
        self._count_spin.setValue(6)
        self._count_spin.setFixedWidth(56)

        provider_row.addWidget(provider_lbl)
        provider_row.addWidget(self._provider_combo)
        provider_row.addSpacing(12)
        provider_row.addWidget(model_lbl)
        provider_row.addWidget(self._model_combo, stretch=1)
        provider_row.addWidget(self._refresh_models_btn)
        provider_row.addSpacing(12)
        provider_row.addWidget(count_lbl)
        provider_row.addWidget(self._count_spin)
        gen_v.addLayout(provider_row)

        gen_btn_row = QHBoxLayout()
        self._gen_btn = QPushButton("✨  Generate")
        self._gen_btn.setObjectName("small_btn")
        self._gen_btn.clicked.connect(self._on_generate)
        gen_btn_row.addWidget(self._gen_btn)
        self._gen_status_lbl = QLabel("")
        self._gen_status_lbl.setObjectName("subtitle")
        gen_btn_row.addWidget(self._gen_status_lbl, stretch=1)
        gen_v.addLayout(gen_btn_row)

        layout.addWidget(gen_group)

        hint = QLabel(
            f'Separate prompts with:  <b>{PROMPT_SEPARATOR}</b>  on its own line.  '
            f'Each prompt can span multiple lines.  '
            f'Add a weight to bias random selection: <b>---- PROMPT START x3 -----</b> '
            f'(3x more likely to be picked than a weight-1 prompt).'
        )
        hint.setObjectName("subtitle")
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._editor = QPlainTextEdit()
        self._editor.setTabChangesFocus(False)
        layout.addWidget(self._editor, stretch=1)

        self._editor.textChanged.connect(self._update_count)

        bottom = QHBoxLayout()
        self._count_lbl = QLabel("0 prompts")
        self._count_lbl.setObjectName("subtitle")
        bottom.addWidget(self._count_lbl)
        bottom.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setMinimumWidth(90)
        cancel_btn.clicked.connect(self.reject)

        save_btn = QPushButton("Save")
        save_btn.setMinimumWidth(90)
        save_btn.clicked.connect(self._save)

        bottom.addWidget(cancel_btn)
        bottom.addWidget(save_btn)
        layout.addLayout(bottom)

    def _load(self):
        try:
            text = self._file.read_text(encoding="utf-8")
        except OSError:
            text = f"{PROMPT_SEPARATOR}\n"
        self._editor.setPlainText(text)

    def _update_count(self):
        n = len(parse_prompts(self._editor.toPlainText()))
        self._count_lbl.setText(f"{n} prompt{'s' if n != 1 else ''} detected")

    def _save(self):
        try:
            self._file.write_text(self._editor.toPlainText(), encoding="utf-8")
            self.accept()
        except OSError as exc:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", str(exc))

    # ------------------------------------------------------------------ #
    # AI scene generation
    # ------------------------------------------------------------------ #

    def _current_provider_id(self) -> str:
        return self._provider_combo.currentData()

    def _current_model(self) -> str:
        text = self._model_combo.currentText().strip()
        idx = self._model_combo.findText(text)
        if idx >= 0:
            return self._model_combo.itemData(idx)
        return text  # user typed a custom model id not in the curated list

    def _on_provider_changed(self):
        provider_id = self._current_provider_id()
        self._config.set("scene_gen_provider", provider_id)

        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for model_id, label in PROVIDERS[provider_id]["models"]:
            self._model_combo.addItem(label, model_id)
        last_model = self._config.get("scene_gen_last_model", {}).get(provider_id)
        if last_model:
            idx = self._model_combo.findData(last_model)
            if idx >= 0:
                self._model_combo.setCurrentIndex(idx)
            else:
                self._model_combo.setCurrentText(last_model)
        self._model_combo.blockSignals(False)

        self._refresh_key_state()

    def _refresh_key_state(self):
        provider_id = self._current_provider_id()
        has_key = bool(self._config.get(PROVIDERS[provider_id]["key_config"], "").strip())
        busy = self._worker is not None and self._worker.isRunning()
        models_busy = self._model_worker is not None and self._model_worker.isRunning()
        self._gen_btn.setEnabled(has_key and not busy)
        # OpenRouter's model list is public and works without a key.
        self._refresh_models_btn.setEnabled((has_key or provider_id == "openrouter") and not models_busy)
        if not has_key:
            label = PROVIDERS[provider_id]["label"]
            self._gen_status_lbl.setText(f"Set your {label} API key in Settings to use this provider.")
        elif not busy:
            self._gen_status_lbl.setText("")

    def _on_refresh_models(self):
        provider_id = self._current_provider_id()
        api_key = self._config.get(PROVIDERS[provider_id]["key_config"], "").strip()

        self._refresh_models_btn.setEnabled(False)
        self._gen_status_lbl.setText("Fetching model list...")

        self._model_worker = ModelListWorker(provider_id, api_key)
        self._model_worker.result_ready.connect(lambda models: self._on_models_fetched(provider_id, models))
        self._model_worker.error.connect(self._on_gen_error)
        self._model_worker.finished.connect(self._refresh_key_state)
        self._model_worker.start()

    def _on_models_fetched(self, provider_id: str, models: list):
        if provider_id != self._current_provider_id():
            return  # user switched providers while the request was in flight
        current = self._current_model()
        self._model_combo.blockSignals(True)
        self._model_combo.clear()
        for model_id, label in models:
            self._model_combo.addItem(label, model_id)
        idx = self._model_combo.findData(current)
        if idx >= 0:
            self._model_combo.setCurrentIndex(idx)
        else:
            self._model_combo.setEditText(current)
        self._model_combo.blockSignals(False)
        self._gen_status_lbl.setText(f"Loaded {len(models)} model(s) from {PROVIDERS[provider_id]['label']}.")

    def _on_generate(self):
        idea = self._idea_edit.text().strip()
        if not idea:
            self._gen_status_lbl.setText("Enter a scene idea first.")
            return

        provider_id = self._current_provider_id()
        api_key = self._config.get(PROVIDERS[provider_id]["key_config"], "").strip()
        if not api_key:
            self._refresh_key_state()
            return

        model = self._current_model()
        if not model:
            self._gen_status_lbl.setText("Enter or pick a model.")
            return

        scenario = self._scenario_edit.text().strip()

        last_model = self._config.get("scene_gen_last_model", {})
        last_model[provider_id] = model
        self._config.set("scene_gen_last_model", last_model)
        self._config.set("scene_gen_scenario", scenario)
        self._config.save()

        n = self._count_spin.value()
        scenario_block = (
            SCENARIO_BLOCK_TMPL.format(scenario=scenario, n=n) if scenario else NO_SCENARIO_BLOCK
        )
        system_prompt = SCENE_SYSTEM_PROMPT_TMPL.format(
            n=n, separator=PROMPT_SEPARATOR, scenario_block=scenario_block,
        )

        self._gen_btn.setEnabled(False)
        self._gen_status_lbl.setText("Generating...")

        self._worker = PromptWorker(provider_id, model, api_key, system_prompt, idea)
        self._worker.result_ready.connect(self._on_generate_result)
        self._worker.error.connect(self._on_gen_error)
        self._worker.finished.connect(self._refresh_key_state)
        self._worker.start()

    def _on_generate_result(self, text: str):
        entries = parse_prompts(text)
        if not entries:
            self._gen_status_lbl.setText("Could not parse any prompts from the response — try again.")
            return

        blocks = "\n\n".join(f"{PROMPT_SEPARATOR}\n{e.text}" for e in entries)
        cursor = self._editor.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self._editor.setTextCursor(cursor)
        prefix = "\n\n" if self._editor.toPlainText().strip() else ""
        self._editor.insertPlainText(f"{prefix}{blocks}\n")

        self._gen_status_lbl.setText(f"Added {len(entries)} generated prompt(s).")

    def _on_gen_error(self, message: str):
        self._gen_status_lbl.setText(message)
