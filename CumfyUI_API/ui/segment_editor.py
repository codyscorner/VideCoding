import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QDoubleSpinBox, QSpinBox, QGroupBox, QScrollArea,
    QWidget, QFormLayout, QDialogButtonBox, QFrame,
)
from PyQt6.QtCore import Qt
from ui.styles import COLORS


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

    def __init__(self, segment: int, json_path: Path, parent=None):
        super().__init__(parent)
        self._json_path = json_path
        self._segment = segment
        self._workflow: dict = {}

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
            with open(self._json_path, "r") as f:
                self._workflow = json.load(f)
        except Exception as e:
            self._workflow = {}
            self._load_error = str(e)
        else:
            self._load_error = ""

    def _save_workflow(self):
        with open(self._json_path, "w") as f:
            json.dump(self._workflow, f, indent=4)

    # ------------------------------------------------------------------ #
    # Identify nodes
    # ------------------------------------------------------------------ #

    def _nodes_of_type(self, class_types: set) -> list[tuple[str, dict]]:
        return [
            (nid, node) for nid, node in self._workflow.items()
            if node.get("class_type") in class_types
        ]

    def _identify_prompts(self) -> tuple[tuple | None, tuple | None]:
        """Return (positive_node, negative_node) as (nid, node) tuples.
        Positive = longer text; negative = shorter (usually the quality negative)."""
        clips = self._nodes_of_type(self._CLIP_TYPES)
        if not clips:
            return None, None
        if len(clips) == 1:
            return clips[0], None
        # Negative prompt contains quality keywords — detect by common negative terms
        neg_keywords = {"blurry", "distorted", "deformed", "ugly", "watermark", "artifact"}
        def is_negative(node_tuple):
            text = node_tuple[1].get("inputs", {}).get("text", "").lower()
            return sum(1 for kw in neg_keywords if kw in text)

        clips_sorted = sorted(clips, key=is_negative, reverse=True)
        return clips_sorted[1], clips_sorted[0]  # positive, negative

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

        title = QLabel(f"Segment {self._segment}  —  {self._json_path.name}")
        title.setStyleSheet(f"font-size: 11pt; font-weight: bold; color: {COLORS['accent']};")
        root.addWidget(title)

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

        # ── Prompts ───────────────────────────────────────────────────────
        pos_node, neg_node = self._identify_prompts()

        if pos_node:
            nid, node = pos_node
            group, widget = self._text_editor(
                "Positive Prompt",
                node["inputs"].get("text", "")
            )
            content_layout.addWidget(group)
            self._editors.append((nid, "text", widget))

        if neg_node:
            nid, node = neg_node
            group, widget = self._text_editor(
                "Negative Prompt",
                node["inputs"].get("text", ""),
                height=80
            )
            content_layout.addWidget(group)
            self._editors.append((nid, "text", widget))

        # ── Frame count ───────────────────────────────────────────────────
        wan_nodes = self._nodes_of_type(self._WAN_TYPES)
        for nid, node in wan_nodes:
            length = node["inputs"].get("length")
            if length is not None:
                group, widget = self._spinbox_editor("Frame Count", int(length), 1, 1000)
                content_layout.addWidget(group)
                self._editors.append((nid, "length", widget))

        # ── LoRAs (individual loader nodes) ───────────────────────────────
        lora_nodes = self._nodes_of_type(self._LORA_TYPES)
        if lora_nodes:
            lora_group = QGroupBox("LoRA Strengths")
            lora_group.setStyleSheet(self._group_style())
            lora_form = QFormLayout(lora_group)
            lora_form.setSpacing(8)
            lora_form.setContentsMargins(12, 12, 12, 12)

            for nid, node in lora_nodes:
                lora_name = node["inputs"].get("lora_name", f"Node {nid}")
                strength = float(node["inputs"].get("strength_model", 1.0))
                spinbox = QDoubleSpinBox()
                spinbox.setRange(0.0, 4.0)
                spinbox.setSingleStep(0.05)
                spinbox.setDecimals(2)
                spinbox.setValue(strength)
                spinbox.setFixedWidth(90)
                spinbox.setStyleSheet(self._input_style())
                name_lbl = QLabel(Path(lora_name).stem)
                name_lbl.setStyleSheet(f"color: {COLORS['fg_primary']}; font-size: 9pt;")
                name_lbl.setWordWrap(True)
                lora_form.addRow(name_lbl, spinbox)
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
            # Find all lora_NN / strength_NN pairs
            i = 1
            while f"lora_{i:02d}" in inputs or f"lora_0{i}" in inputs:
                key_lora = f"lora_{i:02d}" if f"lora_{i:02d}" in inputs else f"lora_0{i}"
                key_str  = f"strength_{i:02d}" if f"strength_{i:02d}" in inputs else f"strength_0{i}"
                lora_name = inputs.get(key_lora, "None")
                strength  = float(inputs.get(key_str, 1.0))
                if lora_name and lora_name != "None":
                    spinbox = QDoubleSpinBox()
                    spinbox.setRange(0.0, 4.0)
                    spinbox.setSingleStep(0.05)
                    spinbox.setDecimals(2)
                    spinbox.setValue(strength)
                    spinbox.setFixedWidth(90)
                    spinbox.setStyleSheet(self._input_style())
                    name_lbl = QLabel(Path(lora_name).stem)
                    name_lbl.setStyleSheet(f"color: {COLORS['fg_primary']}; font-size: 9pt;")
                    name_lbl.setWordWrap(True)
                    stack_form.addRow(name_lbl, spinbox)
                    self._editors.append((nid, key_str, spinbox))
                i += 1

            if stack_form.rowCount() > 0:
                content_layout.addWidget(stack_group)

        content_layout.addStretch()

        # ── Buttons ───────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        save_btn = QPushButton("💾  Save")
        save_btn.setFixedHeight(40)
        save_btn.clicked.connect(self._on_save)
        cancel_btn = QPushButton("✕  Cancel")
        cancel_btn.setObjectName("cancel_btn")
        cancel_btn.setFixedHeight(40)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(save_btn)
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
            elif isinstance(widget, QDoubleSpinBox):
                node["inputs"][field] = round(widget.value(), 4)
            elif isinstance(widget, QSpinBox):
                node["inputs"][field] = widget.value()
        try:
            self._save_workflow()
            self.accept()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "Save Error", str(e))

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
                font-size: 9pt;
                padding: 4px;
            }}
        """)
        layout.addWidget(edit)
        return group, edit

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
