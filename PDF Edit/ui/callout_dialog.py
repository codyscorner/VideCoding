"""Shared dialog for text annotations (Text Box and Callout):
text, font family, bold, font size, text color, background color."""

from PyQt6.QtGui import QColor, QIcon, QPixmap
from PyQt6.QtWidgets import (QCheckBox, QColorDialog, QComboBox, QDialog,
                             QDialogButtonBox, QFormLayout, QHBoxLayout,
                             QPlainTextEdit, QPushButton, QSpinBox,
                             QVBoxLayout)

# (family label, regular fontname, bold fontname) — PDF base-14 fonts
FONTS = [("Helvetica", "helv", "hebo"),
         ("Times", "tiro", "tibo"),
         ("Courier", "cour", "cobo")]


class TextAnnotDialog(QDialog):
    # remembered across invocations
    last_fill = QColor("#fff2a8")
    last_text = QColor("#1a1a1a")
    last_fontsize = 14
    last_font_index = 0
    last_bold = False

    def __init__(self, parent=None, title="Callout"):
        super().__init__(parent)
        self.setWindowTitle(title)
        cls = TextAnnotDialog
        self.fill_color = QColor(cls.last_fill)
        self.text_color = QColor(cls.last_text)

        self.edit = QPlainTextEdit()
        self.edit.setPlaceholderText("Text…")
        self.edit.setMinimumSize(340, 110)

        self.font_combo = QComboBox()
        self.font_combo.addItems([f[0] for f in FONTS])
        self.font_combo.setCurrentIndex(cls.last_font_index)
        self.bold_check = QCheckBox("Bold")
        self.bold_check.setChecked(cls.last_bold)
        self.size_spin = QSpinBox()
        self.size_spin.setRange(6, 96)
        self.size_spin.setValue(cls.last_fontsize)

        font_row = QHBoxLayout()
        font_row.addWidget(self.font_combo, 1)
        font_row.addWidget(self.bold_check)
        font_row.addWidget(self.size_spin)

        self.text_btn = QPushButton("Text color")
        self.text_btn.clicked.connect(lambda: self._pick("text"))
        self.fill_btn = QPushButton("Background color")
        self.fill_btn.clicked.connect(lambda: self._pick("fill"))

        form = QFormLayout()
        form.addRow("Font:", font_row)
        form.addRow("Text color:", self.text_btn)
        form.addRow("Background:", self.fill_btn)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok
                                   | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        lay = QVBoxLayout(self)
        lay.addWidget(self.edit)
        lay.addLayout(form)
        lay.addWidget(buttons)
        self._swatches()
        self.edit.setFocus()

    def _swatches(self):
        for btn, color in ((self.fill_btn, self.fill_color),
                           (self.text_btn, self.text_color)):
            pm = QPixmap(16, 16)
            pm.fill(color)
            btn.setIcon(QIcon(pm))

    def _pick(self, which: str):
        current = self.fill_color if which == "fill" else self.text_color
        c = QColorDialog.getColor(current, self, "Choose color")
        if c.isValid():
            if which == "fill":
                self.fill_color = c
            else:
                self.text_color = c
            self._swatches()

    def accept(self):
        cls = TextAnnotDialog
        cls.last_fill = QColor(self.fill_color)
        cls.last_text = QColor(self.text_color)
        cls.last_fontsize = self.size_spin.value()
        cls.last_font_index = self.font_combo.currentIndex()
        cls.last_bold = self.bold_check.isChecked()
        super().accept()

    @property
    def text(self) -> str:
        return self.edit.toPlainText().strip()

    @property
    def fontsize(self) -> int:
        return self.size_spin.value()

    @property
    def fontname(self) -> str:
        _, regular, bold = FONTS[self.font_combo.currentIndex()]
        return bold if self.bold_check.isChecked() else regular

    def rgb_text(self) -> tuple:
        c = self.text_color
        return (c.redF(), c.greenF(), c.blueF())

    def rgb_fill(self) -> tuple:
        c = self.fill_color
        return (c.redF(), c.greenF(), c.blueF())


# backward-compatible alias
CalloutDialog = TextAnnotDialog
