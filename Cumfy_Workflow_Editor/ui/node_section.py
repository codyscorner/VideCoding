"""
One collapsible section per workflow node, plus the editor-widget factory.

`NodeSection` renders a node's title bar (category-coloured), its editable fields
in a form, and a dim read-only line listing wired-up inputs.  `EditorBinding`
pairs a `Field` with the widget editing it and knows how to read the value back
in the right JSON type.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLabel, QToolButton,
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QLineEdit, QTextEdit,
    QSizePolicy, QFrame,
)
from PyQt6.QtGui import QRegularExpressionValidator
from PyQt6.QtCore import Qt, QRegularExpression

from ui.styles import COLORS
from workflow import (
    NodeInfo, Field, number_hint,
    CAT_PROMPT, CAT_LORA, CAT_SAMPLER, CAT_OUTPUT, CAT_LOADER, CAT_MEDIA, CAT_NOTES,
)

CATEGORY_COLORS = {
    CAT_PROMPT:  COLORS["prompt_color"],
    CAT_LORA:    COLORS["lora_color"],
    CAT_SAMPLER: COLORS["sampler_color"],
    CAT_OUTPUT:  COLORS["output_color"],
    CAT_LOADER:  COLORS["checkpoint_color"],
    CAT_MEDIA:   COLORS["media_color"],
    CAT_NOTES:   COLORS["fg_secondary"],
}


def category_color(category: str) -> str:
    return CATEGORY_COLORS.get(category, COLORS["generic_color"])


# ── editor styling ────────────────────────────────────────────────────────────

def _spin_style() -> str:
    return f"""
        QSpinBox, QDoubleSpinBox {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 3px 6px;
            font-size: 10pt;
        }}
        QSpinBox:focus, QDoubleSpinBox:focus {{ border: 1px solid {COLORS['accent']}; }}
        QSpinBox::up-button, QDoubleSpinBox::up-button,
        QSpinBox::down-button, QDoubleSpinBox::down-button {{ width: 16px; }}
    """


def _text_style(accent: str | None = None) -> str:
    border = accent or COLORS["border"]
    return f"""
        QTextEdit {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {border};
            border-radius: 4px;
            padding: 6px;
            font-family: "Segoe UI";
            font-size: 10pt;
        }}
        QTextEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
    """


def _line_style() -> str:
    return f"""
        QLineEdit {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 4px 6px;
            font-size: 10pt;
        }}
        QLineEdit:focus {{ border: 1px solid {COLORS['accent']}; }}
        QLineEdit:disabled {{ color: {COLORS['fg_dim']}; }}
    """


def _combo_style() -> str:
    return f"""
        QComboBox {{
            background-color: {COLORS['bg_medium']};
            color: {COLORS['fg_primary']};
            border: 1px solid {COLORS['border']};
            border-radius: 3px;
            padding: 3px 6px;
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


_CHECK_STYLE = f"""
    QCheckBox {{ color: {COLORS['fg_primary']}; spacing: 8px; }}
    QCheckBox::indicator {{ width: 16px; height: 16px; }}
"""


# ── bindings ──────────────────────────────────────────────────────────────────

@dataclass
class EditorBinding:
    field: Field
    widget: QWidget
    read: Callable[[], object]

    def commit(self):
        self.field.apply(self.read())


def make_editor(field: Field, on_change: Callable, accent: str | None = None) -> EditorBinding:
    """Create the right widget for a field and wire its change signal."""
    kind, value = field.kind, field.value

    if kind == "bool":
        cb = QCheckBox("enabled" if value else "disabled")
        cb.setChecked(bool(value))
        cb.setStyleSheet(_CHECK_STYLE)
        cb.toggled.connect(lambda on, w=cb: w.setText("enabled" if on else "disabled"))
        cb.toggled.connect(on_change)
        return EditorBinding(field, cb, cb.isChecked)

    if kind == "int":
        lo, hi, step, _ = number_hint(field.key)
        spin = QSpinBox()
        spin.setRange(int(max(lo, -2 ** 31)), int(min(hi, 2 ** 31 - 1)))
        spin.setSingleStep(int(step) or 1)
        spin.setValue(int(value))
        spin.setFixedWidth(110)
        spin.setStyleSheet(_spin_style())
        spin.valueChanged.connect(on_change)
        return EditorBinding(field, spin, spin.value)

    if kind == "bigint":
        edit = QLineEdit(str(value))
        edit.setValidator(QRegularExpressionValidator(QRegularExpression("-?[0-9]{0,20}")))
        edit.setFixedWidth(200)
        edit.setStyleSheet(_line_style())
        edit.textChanged.connect(on_change)

        def read_int(e=edit, orig=value):
            try:
                return int(e.text())
            except ValueError:
                return orig
        return EditorBinding(field, edit, read_int)

    if kind == "float":
        lo, hi, step, decimals = number_hint(field.key)
        spin = QDoubleSpinBox()
        spin.setRange(lo, hi)
        spin.setSingleStep(step)
        spin.setDecimals(max(decimals, 1))
        spin.setValue(float(value))
        spin.setFixedWidth(110)
        spin.setStyleSheet(_spin_style())
        spin.valueChanged.connect(on_change)

        def read_float(s=spin, d=max(decimals, 1), was_int=isinstance(value, int)):
            v = round(s.value(), d)
            # keep whole numbers as ints when the file stored them that way
            return int(v) if was_int and v.is_integer() else v
        return EditorBinding(field, spin, read_float)

    if kind == "choice":
        combo = QComboBox()
        combo.setEditable(True)
        combo.addItems(field.choices)
        if str(value) not in field.choices:
            combo.addItem(str(value))
        combo.setCurrentText(str(value))
        combo.setMinimumWidth(180)
        # don't let the longest choice dictate the card's minimum width
        combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        combo.setMinimumContentsLength(14)
        combo.setStyleSheet(_combo_style())
        combo.currentTextChanged.connect(on_change)
        return EditorBinding(field, combo, combo.currentText)

    if kind == "text":
        edit = QTextEdit()
        edit.setPlainText(str(value))
        edit.setAcceptRichText(False)
        edit.setMinimumHeight(60)
        edit.setFixedHeight(_text_height(str(value)))
        edit.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        edit.setStyleSheet(_text_style(accent))
        edit.textChanged.connect(on_change)
        return EditorBinding(field, edit, edit.toPlainText)

    if kind == "line":
        edit = QLineEdit(str(value))
        edit.setStyleSheet(_line_style())
        edit.textChanged.connect(on_change)
        return EditorBinding(field, edit, edit.text)

    # readonly / unknown: show but don't edit; commit writes the original back
    edit = QLineEdit("" if value is None else str(value))
    edit.setEnabled(False)
    edit.setStyleSheet(_line_style())
    return EditorBinding(field, edit, lambda v=value: v)


def _text_height(text: str) -> int:
    lines = text.count("\n") + 1 + len(text) // 90
    return max(60, min(260, 24 + lines * 20))


def _esc(text: str) -> str:
    return (str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


# ── section widget ────────────────────────────────────────────────────────────

class NodeSection(QFrame):
    """Collapsible card for a single node."""

    def __init__(self, node: NodeInfo, on_change: Callable, parent: QWidget | None = None):
        super().__init__(parent)
        self.node = node
        self.bindings: list[EditorBinding] = []
        color = category_color(node.category)

        self.setObjectName("nodeSection")
        self.setStyleSheet(f"""
            QFrame#nodeSection {{
                background-color: {COLORS['bg_card']};
                border: 1px solid {COLORS['border_card']};
                border-left: 3px solid {color};
                border-radius: 5px;
            }}
        """)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 6, 10, 8)
        outer.setSpacing(4)

        # ── header ────────────────────────────────────────────────────────
        header = QHBoxLayout()
        header.setSpacing(8)

        self._toggle = QToolButton()
        self._toggle.setArrowType(Qt.ArrowType.DownArrow)
        self._toggle.setCheckable(True)
        self._toggle.setChecked(True)
        self._toggle.setAutoRaise(True)
        self._toggle.setStyleSheet("QToolButton { border: none; background: transparent; }")
        self._toggle.toggled.connect(self.set_expanded)
        header.addWidget(self._toggle)

        # one wrapping label so a long title can never force the card wider than the window
        meta_text = node.class_type if node.class_type != node.title else ""
        meta_bits = [b for b in (meta_text, f"#{node.id}") if b]
        title = QLabel(
            f"<span style='color:{color}; font-weight:bold; font-size:10pt;'>{_esc(node.title)}</span>"
            f" <span style='color:{COLORS['fg_dim']}; font-size:8pt;'> · {_esc(' · '.join(meta_bits))}</span>"
        )
        title.setTextFormat(Qt.TextFormat.RichText)
        title.setWordWrap(True)
        title.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        header.addWidget(title, 1)
        if node.state_badge:
            badge = QLabel(node.state_badge)
            badge.setStyleSheet(
                f"color: {COLORS['bg_dark']}; background-color: {COLORS['warning']};"
                f"font-size: 7pt; font-weight: bold; padding: 1px 6px; border-radius: 3px;"
            )
            header.addWidget(badge)
        outer.addLayout(header)

        # ── body ──────────────────────────────────────────────────────────
        self._body = QWidget()
        body = QVBoxLayout(self._body)
        body.setContentsMargins(22, 2, 0, 0)
        body.setSpacing(6)

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(6)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        lbl_style = f"color: {COLORS['fg_secondary']}; font-size: 9pt;"

        text_accent = (COLORS["error"] + "66") if node.is_negative_prompt else None
        for fld in node.fields:
            binding = make_editor(fld, on_change, accent=text_accent)
            self.bindings.append(binding)
            if fld.kind == "text":
                # paragraph fields go full width under their label
                lbl = QLabel(fld.label)
                lbl.setStyleSheet(
                    f"color: {COLORS['error'] if node.is_negative_prompt else COLORS['fg_secondary']};"
                    f"font-size: 9pt; font-weight: bold;"
                )
                body.addWidget(lbl)
                body.addWidget(binding.widget)
            else:
                lbl = QLabel(fld.label + ":")
                lbl.setStyleSheet(lbl_style)
                if fld.kind == "readonly":
                    lbl.setToolTip("Driven by a connection — edit the source node instead")
                form.addRow(lbl, binding.widget)

        if form.rowCount():
            body.addLayout(form)

        if not node.fields:
            none_lbl = QLabel("No editable settings — every input is a connection.")
            none_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 9pt; font-style: italic;")
            none_lbl.setWordWrap(True)
            body.addWidget(none_lbl)

        if node.links:
            joined = "   ·   ".join(f"{ln.name} ← {ln.source}" for ln in node.links)
            links_lbl = QLabel(f"Connections:  {joined}")
            links_lbl.setStyleSheet(f"color: {COLORS['fg_dim']}; font-size: 8pt;")
            links_lbl.setWordWrap(True)
            body.addWidget(links_lbl)

        outer.addWidget(self._body)

    # ── collapse ──────────────────────────────────────────────────────────

    def set_expanded(self, expanded: bool):
        self._body.setVisible(expanded)
        self._toggle.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        if self._toggle.isChecked() != expanded:
            self._toggle.setChecked(expanded)

    # ── filtering ─────────────────────────────────────────────────────────

    def matches(self, needle: str) -> bool:
        if not needle:
            return True
        hay = f"{self.node.title} {self.node.class_type} {self.node.id} {self.node.category}".lower()
        return needle.lower() in hay

    @property
    def has_settings(self) -> bool:
        return bool(self.node.fields)
