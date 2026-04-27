from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QPushButton, QFrame
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from bb_constants import Tool, PALETTE_16, THICKNESS_LEVELS


class SidebarPanel(QWidget):
    """Left-side tool palette: tools, color swatches, thickness, bidir toggle."""

    def __init__(self, view):
        super().__init__()
        self._view = view
        self.setFixedWidth(100)
        self.setStyleSheet("background: #1e1e2e;")

        root = QVBoxLayout(self)
        root.setContentsMargins(6, 8, 6, 8)
        root.setSpacing(3)

        self._tool_btns: dict[Tool, QPushButton] = {}

        sections = [
            ("— TOOLS —",    None,               ""),
            ("Select",        Tool.SELECT,        "S"),
            ("Pan",           Tool.PAN,           "P"),
            ("— DRAW —",     None,               ""),
            ("Pen",           Tool.PEN,           "D"),
            ("Rectangle",     Tool.RECT,          "R"),
            ("Ellipse",       Tool.ELLIPSE,       "E"),
            ("Arrow",         Tool.ARROW,         "A"),
            ("Text",          Tool.TEXT,          "T"),
            ("— NODES —",    None,               ""),
            ("Table",         Tool.NODE_TABLE,    "1"),
            ("Decision",      Tool.NODE_DECISION, "2"),
            ("Procedure",     Tool.NODE_PROC,     "3"),
            ("API",           Tool.NODE_API,      "4"),
            ("Note",          Tool.NODE_NOTE,     "5"),
            ("Generic",       Tool.NODE_GENERIC,  "6"),
        ]

        for label, tool, shortcut in sections:
            if tool is None:
                lbl = QLabel(label)
                lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
                lbl.setStyleSheet("color:#666;font-size:9px;padding:6px 0 2px 0;")
                root.addWidget(lbl)
            else:
                btn = QPushButton(label)
                btn.setCheckable(True)
                btn.setFixedHeight(32)
                btn.setToolTip(f"{label}  [{shortcut}]" if shortcut else label)
                btn.setShortcut(shortcut)
                btn.setStyleSheet(self._btn_style())
                btn.clicked.connect(lambda _, t=tool: self._select_tool(t))
                root.addWidget(btn)
                self._tool_btns[tool] = btn

        # ── Color palette ──────────────────────────────────────────────────
        root.addWidget(self._separator())
        color_lbl = QLabel("— COLOR —")
        color_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        color_lbl.setStyleSheet("color:#666;font-size:9px;padding:4px 0 2px 0;")
        root.addWidget(color_lbl)

        grid = QGridLayout()
        grid.setSpacing(3)
        grid.setContentsMargins(0, 0, 0, 0)
        for idx, (hex_color, name) in enumerate(PALETTE_16):
            swatch = QPushButton()
            swatch.setFixedSize(38, 20)
            swatch.setToolTip(name)
            swatch.setStyleSheet(
                f"background:{hex_color};border:1px solid #555;border-radius:3px;")
            swatch.clicked.connect(lambda _, c=QColor(hex_color): self._set_color(c))
            grid.addWidget(swatch, idx // 2, idx % 2)
        root.addLayout(grid)

        # ── Thickness ─────────────────────────────────────────────────────
        root.addWidget(self._separator())
        thick_lbl = QLabel("— WIDTH —")
        thick_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        thick_lbl.setStyleSheet("color:#666;font-size:9px;padding:4px 0 2px 0;")
        root.addWidget(thick_lbl)

        self._thick_btns: dict[int, QPushButton] = {}
        for w, lbl in zip(THICKNESS_LEVELS, ["Thin", "Medium", "Thick"]):
            btn = QPushButton(lbl)
            btn.setCheckable(True)
            btn.setFixedHeight(28)
            btn.setStyleSheet(self._btn_style())
            btn.clicked.connect(lambda _, ww=w: self._set_width(ww))
            root.addWidget(btn)
            self._thick_btns[w] = btn

        # ── Bidirectional toggle ───────────────────────────────────────────
        root.addWidget(self._separator())
        self._bidir_btn = QPushButton("→  One-way")
        self._bidir_btn.setCheckable(True)
        self._bidir_btn.setFixedHeight(32)
        self._bidir_btn.setToolTip("Toggle bidirectional connections")
        self._bidir_btn.setStyleSheet(self._btn_style())
        self._bidir_btn.clicked.connect(self._toggle_bidir)
        root.addWidget(self._bidir_btn)

        root.addStretch()

        self._select_tool(Tool.SELECT)
        self._set_width(2)

    @staticmethod
    def _separator() -> QFrame:
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet("color:#333;")
        return sep

    @staticmethod
    def _btn_style() -> str:
        return (
            "QPushButton{background:#2a2a3e;color:#ccc;border:1px solid #444;"
            "border-radius:3px;font-size:11px;}"
            "QPushButton:checked{background:#4060a0;color:#fff;border:1px solid #80a0e0;}"
            "QPushButton:hover{background:#333350;}"
        )

    def _select_tool(self, tool: Tool):
        for t, btn in self._tool_btns.items():
            btn.setChecked(t == tool)
        self._view.set_tool(tool)

    def _set_color(self, color: QColor):
        self._view.draw_color = color

    def _set_width(self, width: int):
        for w, btn in self._thick_btns.items():
            btn.setChecked(w == width)
        self._view.draw_width = width

    def _toggle_bidir(self, checked: bool):
        self._view.conn_bidir = checked
        self._bidir_btn.setText("↔  Both-way" if checked else "→  One-way")
