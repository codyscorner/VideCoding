from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel,
    QTextEdit, QLineEdit, QSlider, QSpinBox,
    QDoubleSpinBox, QComboBox, QWidget, QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QIntValidator

from ui.styles import COLORS, CARD_STYLESHEET

CARD_WIDTH = 300

NODE_ACCENT: dict[str, str] = {
    "CLIPTextEncode":          COLORS["prompt_color"],
    "LoraLoader":              COLORS["lora_color"],
    "KSampler":                COLORS["sampler_color"],
    "KSamplerAdvanced":        COLORS["sampler_color"],
    "CheckpointLoaderSimple":  COLORS["checkpoint_color"],
}

SAMPLER_NAMES = [
    "euler", "euler_ancestral", "heun", "heunpp2", "dpm_2",
    "dpm_2_ancestral", "lms", "dpm_fast", "dpm_adaptive",
    "dpmpp_2s_ancestral", "dpmpp_sde", "dpmpp_sde_gpu",
    "dpmpp_2m", "dpmpp_2m_sde", "dpmpp_2m_sde_gpu",
    "dpmpp_3m_sde", "dpmpp_3m_sde_gpu", "ddpm", "lcm",
    "ddim", "uni_pc", "uni_pc_bh2",
]

SCHEDULER_NAMES = [
    "normal", "karras", "exponential", "sgm_uniform",
    "simple", "ddim_uniform", "beta",
]


class NodeCard(QFrame):
    data_changed = pyqtSignal()

    def __init__(self, node_id: str, node_data: dict, parent=None):
        super().__init__(parent)
        self.node_id = node_id
        self.node_data = node_data
        self.inputs: dict = node_data.get("inputs", {})

        self.setObjectName("card")
        self.setFixedWidth(CARD_WIDTH)
        self.setStyleSheet(CARD_STYLESHEET)

        self._outer = QVBoxLayout(self)
        self._outer.setContentsMargins(0, 0, 0, 6)
        self._outer.setSpacing(0)

        self._build_header()
        self._build_body()   # dispatches to subclass override
        self._build_links()

    # ── helpers ──────────────────────────────────────────────────────────

    def _accent(self) -> str:
        return NODE_ACCENT.get(self.node_data.get("class_type", ""), COLORS["generic_color"])

    def _build_header(self):
        ct = self.node_data.get("class_type", "Unknown")
        title = self.node_data.get("_meta", {}).get("title", ct)
        accent = self._accent()

        header = QWidget()
        header.setFixedHeight(40)
        header.setStyleSheet(f"""
            QWidget {{
                background-color: {accent}22;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                border-bottom: 2px solid {accent};
            }}
        """)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(8, 0, 8, 0)
        hl.setSpacing(4)

        badge = QLabel(ct)
        badge.setStyleSheet(
            f"color: {accent}; font-size: 7pt; font-weight: bold; font-family: Consolas;"
        )

        title_lbl = QLabel(title)
        title_lbl.setStyleSheet(
            f"color: {COLORS['fg_primary']}; font-size: 9pt; font-weight: bold;"
        )
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        id_lbl = QLabel(f"#{self.node_id}")
        id_lbl.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 7pt; font-family: Consolas;"
        )

        hl.addWidget(badge)
        hl.addStretch()
        hl.addWidget(title_lbl)
        hl.addWidget(id_lbl)
        self._outer.addWidget(header)

    def _build_body(self):
        pass  # subclasses override

    def _build_links(self):
        link_inputs = {
            k: v for k, v in self.inputs.items()
            if isinstance(v, list) and len(v) == 2
        }
        if not link_inputs:
            return

        lw = QWidget()
        ll = QVBoxLayout(lw)
        ll.setContentsMargins(8, 2, 8, 4)
        ll.setSpacing(0)

        text = "  ·  ".join(f"{k}←#{v[0]}" for k, v in link_inputs.items())
        lbl = QLabel(text)
        lbl.setStyleSheet(
            f"color: {COLORS['fg_dim']}; font-size: 7pt; font-family: Consolas;"
        )
        lbl.setWordWrap(True)
        ll.addWidget(lbl)
        self._outer.addWidget(lw)

    def _field_row(self, body_layout: QVBoxLayout, label: str, widget: QWidget):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 2, 8, 2)
        rl.setSpacing(8)

        lbl = QLabel(label + ":")
        lbl.setFixedWidth(72)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 8pt;")

        rl.addWidget(lbl)
        rl.addWidget(widget, 1)
        body_layout.addWidget(row)

    def _slider_row(
        self,
        body_layout: QVBoxLayout,
        label: str,
        key: str,
        val_min: float,
        val_max: float,
        default: float,
    ):
        row = QWidget()
        rl = QHBoxLayout(row)
        rl.setContentsMargins(8, 2, 8, 2)
        rl.setSpacing(6)

        lbl = QLabel(label + ":")
        lbl.setFixedWidth(72)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setStyleSheet(f"color: {COLORS['fg_secondary']}; font-size: 8pt;")

        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(int(val_min * 100), int(val_max * 100))
        current = float(self.inputs.get(key, default))
        slider.setValue(int(current * 100))

        val_lbl = QLabel(f"{current:.2f}")
        val_lbl.setFixedWidth(38)
        val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        val_lbl.setStyleSheet(
            f"color: {COLORS['fg_primary']}; font-size: 8pt; font-family: Consolas;"
        )

        def on_change(v: int):
            real = v / 100.0
            self.inputs[key] = real
            val_lbl.setText(f"{real:.2f}")
            self.data_changed.emit()

        slider.valueChanged.connect(on_change)

        rl.addWidget(lbl)
        rl.addWidget(slider, 1)
        rl.addWidget(val_lbl)
        body_layout.addWidget(row)
        return slider


