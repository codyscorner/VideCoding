import sys
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QTextEdit, QLineEdit, QComboBox, QApplication,
)
from PyQt6.QtCore import pyqtSignal

from config import ConfigManager
from prompt_llm_worker import PromptWriterWorker
from ui.styles import COLORS


def _resources_dir() -> Path:
    if getattr(sys, 'frozen', False):
        return Path(sys._MEIPASS) / "resources"
    return Path(__file__).parent.parent / "resources"


RESOURCES_DIR = _resources_dir()

H3_MODES = ["T2VA", "I2VA", "FL2VA", "L2VA", "Ref2VA"]

WAN_SYSTEM_PROMPT = """You write video-generation prompts for WAN 2.2 (image-to-video and text-to-video).

WAN prompts are plain, natural-language descriptions — not a multi-field structure. Write one tight paragraph (2-5 sentences) covering, in this rough order:
1. Subject and appearance (who/what is in frame, key visual details).
2. Setting and lighting/style (environment, time of day, art style if relevant).
3. The action or motion that happens over the clip.
4. Camera movement (e.g. slow push in, static shot, pan left, handheld) — only if it adds something.

Keep it concise and concrete — avoid vague mood words, avoid multi-shot cuts unless asked, avoid dialogue/subtitle notation. Output ONLY the final prompt text, nothing else (no preamble, no explanation, no markdown headers)."""

H3_MODE_NOTES = {
    "T2VA": "Mode: T2VA — build the full audiovisual timeline from text alone, no reference image.",
    "I2VA": "Mode: I2VA — the video starts from a first-frame reference image (<Picture 1>) and develops forward from it. Include the required first-frame instruction line before the core fields.",
    "FL2VA": "Mode: FL2VA — a first-frame and last-frame reference image are both supplied. Describe the continuous path between them. Include the required alignment instruction line before the core fields.",
    "L2VA": "Mode: L2VA — only a last-frame reference image is supplied (<Picture 1> is the final frame). Infer a plausible opening and converge to it. Include the required alignment instruction line before the core fields.",
    "Ref2VA": "Mode: Ref2VA — full-reference mode using subject_definitions, summary, retention_analysis, detailed_description, overall_soundscape, non_diegetic_music in that order, per the Ref2VA guide.",
}


def _load_h3_guide(mode: str) -> str:
    fname = "h3_ref_guide.txt" if mode == "Ref2VA" else "h3_base_guide.txt"
    path = RESOURCES_DIR / fname
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


