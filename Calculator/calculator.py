"""
Calculator v1.1.0
Dark Blue / Midnight theme PyQt6 Calculator
"""

import re
import sys
import math
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QGridLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont, QIcon

__version__ = "1.1.0"

_NUM_RE = re.compile(r'(\d*\.?\d+)$')

BASE_W, BASE_H = 370, 580
SCI_EXTRA_H = 78
HIST_EXTRA_W = 210


# ---------------------------------------------------------------------------
# QSS Stylesheet — keeps design fully separate from logic
# ---------------------------------------------------------------------------
QSS = """
QMainWindow {
    background-color: #1b1e23;
}

/* ── Main container ── */
#container {
    background-color: #1b1e23;
    border-radius: 16px;
}

/* ── Display area ── */
#display_widget {
    background-color: #1b1e23;
    padding: 12px 18px 6px 18px;
}

#expression_label {
    color: #8a8fa8;
    font-size: 16px;
    qproperty-alignment: AlignRight;
    background: transparent;
}

#result_label {
    color: #e8eaf6;
    font-size: 36px;
    font-weight: bold;
    qproperty-alignment: AlignRight;
    background: transparent;
}

/* ── Button grid container ── */
#button_area {
    background-color: #252932;
    border-radius: 14px;
    padding: 10px;
}

/* ── Base button ── */
QPushButton {
    border: none;
    border-radius: 10px;
    font-size: 20px;
    font-weight: 600;
    min-height: 68px;
    min-width: 68px;
    color: #e8eaf6;
    background-color: #303542;
}
QPushButton:hover {
    background-color: #3a404f;
}
QPushButton:pressed {
    background-color: #252932;
}

/* ── Operator buttons (+, -, *, /, ^) ── */
QPushButton[btnClass="operator"] {
    background-color: #2e3340;
    color: #90caf9;
}
QPushButton[btnClass="operator"]:hover {
    background-color: #3a4257;
}

/* ── Function buttons (AC, +/-, %) ── */
QPushButton[btnClass="function"] {
    background-color: #3a404f;
    color: #b0bec5;
}
QPushButton[btnClass="function"]:hover {
    background-color: #454c5c;
}

/* ── Equals button ── */
QPushButton[btnClass="equals"] {
    background-color: #3d5afe;
    color: #ffffff;
    font-size: 26px;
}
QPushButton[btnClass="equals"]:hover {
    background-color: #536dfe;
}
QPushButton[btnClass="equals"]:pressed {
    background-color: #304ffe;
}

/* ── Memory buttons ── */
QPushButton[btnClass="memory"] {
    background-color: #1a2340;
    color: #7986cb;
    font-size: 14px;
    font-weight: 500;
    min-height: 38px;
    border-radius: 8px;
}
QPushButton[btnClass="memory"]:hover {
    background-color: #223060;
}

/* ── Utility buttons (Copy / History / Scientific) ── */
QPushButton[btnClass="util"] {
    background-color: #1a2340;
    color: #7986cb;
    font-size: 13px;
    font-weight: 500;
    min-height: 32px;
    border-radius: 8px;
}
QPushButton[btnClass="util"]:hover {
    background-color: #223060;
}
QPushButton[btnClass="util"][active="true"] {
    background-color: #3d5afe;
    color: #ffffff;
}

/* ── Scientific function buttons ── */
QPushButton[btnClass="sci"] {
    background-color: #2a2f3d;
    color: #b39ddb;
    font-size: 16px;
    min-height: 46px;
}
QPushButton[btnClass="sci"]:hover {
    background-color: #363c4d;
}

/* ── Zero button (wide) ── */
QPushButton#btn_zero {
    text-align: left;
    padding-left: 22px;
}

/* ── History panel ── */
#history_panel {
    background-color: #20242c;
    border-radius: 14px;
}
#history_title {
    color: #8a8fa8;
    font-size: 13px;
    font-weight: 600;
    padding: 4px 8px;
    background: transparent;
}
QListWidget#history_list {
    background-color: transparent;
    border: none;
    color: #e8eaf6;
    font-size: 13px;
}
QListWidget#history_list::item {
    padding: 6px 8px;
    border-radius: 6px;
}
QListWidget#history_list::item:hover {
    background-color: #2e3340;
}
QListWidget#history_list::item:selected {
    background-color: #3d5afe;
}
"""


