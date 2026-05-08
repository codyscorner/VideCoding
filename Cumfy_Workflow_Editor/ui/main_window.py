import json
from pathlib import Path

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QDoubleSpinBox,
    QSpinBox, QComboBox, QGroupBox, QFormLayout,
    QScrollArea, QFrame, QFileDialog, QMessageBox,
    QSizePolicy, QLineEdit,
)
from PyQt6.QtGui import QAction
from PyQt6.QtCore import Qt

from ui.styles import APP_STYLESHEET, COLORS
from settings import Settings

# Node class types we surface
_CLIP_TYPES  = {"CLIPTextEncode"}
_LORA_TYPES  = {"LoraLoader", "LoraLoaderModelOnly"}
_STACK_TYPES = {"Lora Loader Stack (rgthree)"}
_SAMPLER_TYPES = {"KSampler", "KSamplerAdvanced"}
_WAN_TYPES   = {"WanImageToVideo", "WanVideoToVideo"}

SAMPLER_NAMES = [
    "euler", "euler_ancestral", "heun", "heunpp2", "dpm_2",
    "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm",
    "ddim", "uni_pc", "uni_pc_bh2",
]
SCHEDULER_NAMES = ["normal", "karras", "exponential", "sgm_uniform", "simple", "ddim_uniform", "beta"]


def _group_style(accent: str | None = None) -> str:
    color = accent or COLORS["accent_hover"]
    return f"""
        QGroupBox {{
            color: {color};
            font-weight: bold;
            font-size: 10pt;
            border: 1px solid {COLORS['border']};
            border-radius: 5px;
            margin-top: 10px;
            padding-top: 6px;
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 4px;
        }}
    """


def _spinbox_style() -> str:
    return f"""
        QDoubleSpinBox, QSpinBox {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 3px 6px;
            font-size: 10pt;
        }}
        QDoubleSpinBox:focus, QSpinBox:focus {{
            border: 1px solid {COLORS['accent']};
        }}
    """


def _textarea_style(accent: str | None = None) -> str:
    border = accent or COLORS["border"]
    return f"""
        QTextEdit {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {border};
            border-radius: 3px;
            font-size: 9pt;
            padding: 5px;
        }}
        QTextEdit:focus {{
            border: 1px solid {COLORS['accent']};
        }}
    """


def _lineedit_style() -> str:
    return f"""
        QLineEdit {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 3px 7px;
            font-size: 10pt;
        }}
        QLineEdit:focus {{
            border: 1px solid {COLORS['accent']};
        }}
    """


def _combo_style() -> str:
    return f"""
        QComboBox {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 3px 8px;
            font-size: 10pt;
        }}
        QComboBox:focus {{ border: 1px solid {COLORS['accent']}; }}
        QComboBox::drop-down {{ border: none; width: 20px; }}
        QComboBox QAbstractItemView {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            selection-background-color: {COLORS['accent']};
            border: 1px solid {COLORS['border']};
        }}
    """