# ── Specialised cards ─────────────────────────────────────────────────────────

class PromptCard(NodeCard):
    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(8, 6, 8, 4)
        bl.setSpacing(2)

        text_edit = QTextEdit()
        text_edit.setFixedHeight(120)
        text_edit.setPlaceholderText("Enter prompt…")
        text_edit.setPlainText(str(self.inputs.get("text", "")))

        # Red border tint for nodes whose title contains "negative" / "neg"
        title = self.node_data.get("_meta", {}).get("title", "").lower()
        if "negative" in title or title.endswith("neg"):
            text_edit.setStyleSheet(f"""
                QTextEdit {{
                    background-color: {COLORS['bg_medium']};
                    color: {COLORS['fg_primary']};
                    border: 1px solid {COLORS['error']}66;
                    border-radius: 3px;
                    padding: 4px;
                    font-family: "Segoe UI";
                    font-size: 9pt;
                }}
            """)

        def on_changed():
            self.inputs["text"] = text_edit.toPlainText()
            self.data_changed.emit()

        text_edit.textChanged.connect(on_changed)
        bl.addWidget(text_edit)
        self._outer.addWidget(body)


class LoraCard(NodeCard):
    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(2)

        name_edit = QLineEdit(str(self.inputs.get("lora_name", "")))
        name_edit.setPlaceholderText("lora filename…")

        def on_name(t: str):
            self.inputs["lora_name"] = t
            self.data_changed.emit()

        name_edit.textChanged.connect(on_name)
        self._field_row(bl, "LoRA name", name_edit)

        self._slider_row(bl, "Model str", "strength_model", -2.0, 2.0, 1.0)
        self._slider_row(bl, "CLIP str",  "strength_clip",  -2.0, 2.0, 1.0)

        self._outer.addWidget(body)


