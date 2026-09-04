import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea,
    QWidget, QFormLayout, QDialogButtonBox, QFrame, QComboBox,
)
from PyQt6.QtCore import Qt
from ui.styles import COLORS
from ui.prompt_history import append_history, PromptHistoryDialog


class SegmentEditorDialog(QDialog):
    """Quick-edit dialog for a single segment's workflow JSON.

    Editable fields:
      - Positive prompt (CLIPTextEncode — node 93 or whichever has the longer text)
      - Negative prompt (CLIPTextEncode — node 89 or the other one)
      - Frame count (WanImageToVideo.length)
      - LoRA strengths (all LoraLoaderModelOnly nodes)
    """

    # Node class types we care about
    _LORA_TYPES  = {"LoraLoaderModelOnly", "LoraLoader"}
    _STACK_TYPES = {"Lora Loader Stack (rgthree)"}
    _CLIP_TYPES  = {"CLIPTextEncode"}
    _WAN_TYPES   = {"WanImageToVideo", "WanVideoToVideo"}

    def __init__(self, segment: int, json_path: Path, config: dict = None, parent=None):
        super().__init__(parent)
        self._json_path = json_path
        self._segment = segment
        self._workflow: dict = {}
        self._config = config or {}
        self._lora_names: list[str] = self._scan_loras(self._config)
        self._prompt_font_size: int = int(self._config.get("segment_editor_font_size", 9))
        self._prompt_edits: list[QTextEdit] = []

        self.setWindowTitle(f"Segment {segment} — Quick Edit")
        self.setMinimumSize(700, 560)
        self.resize(780, 640)
        self.setStyleSheet(parent.styleSheet() if parent else "")

        self._load_workflow()
        self._build_ui()

    # ------------------------------------------------------------------ #
    # Load / save
    # ------------------------------------------------------------------ #

    def _load_workflow(self):
        try:
            with open(self._json_path, "r", encoding="utf-8") as f:
                self._workflow = json.load(f)
        except Exception as e:
            self._workflow = {}
            self._load_error = str(e)
        else:
            self._load_error = ""

    def _save_workflow(self):
        with open(self._json_path, "w", encoding="utf-8") as f:
            json.dump(self._workflow, f, indent=4)

    def _scan_loras(self, config: dict) -> list[str]:
        loras_dir = config.get("loras_dir", "")
        if not loras_dir:
            workflow_dir = config.get("workflow_dir", "")
            if workflow_dir:
                loras_dir = str(Path(workflow_dir).parent / "models" / "loras")
        if not loras_dir:
            return []
        base = Path(loras_dir)
        if not base.is_dir():
            return []
        exts = {".safetensors", ".ckpt", ".pt"}
        files = sorted(
            str(p.relative_to(base)).replace("\\", "/")
            for p in base.rglob("*")
            if p.suffix.lower() in exts
        )
        return files

    # ------------------------------------------------------------------ #
    # Identify nodes
    # ------------------------------------------------------------------ #

    def _nodes_of_type(self, class_types: set) -> list[tuple[str, dict]]:
        return [
            (nid, node) for nid, node in self._workflow.items()
            if node.get("class_type") in class_types
        ]

    def _identify_prompts(self) -> tuple[tuple | None, tuple | None]:
        """Return (positive_node, negative_node) as (nid, node, field) tuples.
        Positive = longer text; negative = shorter (usually the quality negative).

        CLIPTextEncode holds its text in `inputs.text`. MiniMax H3 nodes
        (MiniMaxH3ImageToVideo etc.) pack the whole structured prompt —
        description + soundscape + music — into a single `inputs.prompt`
        field with no separate negative, so they're matched by class_type
        prefix rather than a fixed node-type set (H3 has several
        mode-specific node classes: image/text/first-last-frame/reference
        to video)."""
        clips = [(nid, node, "text") for nid, node in self._nodes_of_type(self._CLIP_TYPES)]
        h3_nodes = [
            (nid, node, "prompt") for nid, node in self._workflow.items()
            if node.get("class_type", "").startswith("MiniMaxH3") and "prompt" in node.get("inputs", {})
        ]
        candidates = clips + h3_nodes
        if not candidates:
            return None, None
        if len(candidates) == 1:
            return candidates[0], None
        # Negative prompt contains quality keywords — detect by common negative terms
        neg_keywords = {"blurry", "distorted", "deformed", "ugly", "watermark", "artifact"}
        def is_negative(candidate):
            text = candidate[1].get("inputs", {}).get(candidate[2], "")
            text = text.lower() if isinstance(text, str) else ""
            return sum(1 for kw in neg_keywords if kw in text)

        candidates_sorted = sorted(candidates, key=is_negative, reverse=True)
        return candidates_sorted[1], candidates_sorted[0]  # positive, negative

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)
        root.setContentsMargins(16, 16, 16, 16)

        if self._load_error:
            err = QLabel(f"Could not load workflow:\n{self._load_error}")
            err.setStyleSheet("color: #ff6b6b;")
            root.addWidget(err)
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(self.reject)
            root.addWidget(buttons)
            return

        title_row = QHBoxLayout()
        title = QLabel(f"Segment {self._segment}  —  {self._json_path.name}")
        title.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {COLORS['accent']};")
        title_row.addWidget(title)
        title_row.addStretch()
        font_lbl = QLabel("Text Size:")
        font_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt;")
        title_row.addWidget(font_lbl)
        font_spin = QSpinBox()
        font_spin.setRange(7, 24)
        font_spin.setValue(self._prompt_font_size)
        font_spin.setFixedWidth(60)
        font_spin.setStyleSheet(self._input_style())
        font_spin.valueChanged.connect(self._on_font_size_changed)
        title_row.addWidget(font_spin)
        root.addLayout(title_row)

        # Scrollable content area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(12)
        content_layout.setContentsMargins(0, 0, 8, 0)
        scroll.setWidget(content)
        root.addWidget(scroll, stretch=1)

        self._editors: list[tuple[str, str, object]] = []  # (nid, field, widget)
        self._pos_prompt_edit: QTextEdit | None = None
        self._neg_prompt_edit: QTextEdit | None = None

        # ── Prompts ───────────────────────────────────────────────────────
        pos_node, neg_node = self._identify_prompts()

        if pos_node:
            nid, node, field = pos_node
            is_h3 = node.get("class_type", "").startswith("MiniMaxH3")
            group, widget = self._text_editor(
                "Prompt" if is_h3 else "Positive Prompt",
                node["inputs"].get(field, ""),
                height=220 if is_h3 else 120,
            )
            content_layout.addWidget(group)
            self._editors.append((nid, field, widget))
            self._pos_prompt_edit = widget

        if neg_node:
            nid, node, field = neg_node
            group, widget = self._text_editor(
                "Negative Prompt",
                node["inputs"].get(field, ""),
                height=80
            )
            content_layout.addWidget(group)
            self._editors.append((nid, field, widget))
            self._neg_prompt_edit = widget

        # ── Frame count ───────────────────────────────────────────────────
        wan_nodes = self._nodes_of_type(self._WAN_TYPES)
        for nid, node in wan_nodes:
            length = node["inputs"].get("length")
            if length is not None:
                group, widget = self._spinbox_editor("Frame Count", int(length), 1, 1000)
                content_layout.addWidget(group)
                self._editors.append((nid, "length", widget))

        # ── Duration (seconds) — MiniMax H3 drives its frame length from a
        # PrimitiveFloat node (titled "Float (duration)") feeding a math
        # expression, rather than a raw frame count like WAN
        for nid, node in self._workflow.items():
            if node.get("class_type") != "PrimitiveFloat":
                continue
            if "duration" not in node.get("_meta", {}).get("title", "").lower():
                continue
            value = node["inputs"].get("value")
            if value is None:
                continue
            group, widget = self._double_spinbox_editor(
                "Duration (seconds)", float(value), 1.0, 15.0,
                hint="MiniMax H3 supports up to 15s"
            )
            content_layout.addWidget(group)
            self._editors.append((nid, "value", widget))

        # ── LoRAs (individual loader nodes) ───────────────────────────────
        lora_nodes = self._nodes_of_type(self._LORA_TYPES)
        if lora_nodes:
            lora_group = QGroupBox("LoRA Strengths")
            lora_group.setStyleSheet(self._group_style())
            lora_form = QFormLayout(lora_group)
            lora_form.setSpacing(8)
            lora_form.setContentsMargins(12, 12, 12, 12)

            for nid, node in lora_nodes:
                lora_name = node["inputs"].get("lora_name", "")
                strength = float(node["inputs"].get("strength_model", 1.0))

                combo = self._lora_combo(lora_name)
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0.0, 4.0)
                spinbox.setSingleStep(0.05)
                spinbox.setDecimals(2)
                spinbox.setValue(strength)
                spinbox.setFixedWidth(90)
                spinbox.setStyleSheet(self._input_style())

                row = QHBoxLayout()
                row.setSpacing(6)
                row.addWidget(combo, stretch=1)
                strength_lbl = QLabel("Strength:")
                strength_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt;")
                row.addWidget(strength_lbl)
                row.addWidget(spinbox)
                row_widget = QWidget()
                row_widget.setLayout(row)

                lora_form.addRow(row_widget)
                self._editors.append((nid, "lora_name", combo))
                self._editors.append((nid, "strength_model", spinbox))

            content_layout.addWidget(lora_group)

        # ── LoRA Stack nodes (rgthree) ─────────────────────────────────────
        stack_nodes = self._nodes_of_type(self._STACK_TYPES)
        for nid, node in stack_nodes:
            title = node.get("_meta", {}).get("title", f"LoRA Stack (Node {nid})")
            stack_group = QGroupBox(f"LoRA Stack — {title}")
            stack_group.setStyleSheet(self._group_style())
            stack_form = QFormLayout(stack_group)
            stack_form.setSpacing(8)
            stack_form.setContentsMargins(12, 12, 12, 12)

            inputs = node["inputs"]
            # Find all lora_NN / strength_NN pairs — always show every slot
            i = 1
            while f"lora_{i:02d}" in inputs or f"lora_0{i}" in inputs:
                key_lora = f"lora_{i:02d}" if f"lora_{i:02d}" in inputs else f"lora_0{i}"
                key_str  = f"strength_{i:02d}" if f"strength_{i:02d}" in inputs else f"strength_0{i}"
                lora_name = inputs.get(key_lora, "None") or "None"
                strength  = float(inputs.get(key_str, 0.0))

                slot_lbl = QLabel(f"Slot {i}:")
                slot_lbl.setFixedWidth(46)
                slot_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt;")

                combo = self._lora_combo(lora_name)
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0.0, 4.0)
                spinbox.setSingleStep(0.05)
                spinbox.setDecimals(2)
                spinbox.setValue(strength)
                spinbox.setFixedWidth(90)
                spinbox.setStyleSheet(self._input_style())

                row = QHBoxLayout()
                row.setSpacing(6)
                row.addWidget(slot_lbl)
                row.addWidget(combo, stretch=1)
                strength_lbl = QLabel("Strength:")
                strength_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt;")
                row.addWidget(strength_lbl)
                row.addWidget(spinbox)
                row_widget = QWidget()
                row_widget.setLayout(row)

                stack_form.addRow(row_widget)
                self._editors.append((nid, key_lora, combo))
                self._editors.append((nid, key_str, spinbox))
                i += 1

            content_layout.addWidget(stack_group)

        content_layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("💾  Save")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._on_save)
        history_btn = QPushButton("📜  History")
        history_btn.setFixedHeight(40)
        history_btn.setEnabled(self._pos_prompt_edit is not None or self._neg_prompt_edit is not None)
        history_btn.clicked.connect(self._on_view_history)
        cancel_btn = QPushButton("✕  Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(history_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(cancel_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

    def _on_save(self):
        for nid, field, widget in self._editors:
            node = self._workflow.get(nid)
            if node is None:
                continue
            if isinstance(widget, QTextEdit):
                node["inputs"][field] = widget.toPlainText()
            elif isinstance(widget, QComboBox):
                node["inputs"][field] = widget.currentText()
            elif isinstance(widget, QDoubleSpinBox):
                node["inputs"][field] = round(widget.value(), 4)
            elif isinstance(widget, QSpinBox):
                node["inputs"][field] = widget.value()
        try:
            self._save_workflow()
            if self._pos_prompt_edit is not None or self._neg_prompt_edit is not None:
                positive = self._pos_prompt_edit.toPlainText() if self._pos_prompt_edit else ""
                negative = self._neg_prompt_edit.toPlainText() if self._neg_prompt_edit else ""
                append_history(self._json_path, positive, negative)
            self.accept()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", str(e))

    def _on_view_history(self):
        dlg = PromptHistoryDialog(self._json_path, parent=self)
        if dlg.exec() == dlg.DialogCode.Accepted:
            entry = dlg.selected_entry()
            if entry:
                if self._pos_prompt_edit is not None:
                    self._pos_prompt_edit.setPlainText(entry.get("positive", ""))
                if self._neg_prompt_edit is not None:
                    self._neg_prompt_edit.setPlainText(entry.get("negative", ""))

    # ------------------------------------------------------------------ #
    # Widget helpers
    # ------------------------------------------------------------------ #

    def _text_editor(self, label: str, text: str, height: int = 120) -> tuple[QGroupBox, QTextEdit]:
        group = QGroupBox(label)
        group.setStyleSheet(self._group_style())
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        edit = QTextEdit()
        edit.setPlainText(text)
        edit.setFixedHeight(height)
        edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['fg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                font-size: {self._prompt_font_size}pt;
                padding: 4px;
            }}
        """)
        layout.addWidget(edit)
        self._prompt_edits.append(edit)
        return group, edit

    def _on_font_size_changed(self, size: int):
        self._prompt_font_size = size
        for edit in self._prompt_edits:
            font = edit.font()
            font.setPointSize(size)
            edit.setFont(font)
        if hasattr(self._config, "set"):
            self._config.set("segment_editor_font_size", size)
            if hasattr(self._config, "save"):
                self._config.save()

    def _spinbox_editor(self, label: str, value: int, min_: int, max_: int) -> tuple[QGroupBox, QSpinBox]:
        group = QGroupBox(label)
        group.setStyleSheet(self._group_style())
        row = QHBoxLayout(group)
        row.setContentsMargins(12, 8, 12, 8)
        spinbox = QSpinBox()
        spinbox.setRange(min_, max_)
        spinbox.setValue(value)
        spinbox.setFixedWidth(100)
        spinbox.setStyleSheet(self._input_style())
        hint = QLabel("frames  (fps × seconds = frames,  e.g. 16fps × 6s = 97)")
        hint.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 8pt;")
        row.addWidget(spinbox)
        row.addSpacing(12)
        row.addWidget(hint)
        row.addStretch()
        return group, spinbox

    def _double_spinbox_editor(self, label: str, value: float, min_: float, max_: float,
                                step: float = 0.5, hint: str = "") -> tuple[QGroupBox, QDoubleSpinBox]:
        group = QGroupBox(label)
        group.setStyleSheet(self._group_style())
        row = QHBoxLayout(group)
        row.setContentsMargins(12, 8, 12, 8)
        spinbox = QDoubleSpinBox()
        spinbox.setRange(min_, max_)
        spinbox.setSingleStep(step)
        spinbox.setDecimals(1)
        spinbox.setValue(value)
        spinbox.setFixedWidth(100)
        spinbox.setStyleSheet(self._input_style())
        row.addWidget(spinbox)
        if hint:
            hint_lbl = QLabel(hint)
            hint_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 8pt;")
            row.addSpacing(12)
            row.addWidget(hint_lbl)
        row.addStretch()
        return group, spinbox

    def _group_style(self) -> str:
        return f"""
            QGroupBox {{
                color: {COLORS['accent']};
                font-weight: bold;
                font-size: 10pt;
                border: 1px solid {COLORS['border']};
                border-radius: 4px;
                margin-top: 8px;
                padding-top: 4px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 8px;
                padding: 0 4px;
            }}
        """

    def _lora_combo(self, current: str) -> QComboBox:
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItem("None")
        combo.addItems(self._lora_names)
        idx = combo.findText(current)
        if idx >= 0:
            combo.setCurrentIndex(idx)
        else:
            combo.setCurrentText(current)
        combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['fg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 3px 24px 3px 6px;
                font-size: 9pt;
            }}
            QComboBox::drop-down {{
                subcontrol-origin: padding;
                subcontrol-position: top right;
                width: 20px;
                border-left: 1px solid {COLORS['border']};
            }}
            QComboBox::down-arrow {{
                width: 10px;
                height: 10px;
                border: 2px solid {COLORS['fg_primary']};
                border-top: none;
                border-right: none;
                transform: rotate(-45deg);
            }}
            QComboBox QAbstractItemView {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['fg_primary']};
                selection-background-color: {COLORS['accent']};
                border: 1px solid {COLORS['border']};
            }}
        """)
        return combo

    def _input_style(self) -> str:
        return f"""
            QDoubleSpinBox, QSpinBox {{
                background-color: {COLORS['bg_medium']};
                color: {COLORS['fg_primary']};
                border: 1px solid {COLORS['border']};
                border-radius: 3px;
                padding: 3px 6px;
                font-size: 10pt;
            }}
        """
