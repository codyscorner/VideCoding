"""Five-star rating widget: clickable or read-only, small/medium sizes."""

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QWidget

from ui.theme import STAR_EMPTY, STAR_FILLED

_SIZES = {"small": 12, "medium": 16, "large": 20}


class StarRating(QWidget):
    """Shows rating 0-5; clicking star N emits ratingChanged(N) unless readonly.

    Parity with v1.x: no click-to-clear — rating 0 only via default/filter.
    """

    ratingChanged = pyqtSignal(int)

    def __init__(self, rating: int = 0, readonly: bool = False,
                 size: str = "medium", parent: QWidget | None = None):
        super().__init__(parent)
        self._rating = rating
        self._readonly = readonly
        px = _SIZES.get(size, 16)
        self._base_style = f"font-size: {px}pt; background: transparent;"

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(1)

        self._stars: list[QLabel] = []
        for i in range(1, 6):
            star = QLabel("★")
            if not readonly:
                star.setCursor(Qt.CursorShape.PointingHandCursor)
                star.mousePressEvent = self._click_handler(i)
            layout.addWidget(star)
            self._stars.append(star)
        layout.addStretch()
        self._refresh()

    def _click_handler(self, value: int):
        def handler(_event):
            if not self._readonly:
                self.set_rating(value)
                self.ratingChanged.emit(value)
        return handler

    def rating(self) -> int:
        return self._rating

    def set_rating(self, rating: int) -> None:
        self._rating = rating
        self._refresh()

    def _refresh(self) -> None:
        for i, star in enumerate(self._stars, start=1):
            color = STAR_FILLED if i <= self._rating else STAR_EMPTY
            star.setStyleSheet(f"{self._base_style} color: {color};")
