from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QPushButton, QApplication, QSizePolicy,
)
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSlot
from PyQt6.QtGui import QPixmap, QKeyEvent
from PyQt6.QtWidgets import QGraphicsOpacityEffect
from typing import List

class SlideshowWindow(QWidget):
    def __init__(
        self,
        image_paths: List[str],
        start_index: int = 0,
        delay_seconds: float = 3.0,
        fade_seconds: float = 0.5,
        parent=None,
    ):
        super().__init__(parent)
        self._paths = image_paths
        self._index = max(0, min(start_index, len(image_paths) - 1))
        self._delay_ms = int(delay_seconds * 1000)
        self._fade_out_ms = int(fade_seconds * 400)   # 40% of fade time for out
        self._fade_in_ms  = int(fade_seconds * 600)   # 60% of fade time for in
        self._paused = False
        self._next_index: int | None = None   # queued during animation
        self._animating = False

        self._build_ui()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._advance)

        self.showFullScreen()
        # First image appears instantly (fade in from black)
        self._load_image(self._index)
        self._fade_in()
        self._timer.start(self._delay_ms)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        self.setWindowTitle("Slideshow")
        self.setStyleSheet("background-color: black;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._image_label = QLabel()
        self._image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._image_label.setStyleSheet("background-color: black;")
        self._image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        layout.addWidget(self._image_label, stretch=1)

        # Opacity effect attached to the image label for fade animation
        self._opacity = QGraphicsOpacityEffect(self._image_label)
        self._opacity.setOpacity(0.0)
        self._image_label.setGraphicsEffect(self._opacity)

        self._control_bar = QWidget()
        self._control_bar.setStyleSheet(
            "background-color: rgba(0, 0, 0, 180); padding: 4px;"
        )
        ctrl = QHBoxLayout(self._control_bar)
        ctrl.setContentsMargins(16, 4, 16, 4)
        ctrl.setSpacing(8)

        btn_style = (
            "QPushButton { background-color: rgba(13,148,136,200); color: white; "
            "font-weight: bold; border: none; border-radius: 4px; padding: 6px 16px; } "
            "QPushButton:hover { background-color: rgba(20,184,166,220); } "
            "QPushButton:pressed { background-color: rgba(15,118,110,220); }"
        )

        self._prev_btn = QPushButton("◀  Prev")
        self._prev_btn.setStyleSheet(btn_style)
        self._prev_btn.clicked.connect(self._go_prev)

        self._pause_btn = QPushButton("⏸  Pause")
        self._pause_btn.setStyleSheet(btn_style)
        self._pause_btn.clicked.connect(self._toggle_pause)

        self._next_btn = QPushButton("Next  ▶")
        self._next_btn.setStyleSheet(btn_style)
        self._next_btn.clicked.connect(self._go_next)

        self._info_label = QLabel()
        self._info_label.setStyleSheet("color: #94a3b8; font-size: 10pt; background: transparent;")

        ctrl.addWidget(self._prev_btn)
        ctrl.addWidget(self._pause_btn)
        ctrl.addWidget(self._next_btn)
        ctrl.addStretch()
        ctrl.addWidget(self._info_label)

        layout.addWidget(self._control_bar)

    # ── Image loading ─────────────────────────────────────────────────────────

    def _load_image(self, index: int) -> None:
        """Load and display the image at index with no animation."""
        path = self._paths[index]
        pixmap = QPixmap(path)
        if not pixmap.isNull():
            screen = QApplication.primaryScreen().size()
            scaled = pixmap.scaled(
                screen,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._image_label.setPixmap(scaled)
        else:
            self._image_label.clear()
            self._image_label.setText("Cannot load image")
        self._info_label.setText(f"{index + 1} / {len(self._paths)}")

    # ── Fade helpers ──────────────────────────────────────────────────────────

    def _fade_in(self) -> None:
        self._animating = True
        if self._fade_in_ms == 0:
            self._opacity.setOpacity(1.0)
            self._on_fade_in_done()
            return
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(self._fade_in_ms)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.finished.connect(self._on_fade_in_done)
        self._anim = anim
        anim.start()

    def _fade_out_then(self, next_index: int) -> None:
        """Fade out the current image, then load next_index and fade in."""
        if self._animating:
            self._next_index = next_index
            return
        self._next_index = next_index
        self._animating = True
        if self._fade_out_ms == 0:
            self._opacity.setOpacity(0.0)
            self._on_fade_out_done()
            return
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(self._fade_out_ms)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)
        anim.finished.connect(self._on_fade_out_done)
        self._anim = anim
        anim.start()

    @pyqtSlot()
    def _on_fade_out_done(self) -> None:
        if self._next_index is not None:
            self._index = self._next_index
            self._next_index = None
        self._load_image(self._index)
        self._fade_in()

    @pyqtSlot()
    def _on_fade_in_done(self) -> None:
        self._animating = False
        # If another transition was queued while we were fading in, run it now
        if self._next_index is not None:
            idx = self._next_index
            self._next_index = None
            self._fade_out_then(idx)

    # ── Navigation ────────────────────────────────────────────────────────────

    @pyqtSlot()
    def _advance(self) -> None:
        next_idx = (self._index + 1) % len(self._paths)
        self._fade_out_then(next_idx)

    @pyqtSlot()
    def _go_prev(self) -> None:
        self._timer.stop()
        next_idx = (self._index - 1) % len(self._paths)
        self._fade_out_then(next_idx)
        if not self._paused:
            self._timer.start(self._delay_ms)

    @pyqtSlot()
    def _go_next(self) -> None:
        self._timer.stop()
        next_idx = (self._index + 1) % len(self._paths)
        self._fade_out_then(next_idx)
        if not self._paused:
            self._timer.start(self._delay_ms)

    @pyqtSlot()
    def _toggle_pause(self) -> None:
        self._paused = not self._paused
        if self._paused:
            self._timer.stop()
            self._pause_btn.setText("▶  Play")
        else:
            self._pause_btn.setText("⏸  Pause")
            self._timer.start(self._delay_ms)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if key == Qt.Key.Key_Escape:
            self._timer.stop()
            self.close()
        elif key == Qt.Key.Key_Left:
            self._go_prev()
        elif key == Qt.Key.Key_Right:
            self._go_next()
        elif key == Qt.Key.Key_Space:
            self._toggle_pause()
        else:
            super().keyPressEvent(event)