class MainWindow(QMainWindow):
    def __init__(self, version: str, settings: Settings):
        super().__init__()
        self.version = version
        self._settings = settings
        self._path: Path | None = None
        self._workflow: dict = {}
        self._editors: list[tuple[str, str, object]] = []  # (node_id, field, widget)
        self._modified = False

        self.setWindowTitle(f"ComfyUI Workflow Editor  v{version}")
        self.resize(780, 860)
        self.setStyleSheet(APP_STYLESHEET)

        self._build_menu()
        self._build_toolbar()
        self._build_body()
        self._build_statusbar()

    # ── menu ──────────────────────────────────────────────────────────────

    def _build_menu(self):
        mb = self.menuBar()

        file_menu = mb.addMenu("&File")
        for label, shortcut, slot in [
            ("&Open…",       "Ctrl+O",       self.open_file),
            (None,           None,            None),
            ("&Save",        "Ctrl+S",       self.save_file),
            ("Save &As…",    "Ctrl+Shift+S", self.save_as),
            (None,           None,            None),
            ("&Quit",        "Ctrl+Q",       self.close),
        ]:
            if label is None:
                file_menu.addSeparator()
            else:
                act = QAction(label, self)
                act.setShortcut(shortcut)
                act.triggered.connect(slot)
                file_menu.addAction(act)

    # ── toolbar ───────────────────────────────────────────────────────────

    def _build_toolbar(self):
        tb = self.addToolBar("Main")
        tb.setMovable(False)

        for text, slot in [("Open", self.open_file), ("Save", self.save_file)]:
            btn = QPushButton(text)
            btn.clicked.connect(slot)
            tb.addWidget(btn)

        tb.addSeparator()

        self._file_lbl = QLabel("  No file open")
        self._file_lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 9pt;")
        tb.addWidget(self._file_lbl)

    # ── body (scroll area + empty state) ─────────────────────────────────

    def _build_body(self):
        self._central = QWidget()
        self._central_layout = QVBoxLayout(self._central)
        self._central_layout.setContentsMargins(0, 0, 0, 0)
        self._central_layout.setSpacing(0)
        self.setCentralWidget(self._central)

        # Empty-state placeholder
        self._empty = QWidget()
        el = QVBoxLayout(self._empty)
        el.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_lbl = QLabel("Open a ComfyUI workflow JSON to begin editing")
        empty_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 12pt;")
        empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        open_btn = QPushButton("Open Workflow…")
        open_btn.setFixedWidth(200)
        open_btn.clicked.connect(self.open_file)
        el.addWidget(empty_lbl)
        el.addSpacing(16)
        el.addWidget(open_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        self._central_layout.addWidget(self._empty)

        # Scroll area (hidden until a file is loaded)
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.hide()
        self._central_layout.addWidget(self._scroll)

    def _build_statusbar(self):
        self._status_lbl = QLabel("Ready")
        self._status_lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; padding: 2px 6px;")
        self.statusBar().addWidget(self._status_lbl)

    # ── form builder ──────────────────────────────────────────────────────

    def _build_form(self):
        """Scan _workflow and build the editor form from found nodes."""
        self._editors.clear()

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(20, 16, 20, 24)
        layout.setSpacing(14)

        # helper: nodes matching a set of class_types
        def nodes_of(*types):
            wanted = set(types)
            return [
                (nid, node) for nid, node in self._workflow.items()
                if isinstance(node, dict) and node.get("class_type") in wanted
            ]

        has_sections = False

        # ── PROMPTS ───────────────────────────────────────────────────────
        clip_nodes = nodes_of(*_CLIP_TYPES)
        if clip_nodes:
            has_sections = True
            prompts_group = QGroupBox("Prompts")
            prompts_group.setStyleSheet(_group_style(COLORS["prompt_color"]))
            pg_layout = QVBoxLayout(prompts_group)
            pg_layout.setContentsMargins(12, 12, 12, 12)
            pg_layout.setSpacing(10)

            # Sort: put nodes whose title contains "negative" last
            def neg_score(item):
                t = item[1].get("_meta", {}).get("title", "").lower()
                return 1 if ("neg" in t or "negative" in t) else 0
            clip_nodes.sort(key=neg_score)

            for nid, node in clip_nodes:
                title = node.get("_meta", {}).get("title", f"Prompt (Node {nid})")
                text  = node.get("inputs", {}).get("text", "")
                is_neg = neg_score((nid, node)) == 1

                sub_label = QLabel(title)
                sub_label.setStyleSheet(
                    f"color: {COLORS['error'] if is_neg else COLORS['prompt_color']};"
                    f"font-size: 9pt; font-weight: bold; margin-bottom: 2px;"
                )
                edit = QTextEdit()
                edit.setPlainText(text)
                edit.setMinimumHeight(50)
                edit.setFixedHeight(80 if is_neg else 140)
                edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
                edit.setStyleSheet(_textarea_style(
                    COLORS["error"] + "66" if is_neg else None
                ))
                edit.textChanged.connect(self._mark_modified)

                pg_layout.addWidget(sub_label)
                pg_layout.addWidget(edit)
                self._editors.append((nid, "text", edit))

            layout.addWidget(prompts_group)

        # ── LoRA STRENGTHS (individual loader nodes) ──────────────────────
        lora_nodes = nodes_of(*_LORA_TYPES)
        if lora_nodes:
            has_sections = True
            lora_group = QGroupBox("LoRA Strengths")
            lora_group.setStyleSheet(_group_style(COLORS["lora_color"]))
            lora_form = QFormLayout(lora_group)
            lora_form.setContentsMargins(14, 12, 14, 12)
            lora_form.setSpacing(8)
            lora_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

            for nid, node in lora_nodes:
                inputs = node.get("inputs", {})
                lora_name = Path(str(inputs.get("lora_name", f"Node {nid}"))).stem

                row_widget = QWidget()
                row_h = QHBoxLayout(row_widget)
                row_h.setContentsMargins(0, 0, 0, 0)
                row_h.setSpacing(16)

                for field_label, field_key in [("Model", "strength_model"), ("CLIP", "strength_clip")]:
                    if field_key not in inputs:
                        continue
                    spin = QDoubleSpinBox()
                    spin.setRange(-2.0, 4.0)
                    spin.setSingleStep(0.05)
                    spin.setDecimals(2)
                    spin.setFixedWidth(90)
                    spin.setValue(float(inputs.get(field_key, 1.0)))
                    spin.setStyleSheet(_spinbox_style())
                    spin.valueChanged.connect(self._mark_modified)
                    row_h.addWidget(QLabel(field_label + ":"))
                    row_h.addWidget(spin)
                    self._editors.append((nid, field_key, spin))

                row_h.addStretch()
                name_lbl = QLabel(lora_name)
                name_lbl.setStyleSheet(f"color: {COLORS['fg_primary']}; font-size: 9pt;")
                name_lbl.setWordWrap(True)
                lora_form.addRow(name_lbl, row_widget)

            layout.addWidget(lora_group)

        # ── LoRA STACK (rgthree) ──────────────────────────────────────────
        for nid, node in nodes_of(*_STACK_TYPES):
            inputs = node.get("inputs", {})
            stack_title = node.get("_meta", {}).get("title", f"LoRA Stack (Node {nid})")
            stack_group = QGroupBox(stack_title)
            stack_group.setStyleSheet(_group_style(COLORS["lora_color"]))
            stack_form = QFormLayout(stack_group)
            stack_form.setContentsMargins(14, 12, 14, 12)
            stack_form.setSpacing(8)
            stack_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            row_count = 0
            i = 1
            while True:
                k_lora = f"lora_{i:02d}" if f"lora_{i:02d}" in inputs else f"lora_0{i}" if f"lora_0{i}" in inputs else None
                k_str  = f"strength_{i:02d}" if f"strength_{i:02d}" in inputs else f"strength_0{i}" if f"strength_0{i}" in inputs else None
                if k_lora is None:
                    break
                lora_name = inputs.get(k_lora, "None")
                if lora_name and lora_name != "None":
                    spin = QDoubleSpinBox()
                    spin.setRange(0.0, 4.0)
                    spin.setSingleStep(0.05)
                    spin.setDecimals(2)
                    spin.setFixedWidth(90)
                    spin.setValue(float(inputs.get(k_str, 1.0)) if k_str else 1.0)
                    spin.setStyleSheet(_spinbox_style())
                    spin.valueChanged.connect(self._mark_modified)
                    lbl = QLabel(Path(lora_name).stem)
                    lbl.setStyleSheet(f"color: {COLORS['fg_primary']}; font-size: 9pt;")
                    stack_form.addRow(lbl, spin)
                    if k_str:
                        self._editors.append((nid, k_str, spin))
                    row_count += 1
                i += 1
            if row_count > 0:
                has_sections = True
                layout.addWidget(stack_group)

        # ── KSAMPLER ──────────────────────────────────────────────────────
        sampler_nodes = nodes_of(*_SAMPLER_TYPES)
        if sampler_nodes:
            has_sections = True
            for nid, node in sampler_nodes:
                inputs = node.get("inputs", {})
                node_title = node.get("_meta", {}).get("title", node.get("class_type", "KSampler"))
                samp_group = QGroupBox(node_title)
                samp_group.setStyleSheet(_group_style(COLORS["sampler_color"]))
                samp_form = QFormLayout(samp_group)
                samp_form.setContentsMargins(14, 12, 14, 12)
                samp_form.setSpacing(8)
                samp_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

                lbl_style = f"color: {COLORS['fg_secondary']}; font-size: 9pt;"

                if "steps" in inputs:
                    spin = QSpinBox()
                    spin.setRange(1, 200)
                    spin.setValue(int(inputs.get("steps", 20)))
                    spin.setFixedWidth(90)
                    spin.setStyleSheet(_spinbox_style())
                    spin.valueChanged.connect(self._mark_modified)
                    lbl = QLabel("Steps:"); lbl.setStyleSheet(lbl_style)
                    samp_form.addRow(lbl, spin)
                    self._editors.append((nid, "steps", spin))

                if "cfg" in inputs:
                    spin = QDoubleSpinBox()
                    spin.setRange(0.0, 30.0)
                    spin.setSingleStep(0.5)
                    spin.setDecimals(1)
                    spin.setValue(float(inputs.get("cfg", 7.0)))
                    spin.setFixedWidth(90)
                    spin.setStyleSheet(_spinbox_style())
                    spin.valueChanged.connect(self._mark_modified)
                    lbl = QLabel("CFG:"); lbl.setStyleSheet(lbl_style)
                    samp_form.addRow(lbl, spin)
                    self._editors.append((nid, "cfg", spin))

                if "sampler_name" in inputs:
                    cb = QComboBox()
                    cb.addItems(SAMPLER_NAMES)
                    cur = str(inputs.get("sampler_name", "euler"))
                    if cur in SAMPLER_NAMES:
                        cb.setCurrentText(cur)
                    cb.setStyleSheet(_combo_style())
                    cb.currentTextChanged.connect(self._mark_modified)
                    lbl = QLabel("Sampler:"); lbl.setStyleSheet(lbl_style)
                    samp_form.addRow(lbl, cb)
                    self._editors.append((nid, "sampler_name", cb))

                if "scheduler" in inputs:
                    cb = QComboBox()
                    cb.addItems(SCHEDULER_NAMES)
                    cur_s = str(inputs.get("scheduler", "normal"))
                    if cur_s in SCHEDULER_NAMES:
                        cb.setCurrentText(cur_s)
                    cb.setStyleSheet(_combo_style())
                    cb.currentTextChanged.connect(self._mark_modified)
                    lbl = QLabel("Scheduler:"); lbl.setStyleSheet(lbl_style)
                    samp_form.addRow(lbl, cb)
                    self._editors.append((nid, "scheduler", cb))

                if "seed" in inputs:
                    seed_edit = QLineEdit(str(inputs.get("seed", 0)))
                    seed_edit.setStyleSheet(_lineedit_style())
                    seed_edit.textChanged.connect(self._mark_modified)
                    lbl = QLabel("Seed:"); lbl.setStyleSheet(lbl_style)
                    samp_form.addRow(lbl, seed_edit)
                    self._editors.append((nid, "seed", seed_edit))

                layout.addWidget(samp_group)

        # ── WAN VIDEO ─────────────────────────────────────────────────────
        wan_nodes = nodes_of(*_WAN_TYPES)
        if wan_nodes:
            has_sections = True
            wan_group = QGroupBox("Video Settings")
            wan_group.setStyleSheet(_group_style(COLORS["checkpoint_color"]))
            wan_form = QFormLayout(wan_group)
            wan_form.setContentsMargins(14, 12, 14, 12)
            wan_form.setSpacing(8)
            wan_form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            lbl_style = f"color: {COLORS['fg_secondary']}; font-size: 9pt;"

            for nid, node in wan_nodes:
                inputs = node.get("inputs", {})
                node_title = node.get("_meta", {}).get("title", node.get("class_type", ""))
                if "length" in inputs:
                    spin = QSpinBox()
                    spin.setRange(1, 2000)
                    spin.setValue(int(inputs.get("length", 97)))
                    spin.setFixedWidth(90)
                    spin.setStyleSheet(_spinbox_style())
                    spin.valueChanged.connect(self._mark_modified)
                    hint = QLabel("  frames  (e.g. 16fps × 6s = 97)")
                    hint.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 8pt;")
                    row = QWidget()
                    rh = QHBoxLayout(row)
                    rh.setContentsMargins(0, 0, 0, 0)
                    rh.addWidget(spin)
                    rh.addWidget(hint)
                    rh.addStretch()
                    label_text = f"Frame count ({node_title}):" if node_title else "Frame count:"
                    lbl = QLabel(label_text); lbl.setStyleSheet(lbl_style)
                    wan_form.addRow(lbl, row)
                    self._editors.append((nid, "length", spin))

            layout.addWidget(wan_group)

        # ── fallback if nothing found ─────────────────────────────────────
        if not has_sections:
            none_lbl = QLabel(
                "No editable nodes found (CLIPTextEncode, LoraLoader, KSampler, WanImageToVideo).\n"
                "This workflow may use unsupported node types."
            )
            none_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 10pt;")
            none_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            none_lbl.setWordWrap(True)
            layout.addWidget(none_lbl)

        layout.addStretch()
        self._scroll.setWidget(container)

    # ── file operations ───────────────────────────────────────────────────

    def open_file(self):
        start_dir = self._settings.get("last_dir", "")
        path, _ = QFileDialog.getOpenFileName(
            self, "Open ComfyUI Workflow", start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as exc:
            QMessageBox.critical(self, "Open failed", f"Could not load:\n{exc}")
            return

        self._path = Path(path)
        self._settings.set("last_dir", str(self._path.parent))
        self._workflow = data
        self._modified = False

        self._empty.hide()
        self._scroll.show()
        self._build_form()
        self._update_title()

        node_count = sum(1 for v in data.values() if isinstance(v, dict) and "class_type" in v)
        self._status_lbl.setText(f"{self._path.name}  —  {node_count} nodes  —  {len(self._editors)} editable fields")
        self._file_lbl.setText(f"  {self._path.name}")

    def save_file(self):
        if not self._workflow:
            return
        if self._path is None:
            self.save_as()
            return
        self._commit_and_save(self._path)

    def save_as(self):
        if not self._workflow:
            return
        start_dir = str(self._path.parent) if self._path else self._settings.get("last_dir", "")
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Workflow As", start_dir,
            "JSON Files (*.json);;All Files (*)",
        )
        if not path:
            return
        self._commit_and_save(Path(path))

    def _commit_and_save(self, path: Path):
        """Write all editor widgets back into _workflow then save JSON."""
        for nid, field, widget in self._editors:
            node = self._workflow.get(nid)
            if node is None:
                continue
            inputs = node.setdefault("inputs", {})
            if isinstance(widget, QTextEdit):
                inputs[field] = widget.toPlainText()
            elif isinstance(widget, QDoubleSpinBox):
                inputs[field] = round(widget.value(), 4)
            elif isinstance(widget, QSpinBox):
                inputs[field] = widget.value()
            elif isinstance(widget, QComboBox):
                inputs[field] = widget.currentText()
            elif isinstance(widget, QLineEdit):
                try:
                    inputs[field] = int(widget.text())
                except ValueError:
                    inputs[field] = widget.text()

        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self._workflow, f, indent=2, ensure_ascii=False)
            self._path = path
            self._settings.set("last_dir", str(path.parent))
            self._modified = False
            self._update_title()
            self._status_lbl.setText(f"Saved  —  {path.name}")
        except Exception as exc:
            QMessageBox.critical(self, "Save failed", f"Could not save:\n{exc}")

    # ── helpers ───────────────────────────────────────────────────────────

    def _mark_modified(self, *_):
        if not self._modified:
            self._modified = True
            self._update_title()

    def _update_title(self):
        base = f"ComfyUI Workflow Editor  v{self.version}"
        if self._path:
            marker = " *" if self._modified else ""
            self.setWindowTitle(f"{base}  —  {self._path.name}{marker}")
        else:
            self.setWindowTitle(base)

    def closeEvent(self, event):
        if not self._modified:
            event.accept()
            return
        reply = QMessageBox.question(
            self, "Unsaved changes",
            "You have unsaved changes. Save before closing?",
            QMessageBox.StandardButton.Save |
            QMessageBox.StandardButton.Discard |
            QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Save:
            self.save_file()
            event.accept()
        elif reply == QMessageBox.StandardButton.Discard:
            event.accept()
        else:
            event.ignore()