class KSamplerCard(NodeCard):
    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(2)

        # Steps
        steps_spin = QSpinBox()
        steps_spin.setRange(1, 200)
        steps_spin.setValue(int(self.inputs.get("steps", 20)))
        steps_spin.valueChanged.connect(
            lambda v: (self.inputs.__setitem__("steps", v), self.data_changed.emit())
        )
        self._field_row(bl, "Steps", steps_spin)

        # CFG
        cfg_spin = QDoubleSpinBox()
        cfg_spin.setRange(0.0, 30.0)
        cfg_spin.setSingleStep(0.5)
        cfg_spin.setDecimals(1)
        cfg_spin.setValue(float(self.inputs.get("cfg", 7.0)))
        cfg_spin.valueChanged.connect(
            lambda v: (self.inputs.__setitem__("cfg", v), self.data_changed.emit())
        )
        self._field_row(bl, "CFG", cfg_spin)

        # Sampler
        sampler_cb = QComboBox()
        sampler_cb.addItems(SAMPLER_NAMES)
        cur = str(self.inputs.get("sampler_name", "euler"))
        if cur in SAMPLER_NAMES:
            sampler_cb.setCurrentText(cur)
        sampler_cb.currentTextChanged.connect(
            lambda t: (self.inputs.__setitem__("sampler_name", t), self.data_changed.emit())
        )
        self._field_row(bl, "Sampler", sampler_cb)

        # Scheduler
        sched_cb = QComboBox()
        sched_cb.addItems(SCHEDULER_NAMES)
        cur_s = str(self.inputs.get("scheduler", "normal"))
        if cur_s in SCHEDULER_NAMES:
            sched_cb.setCurrentText(cur_s)
        sched_cb.currentTextChanged.connect(
            lambda t: (self.inputs.__setitem__("scheduler", t), self.data_changed.emit())
        )
        self._field_row(bl, "Scheduler", sched_cb)

        # Seed (can exceed QSpinBox int32 range, so use QLineEdit)
        seed_edit = QLineEdit(str(self.inputs.get("seed", 0)))
        seed_edit.setValidator(QIntValidator(0, 2_147_483_647))

        def on_seed(t: str):
            try:
                self.inputs["seed"] = int(t)
                self.data_changed.emit()
            except ValueError:
                pass

        seed_edit.textChanged.connect(on_seed)
        self._field_row(bl, "Seed", seed_edit)

        # Denoise slider (only if the key exists in this workflow)
        if "denoise" in self.inputs:
            self._slider_row(bl, "Denoise", "denoise", 0.0, 1.0, 1.0)

        self._outer.addWidget(body)


class CheckpointCard(NodeCard):
    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(0, 4, 0, 0)
        bl.setSpacing(2)

        ckpt_edit = QLineEdit(str(self.inputs.get("ckpt_name", "")))
        ckpt_edit.setPlaceholderText("checkpoint filename…")
        ckpt_edit.textChanged.connect(
            lambda t: (self.inputs.__setitem__("ckpt_name", t), self.data_changed.emit())
        )
        self._field_row(bl, "Model", ckpt_edit)
        self._outer.addWidget(body)


class GenericCard(NodeCard):
    def _build_body(self):
        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(8, 6, 8, 4)
        bl.setSpacing(2)

        scalar_inputs = {
            k: v for k, v in self.inputs.items()
            if not (isinstance(v, list) and len(v) == 2)
        }

        if not scalar_inputs:
            placeholder = QLabel("(no scalar inputs)")
            placeholder.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 8pt;")
            bl.addWidget(placeholder)
        else:
            for key, val in list(scalar_inputs.items())[:6]:
                row_lbl = QLabel(f"{key}:  {val}")
                row_lbl.setStyleSheet(
                    f"color: {COLORS['fg_secondary']}; font-size: 8pt; font-family: Consolas;"
                )
                row_lbl.setWordWrap(True)
                bl.addWidget(row_lbl)
            if len(scalar_inputs) > 6:
                more = QLabel(f"…and {len(scalar_inputs) - 6} more")
                more.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 7pt;")
                bl.addWidget(more)

        self._outer.addWidget(body)


# ── factory ───────────────────────────────────────────────────────────────────

_CARD_MAP: dict[str, type[NodeCard]] = {
    "CLIPTextEncode":         PromptCard,
    "LoraLoader":             LoraCard,
    "KSampler":               KSamplerCard,
    "KSamplerAdvanced":       KSamplerCard,
    "CheckpointLoaderSimple": CheckpointCard,
}


def make_card(node_id: str, node_data: dict) -> NodeCard:
    cls = _CARD_MAP.get(node_data.get("class_type", ""), GenericCard)
    card = cls(node_id, node_data)
    card.adjustSize()
    return card