class PromptWriterTab(QWidget):
    send_to_generate = pyqtSignal(str)  # user clicked "Send to Generate tab"

    def __init__(self, config: ConfigManager, parent=None):
        super().__init__(parent)
        self._config = config
        self._worker: PromptWriterWorker | None = None
        self._build_ui()
        self._on_model_changed()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 4, 0, 0)
        root.setSpacing(10)

        # ── Target model ──────────────────────────────────────────────────
        model_group = QGroupBox("Target Model")
        model_layout = QHBoxLayout(model_group)
        model_lbl = QLabel("Model:")
        model_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._model_combo = QComboBox()
        self._model_combo.addItems(["WAN 2.2", "MiniMax H3"])
        self._model_combo.setFixedHeight(30)
        self._model_combo.currentIndexChanged.connect(self._on_model_changed)

        self._mode_lbl = QLabel("H3 Mode:")
        self._mode_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._mode_combo = QComboBox()
        self._mode_combo.addItems(H3_MODES)
        self._mode_combo.setFixedHeight(30)

        model_layout.addWidget(model_lbl)
        model_layout.addWidget(self._model_combo)
        model_layout.addSpacing(16)
        model_layout.addWidget(self._mode_lbl)
        model_layout.addWidget(self._mode_combo)
        model_layout.addStretch()
        root.addWidget(model_group)

        # ── Idea input ────────────────────────────────────────────────────
        idea_group = QGroupBox("Rough Idea")
        idea_layout = QVBoxLayout(idea_group)
        idea_layout.setSpacing(6)
        self._idea_edit = QTextEdit()
        self._idea_edit.setPlaceholderText(
            "Describe what you want in plain language — subject, setting, action, mood..."
        )
        self._idea_edit.setFixedHeight(110)
        idea_layout.addWidget(self._idea_edit)

        notes_row = QHBoxLayout()
        notes_lbl = QLabel("Notes:")
        notes_lbl.setStyleSheet(f"color:{COLORS['fg_secondary']}; font-size:10pt;")
        self._notes_edit = QLineEdit()
        self._notes_edit.setPlaceholderText("Optional — duration, aspect ratio, style hints...")
        notes_row.addWidget(notes_lbl)
        notes_row.addWidget(self._notes_edit, stretch=1)
        idea_layout.addLayout(notes_row)
        root.addWidget(idea_group)

        # ── Generate button + status ─────────────────────────────────────
        btn_row = QHBoxLayout()
        self._gen_btn = QPushButton("✨  Generate Prompt")
        self._gen_btn.setMinimumHeight(40)
        self._gen_btn.clicked.connect(self._on_generate)
        btn_row.addWidget(self._gen_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        self._status_lbl = QLabel("")
        self._status_lbl.setObjectName("subtitle")
        root.addWidget(self._status_lbl)

        # ── Output ────────────────────────────────────────────────────────
        out_group = QGroupBox("Generated Prompt")
        out_layout = QVBoxLayout(out_group)
        self._output_edit = QTextEdit()
        self._output_edit.setReadOnly(True)
        self._output_edit.setPlaceholderText("Generated prompt will appear here...")
        out_layout.addWidget(self._output_edit)

        out_btn_row = QHBoxLayout()
        self._copy_btn = QPushButton("📋  Copy")
        self._copy_btn.setEnabled(False)
        self._copy_btn.clicked.connect(self._on_copy)
        self._send_btn = QPushButton("➜  Send to Generate Tab")
        self._send_btn.setEnabled(False)
        self._send_btn.clicked.connect(self._on_send)
        out_btn_row.addWidget(self._copy_btn)
        out_btn_row.addWidget(self._send_btn)
        out_btn_row.addStretch()
        out_layout.addLayout(out_btn_row)

        root.addWidget(out_group, stretch=1)

    # ------------------------------------------------------------------ #
    # Behavior
    # ------------------------------------------------------------------ #

    def _on_model_changed(self):
        is_h3 = self._model_combo.currentText() == "MiniMax H3"
        self._mode_lbl.setVisible(is_h3)
        self._mode_combo.setVisible(is_h3)
        self._refresh_key_state()

    def _refresh_key_state(self):
        has_key = bool(self._config.get("anthropic_api_key", "").strip())
        busy = self._worker is not None and self._worker.isRunning()
        self._gen_btn.setEnabled(has_key and not busy)
        if not has_key:
            self._status_lbl.setText("Set your Anthropic API key in Settings to use the prompt writer.")
        elif not busy:
            self._status_lbl.setText("")

    def refresh_mode(self):
        """Called when this tab becomes visible — re-check API key state."""
        self._refresh_key_state()

    def _build_system_prompt(self) -> str:
        if self._model_combo.currentText() == "WAN 2.2":
            return WAN_SYSTEM_PROMPT
        mode = self._mode_combo.currentText()
        guide = _load_h3_guide(mode)
        note = H3_MODE_NOTES.get(mode, "")
        return (
            "You write MiniMax H3 video-generation prompts by following the reference guide below exactly.\n\n"
            f"{note}\n\n"
            "Reference guide:\n"
            f"{guide}\n\n"
            "Output ONLY the final rewritten prompt text in the exact structure defined by the guide, "
            "nothing else (no preamble, no explanation, no markdown code fences)."
        )

    def _on_generate(self):
        idea = self._idea_edit.toPlainText().strip()
        if not idea:
            self._status_lbl.setText("Enter a rough idea first.")
            return

        api_key = self._config.get("anthropic_api_key", "").strip()
        if not api_key:
            self._refresh_key_state()
            return

        notes = self._notes_edit.text().strip()
        user_message = idea if not notes else f"{idea}\n\nAdditional notes: {notes}"

        system_prompt = self._build_system_prompt()

        self._gen_btn.setEnabled(False)
        self._copy_btn.setEnabled(False)
        self._send_btn.setEnabled(False)
        self._status_lbl.setText("Generating...")
        self._output_edit.clear()

        self._worker = PromptWriterWorker(api_key, system_prompt, user_message)
        self._worker.result_ready.connect(self._on_result)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(lambda: self._refresh_key_state())
        self._worker.start()

    def _on_result(self, text: str):
        self._output_edit.setPlainText(text)
        self._status_lbl.setText("Done.")
        self._copy_btn.setEnabled(True)
        self._send_btn.setEnabled(True)

    def _on_error(self, message: str):
        self._status_lbl.setText(message)

    def _on_copy(self):
        QApplication.clipboard().setText(self._output_edit.toPlainText())
        self._status_lbl.setText("Copied to clipboard.")

    def _on_send(self):
        text = self._output_edit.toPlainText().strip()
        if text:
            self.send_to_generate.emit(text)
