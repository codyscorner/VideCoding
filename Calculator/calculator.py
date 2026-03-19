"""
Calculator v1.0.0
Dark Blue / Midnight theme PyQt6 Calculator
"""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QGridLayout, QPushButton, QLabel
)
from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QFont

__version__ = "1.0.0"


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
    font-size: 42px;
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

/* ── Operator buttons (+, -, *, /) ── */
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

/* ── Zero button (wide) ── */
QPushButton#btn_zero {
    text-align: left;
    padding-left: 22px;
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
        self.setFixedSize(QSize(370, 580))

        # State
        self._expression = ""      # full expression string shown above result
        self._current = "0"        # number being typed
        self._result_shown = False # True after = is pressed
        self._memory = 0.0         # memory register

        self._build_ui()
        self._apply_style()

    # ── UI Construction ──────────────────────────────────────────────────
    def _build_ui(self):
        central = QWidget()
        central.setObjectName("container")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(10, 10, 10, 10)
        root.setSpacing(6)

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
        self.result_label.setFont(QFont("Segoe UI", 40, QFont.Weight.Bold))
        self.result_label.setMinimumHeight(70)

        disp_layout.addWidget(self.expr_label)
        disp_layout.addWidget(self.result_label)
        root.addWidget(display_widget)

        # Button area
        btn_area = QWidget()
        btn_area.setObjectName("button_area")
        grid = QGridLayout(btn_area)
        grid.setSpacing(8)

        # Memory row
        mem_buttons = [
            ("MC", 0, 0), ("MR", 0, 1), ("M-", 0, 2), ("M+", 0, 3),
        ]
        for label, row, col in mem_buttons:
            btn = self._make_button(label, "memory")
            grid.addWidget(btn, row, col)

        # Main button layout — row, col, rowspan, colspan
        main_buttons = [
            # label,      class,      row, col, rspan, cspan
            ("AC",        "function", 1,   0,   1,     1),
            ("+/-",       "function", 1,   1,   1,     1),
            ("%",         "function", 1,   2,   1,     1),
            ("/",         "operator", 1,   3,   1,     1),

            ("7",         "digit",    2,   0,   1,     1),
            ("8",         "digit",    2,   1,   1,     1),
            ("9",         "digit",    2,   2,   1,     1),
            ("*",         "operator", 2,   3,   1,     1),

            ("4",         "digit",    3,   0,   1,     1),
            ("5",         "digit",    3,   1,   1,     1),
            ("6",         "digit",    3,   2,   1,     1),
            ("-",         "operator", 3,   3,   1,     1),

            ("1",         "digit",    4,   0,   1,     1),
            ("2",         "digit",    4,   1,   1,     1),
            ("3",         "digit",    4,   2,   1,     1),
            ("+",         "operator", 4,   3,   1,     1),

            ("0",         "digit",    5,   0,   1,     2),
            (".",         "digit",    5,   2,   1,     1),
            ("=",         "equals",   5,   3,   1,     1),
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

        root.addWidget(btn_area)

    def _make_button(self, label: str, cls: str) -> QPushButton:
        """Create a styled button and connect it to the handler."""
        btn = QPushButton(label)
        btn.setProperty("btnClass", cls)
        # Connect all buttons to one dispatcher
        btn.clicked.connect(lambda _, l=label: self._on_button(l))
        return btn

    def _apply_style(self):
        QApplication.instance().setStyleSheet(QSS)

    # ── Display helpers ──────────────────────────────────────────────────
    def _set_display(self, value: str, expression: str = ""):
        self.result_label.setText(value)
        self.expr_label.setText(expression)

    def _format(self, value: float) -> str:
        """Return a clean string for a float — drop '.0' for integers."""
        if value == int(value) and abs(value) < 1e15:
            return f"{int(value):,}"
        return f"{value:,.10g}"

    # ── Button dispatcher ────────────────────────────────────────────────
    def _on_button(self, label: str):
        """Route button presses to the correct handler."""
        if label in "0123456789":
            self._input_digit(label)
        elif label == ".":
            self._input_dot()
        elif label in ("+", "-", "*", "/"):
            self._input_operator(label)
        elif label == "=":
            self._calculate()
        elif label == "AC":
            self._clear_all()
        elif label == "+/-":
            self._negate()
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
        if self._result_shown:
            self._current = digit
            self._expression = ""
            self._result_shown = False
        elif self._current == "0":
            self._current = digit
        else:
            if len(self._current) < 15:
                self._current += digit
        self._set_display(self._current, self._expression)

    def _input_dot(self):
        if self._result_shown:
            self._current = "0."
            self._expression = ""
            self._result_shown = False
        elif "." not in self._current:
            self._current += "."
        self._set_display(self._current, self._expression)

    def _input_operator(self, op: str):
        # If we have a pending expression, evaluate first
        if self._expression and not self._result_shown:
            self._calculate(chain=True)
        display_op = op
        self._expression = f"{self._current} {display_op}"
        self._current = "0"
        self._result_shown = False
        self._set_display(self._current, self._expression)

    def _calculate(self, chain: bool = False):
        if not self._expression:
            return
        try:
            expr = f"{self._expression} {self._current}"
            # Safe eval: only allow numbers and operators
            result = eval(expr)  # expression is fully controlled by our UI
        except ZeroDivisionError:
            self._set_display("Cannot ÷ 0", self._expression + " " + self._current)
            self._expression = ""
            self._current = "0"
            self._result_shown = True
            return
        except Exception:
            self._set_display("Error", "")
            self._expression = ""
            self._current = "0"
            self._result_shown = True
            return

        formatted = self._format(result)
        if chain:
            self._current = str(result)
        else:
            shown_expr = f"{self._expression} {self._current} ="
            self._set_display(formatted, shown_expr)
            self._current = str(result)
            self._result_shown = True
            self._expression = ""

    def _clear_all(self):
        self._expression = ""
        self._current = "0"
        self._result_shown = False
        self._set_display("0", "")

    def _negate(self):
        try:
            val = float(self._current)
            val = -val
            self._current = str(val) if val != int(val) else str(int(val))
            self._set_display(self._current, self._expression)
        except ValueError:
            pass

    def _percent(self):
        try:
            val = float(self._current) / 100
            self._current = str(val) if val != int(val) else str(int(val))
            self._set_display(self._current, self._expression)
        except ValueError:
            pass

    # ── Memory logic ─────────────────────────────────────────────────────
    def _memory_op(self, op: str):
        try:
            val = float(self._current)
            if op == "+":
                self._memory += val
            else:
                self._memory -= val
        except ValueError:
            pass

    def _recall_memory(self):
        self._current = str(self._memory) if self._memory != int(self._memory) else str(int(self._memory))
        self._result_shown = False
        self._set_display(self._current, self._expression)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("Midnight Calculator")
    app.setApplicationVersion(__version__)
    window = Calculator()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