# ---------------------------------------------------------------------------
# Calculator Window
# ---------------------------------------------------------------------------
class Calculator(QMainWindow):
    """Main calculator window."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Midnight Calculator  v{__version__}")
        icon_path = Path(__file__).parent / "app_icon.ico"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

        # State
        self._expr = "0"           # the full expression being built/eval'd
        self._fresh = True         # True right after '=' or AC — next digit starts new entry
        self._memory = 0.0
        self.sci_mode = False
        self.history_visible = False

        self._build_ui()
        self._apply_style()
        self._update_window_size()
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setFocus()

    # ── UI Construction ──────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("container")
        self.setCentralWidget(central)

        outer = QHBoxLayout(central)
        outer.setContentsMargins(10, 10, 10, 10)
        outer.setSpacing(8)

        left = QWidget()
        root = QVBoxLayout(left)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)
        outer.addWidget(left)

        # Display
        display_widget = QWidget()
        display_widget.setObjectName("display_widget")
        disp_layout = QVBoxLayout(display_widget)
        disp_layout.setContentsMargins(0, 0, 0, 0)
        disp_layout.setSpacing(2)

        self.expr_label = QLabel("")
        self.expr_label.setObjectName("expression_label")
        self.expr_label.setFont(QFont("Segoe UI", 14))

        self.result_label = QLabel("0")
        self.result_label.setObjectName("result_label")
        self.result_label.setFont(QFont("Segoe UI", 36, QFont.Weight.Bold))
        self.result_label.setMinimumHeight(70)

        disp_layout.addWidget(self.expr_label)
        disp_layout.addWidget(self.result_label)
        root.addWidget(display_widget)

        # Button area
        btn_area = QWidget()
        btn_area.setObjectName("button_area")
        grid = QGridLayout(btn_area)
        grid.setSpacing(8)

        # Utility row — Copy / History / Scientific toggle
        copy_btn = QPushButton("Copy")
        copy_btn.setProperty("btnClass", "util")
        copy_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        copy_btn.clicked.connect(self._copy_result)
        grid.addWidget(copy_btn, 0, 0, 1, 2)

        self.hist_btn = QPushButton("Hist")
        self.hist_btn.setProperty("btnClass", "util")
        self.hist_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.hist_btn.clicked.connect(self._toggle_history)
        grid.addWidget(self.hist_btn, 0, 2, 1, 1)

        self.sci_btn = QPushButton("Sci")
        self.sci_btn.setProperty("btnClass", "util")
        self.sci_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.sci_btn.clicked.connect(self._toggle_sci)
        grid.addWidget(self.sci_btn, 0, 3, 1, 1)

        # Memory row
        mem_buttons = [
            ("MC", 1, 0), ("MR", 1, 1), ("M-", 1, 2), ("M+", 1, 3),
        ]
        for label, row, col in mem_buttons:
            btn = self._make_button(label, "memory")
            grid.addWidget(btn, row, col)

        # Main button layout — row, col, rowspan, colspan
        main_buttons = [
            # label,      class,      row, col, rspan, cspan
            ("AC",        "function", 2,   0,   1,     1),
            ("+/-",       "function", 2,   1,   1,     1),
            ("%",         "function", 2,   2,   1,     1),
            ("/",         "operator", 2,   3,   1,     1),

            ("7",         "digit",    3,   0,   1,     1),
            ("8",         "digit",    3,   1,   1,     1),
            ("9",         "digit",    3,   2,   1,     1),
            ("*",         "operator", 3,   3,   1,     1),

            ("4",         "digit",    4,   0,   1,     1),
            ("5",         "digit",    4,   1,   1,     1),
            ("6",         "digit",    4,   2,   1,     1),
            ("-",         "operator", 4,   3,   1,     1),

            ("1",         "digit",    5,   0,   1,     1),
            ("2",         "digit",    5,   1,   1,     1),
            ("3",         "digit",    5,   2,   1,     1),
            ("+",         "operator", 5,   3,   1,     1),

            ("0",         "digit",    6,   0,   1,     2),
            (".",         "digit",    6,   2,   1,     1),
            ("=",         "equals",   6,   3,   1,     1),
        ]

        for item in main_buttons:
            label, cls, row, col, rspan, cspan = item
            btn = self._make_button(label, cls)
            if label == "0":
                btn.setObjectName("btn_zero")
                btn.setStyleSheet(
                    "QPushButton { text-align: left; padding-left: 22px; }"
                )
            grid.addWidget(btn, row, col, rspan, cspan)

        # Scientific row — hidden until toggled on
        self.sci_row = QWidget()
        sci_grid = QGridLayout(self.sci_row)
        sci_grid.setContentsMargins(0, 0, 0, 0)
        sci_grid.setSpacing(8)
        sci_buttons = [
            ("(", "(", "sci"),
            (")", ")", "sci"),
            ("√", "√", "sci"),
            ("xʸ", "^", "sci"),
        ]
        for col, (text, label, cls) in enumerate(sci_buttons):
            btn = self._make_button(label, cls, text=text)
            sci_grid.addWidget(btn, 0, col)
        grid.addWidget(self.sci_row, 7, 0, 1, 4)
        self.sci_row.setVisible(False)

        root.addWidget(btn_area)

        # History panel — hidden until toggled on
        self.history_panel = QWidget()
        self.history_panel.setObjectName("history_panel")
        hist_layout = QVBoxLayout(self.history_panel)
        hist_layout.setContentsMargins(8, 8, 8, 8)
        hist_title = QLabel("History")
        hist_title.setObjectName("history_title")
        self.history_list = QListWidget()
        self.history_list.setObjectName("history_list")
        self.history_list.itemClicked.connect(self._on_history_clicked)
        hist_layout.addWidget(hist_title)
        hist_layout.addWidget(self.history_list)
        outer.addWidget(self.history_panel)
        self.history_panel.setVisible(False)

    def _make_button(self, label: str, cls: str, text: str = None) -> QPushButton:
        """Create a styled button and connect it to the handler."""
        btn = QPushButton(text if text is not None else label)
        btn.setProperty("btnClass", cls)
        btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn.clicked.connect(lambda _, l=label: self._on_button(l))
        return btn

    def _apply_style(self):
        QApplication.instance().setStyleSheet(QSS)

    def _update_window_size(self):
        w = BASE_W + (HIST_EXTRA_W if self.history_visible else 0)
        h = BASE_H + (SCI_EXTRA_H if self.sci_mode else 0)
        self.setFixedSize(QSize(w, h))

    # ── Display helpers ──────────────────────────────────────────────────
    def _set_display(self, value: str, expression: str = ""):
        self.result_label.setText(value)
        self.expr_label.setText(expression)

    def _update_display(self):
        self._set_display(self._expr if self._expr else "0", "")

    def _format(self, value: float) -> str:
        """Return a clean, comma-grouped string for a float — drop '.0' for integers."""
        if value == int(value) and abs(value) < 1e15:
            return f"{int(value):,}"
        return f"{value:,.10g}"

    def _format_plain(self, value: float) -> str:
        """Return a clean string with no comma grouping, safe to feed back into an expression."""
        if value == int(value) and abs(value) < 1e15:
            return str(int(value))
        return f"{value:.10g}"

    def _segment_start(self) -> int:
        """Index of the start of the number/segment currently being typed."""
        idx = -1
        for ch in "+-*/^(":
            pos = self._expr.rfind(ch)
            if pos > idx:
                idx = pos
        return idx + 1

    # ── Button dispatcher ────────────────────────────────────────────────
    def _on_button(self, label: str):
        """Route button presses to the correct handler."""
        if label in "0123456789":
            self._input_digit(label)
        elif label == ".":
            self._input_dot()
        elif label in ("+", "-", "*", "/", "^"):
            self._input_operator(label)
        elif label in ("(", ")"):
            self._input_paren(label)
        elif label == "√":
            self._input_sqrt()
        elif label == "=":
            self._calculate()
        elif label == "AC":
            self._clear_all()
        elif label == "+/-":
            self._toggle_sign()
        elif label == "%":
            self._percent()
        elif label == "MC":
            self._memory = 0.0
        elif label == "MR":
            self._recall_memory()
        elif label == "M+":
            self._memory_op("+")
        elif label == "M-":
            self._memory_op("-")

    # ── Input logic ──────────────────────────────────────────────────────
    def _input_digit(self, digit: str):
        if self._fresh:
            self._expr = digit
            self._fresh = False
        elif self._expr in ("", "0"):
            self._expr = digit
        else:
            m = _NUM_RE.search(self._expr)
            if m and m.group(1) == "0" and m.end() == len(self._expr):
                self._expr = self._expr[:m.start()] + digit
            else:
                self._expr += digit
        self._update_display()

    def _input_dot(self):
        if self._fresh:
            self._expr = "0."
            self._fresh = False
            self._update_display()
            return
        segment = self._expr[self._segment_start():]
        if "." in segment:
            return
        if self._expr in ("", "0"):
            self._expr = "0."
        elif not segment:
            self._expr += "0."
        else:
            self._expr += "."
        self._update_display()

    def _input_operator(self, op: str):
        if self._fresh:
            self._fresh = False
        if not self._expr:
            self._expr = "-" if op == "-" else "0"
            self._update_display()
            return
        last = self._expr[-1]
        if last in "+-*/^":
            if op == "-" and last != "-":
                self._expr += op
            else:
                self._expr = self._expr[:-1] + op
        elif last == "(":
            if op == "-":
                self._expr += op
        else:
            self._expr += op
        self._update_display()

    def _input_paren(self, p: str):
        if p == "(":
            if self._fresh or not self._expr or self._expr == "0":
                self._expr = "("
                self._fresh = False
            elif self._expr[-1] not in "+-*/^(":
                self._expr += "*("
            else:
                self._expr += "("
        else:
            opens = self._expr.count("(")
            closes = self._expr.count(")")
            if opens > closes and self._expr and self._expr[-1] not in "+-*/^(":
                self._expr += ")"
        self._update_display()

    def _input_sqrt(self):
        if self._fresh or not self._expr or self._expr == "0":
            self._expr = "√("
            self._fresh = False
        elif self._expr[-1] not in "+-*/^(":
            self._expr += "*√("
        else:
            self._expr += "√("
        self._update_display()

    def _eval_expr(self, expr_raw: str) -> float:
        opens = expr_raw.count("(")
        closes = expr_raw.count(")")
        balanced = expr_raw + (")" * max(0, opens - closes))
        py_expr = balanced.replace("√(", "sqrt(").replace("^", "**")
        return eval(py_expr, {"__builtins__": {}}, {"sqrt": math.sqrt})

    def _calculate(self):
        if not self._expr or self._fresh:
            return
        try:
            result = self._eval_expr(self._expr)
        except ZeroDivisionError:
            self._set_display("Cannot ÷ 0", self._expr)
            self._expr = "0"
            self._fresh = True
            return
        except Exception:
            self._set_display("Error", self._expr)
            self._expr = "0"
            self._fresh = True
            return

        formatted = self._format(result)
        plain_result = self._format_plain(result)
        self._add_history(self._expr, formatted, plain_result)
        self._set_display(formatted, self._expr + " =")
        self._expr = plain_result
        self._fresh = True

    def _clear_all(self):
        self._expr = "0"
        self._fresh = False
        self._set_display("0", "")

    def _backspace(self):
        if self._fresh:
            return
        if self._expr.endswith("√("):
            self._expr = self._expr[:-2]
        else:
            self._expr = self._expr[:-1]
        if not self._expr:
            self._expr = "0"
        self._update_display()

    def _toggle_sign(self):
        m = _NUM_RE.search(self._expr)
        if not m:
            return
        start = m.start()
        before = self._expr[:start]
        if before.endswith("-") and (len(before) == 1 or before[-2] in "+-*/^("):
            new_expr = before[:-1] + self._expr[start:]
        else:
            new_expr = before + "-" + self._expr[start:]
        self._expr = new_expr
        self._fresh = False
        self._update_display()

    def _percent(self):
        m = _NUM_RE.search(self._expr)
        if not m:
            return
        val = float(m.group(1)) / 100
        numeral = self._format_plain(val)
        self._expr = self._expr[:m.start()] + numeral + self._expr[m.end():]
        self._fresh = False
        self._update_display()

    # ── Memory logic ─────────────────────────────────────────────────────
    def _get_operand_value(self) -> float:
        m = _NUM_RE.search(self._expr)
        if m and m.end() == len(self._expr):
            return float(m.group(1))
        try:
            return self._eval_expr(self._expr)
        except Exception:
            return 0.0

    def _memory_op(self, op: str):
        val = self._get_operand_value()
        if op == "+":
            self._memory += val
        else:
            self._memory -= val

    def _recall_memory(self):
        val_str = self._format_plain(self._memory)
        m = _NUM_RE.search(self._expr)
        if m and m.end() == len(self._expr) and not self._fresh:
            self._expr = self._expr[:m.start()] + val_str
        elif self._fresh or self._expr in ("", "0"):
            self._expr = val_str
        else:
            self._expr += val_str
        self._fresh = False
        self._update_display()

    # ── History panel ─────────────────────────────────────────────────────
    def _add_history(self, expr_display: str, formatted_result: str, plain_result: str):
        item = QListWidgetItem(f"{expr_display} = {formatted_result}")
        item.setData(Qt.ItemDataRole.UserRole, plain_result)
        self.history_list.insertItem(0, item)
        while self.history_list.count() > 50:
            self.history_list.takeItem(self.history_list.count() - 1)

    def _on_history_clicked(self, item: QListWidgetItem):
        val = item.data(Qt.ItemDataRole.UserRole)
        self._expr = val
        self._fresh = False
        self._update_display()

    def _toggle_history(self):
        self.history_visible = not self.history_visible
        self.history_panel.setVisible(self.history_visible)
        self.hist_btn.setProperty("active", "true" if self.history_visible else "false")
        self.hist_btn.style().unpolish(self.hist_btn)
        self.hist_btn.style().polish(self.hist_btn)
        self._update_window_size()

    def _toggle_sci(self):
        self.sci_mode = not self.sci_mode
        self.sci_row.setVisible(self.sci_mode)
        self.sci_btn.setProperty("active", "true" if self.sci_mode else "false")
        self.sci_btn.style().unpolish(self.sci_btn)
        self.sci_btn.style().polish(self.sci_btn)
        self._update_window_size()

    def _copy_result(self):
        QApplication.clipboard().setText(self.result_label.text())

    # ── Keyboard support ──────────────────────────────────────────────────
    def keyPressEvent(self, event):
        key = event.key()
        text = event.text()

        if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self._calculate()
            return
        if key == Qt.Key.Key_Backspace:
            self._backspace()
            return
        if key == Qt.Key.Key_Escape:
            self._clear_all()
            return

        if text in "0123456789":
            self._input_digit(text)
        elif text == ".":
            self._input_dot()
        elif text == "=":
            self._calculate()
        elif text in "+-*/^":
            self._input_operator(text)
        elif text in "()":
            self._input_paren(text)
        elif text == "%":
            self._percent()
        else:
            super().keyPressEvent(event)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Midnight Calculator")
    app.setApplicationVersion(__version__)
    icon_path = Path(__file__).parent / "app_icon.ico"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))
    window = Calculator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
