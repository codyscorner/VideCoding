"""Preview widget for one output file: image, video, text, or fallback note."""

from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QPixmap
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QScrollArea, QSlider,
    QVBoxLayout, QWidget,
)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".svg"}
VIDEO_EXTS = {".mp4", ".avi", ".mov", ".wmv", ".flv", ".webm", ".mkv"}
TEXT_EXTS = {".txt", ".md", ".json", ".xml", ".csv", ".log"}


class MediaViewer(QWidget):
    """Renders one file by extension. Recreated per file (cheap widgets)."""

    def __init__(self, file_path: str, prompt_type: str, parent: QWidget | None = None):
        super().__init__(parent)
        self._player: QMediaPlayer | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)

        path = Path(file_path)
        heading = QLabel(path.name)
        heading.setObjectName("sectionLabel")
        heading.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(heading)

        if not path.exists():
            layout.addWidget(self._note(f"File not found: {path.name}", warn=True))
            return

        ext = path.suffix.lower()
        if ext in IMAGE_EXTS:
            self._build_image(layout, path)
        elif ext in VIDEO_EXTS:
            self._build_video(layout, path)
        elif ext in TEXT_EXTS or prompt_type == "text":
            self._build_text(layout, path)
        else:
            size = path.stat().st_size
            layout.addWidget(self._note(
                f"File type not supported for preview. File size: {size} bytes",
                warn=True,
            ))
        layout.addStretch()

    @staticmethod
    def _note(text: str, warn: bool = False) -> QLabel:
        label = QLabel(text)
        label.setObjectName("warnNote" if warn else "infoNote")
        label.setWordWrap(True)
        return label

    # ---- image -----------------------------------------------------------

    def _build_image(self, layout: QVBoxLayout, path: Path) -> None:
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            layout.addWidget(self._note("Could not load image.", warn=True))
            return

        self._pixmap = pixmap
        self._img_label = QLabel()
        self._img_label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        self._img_label.setStyleSheet(
            "border: 1px solid #2a4a6e; border-radius: 4px; background: #0f1e30;"
        )

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self._img_label)
        layout.addWidget(scroll, stretch=1)

        dims = QLabel(f"{pixmap.width()} × {pixmap.height()}")
        dims.setObjectName("dimLabel")
        dims.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(dims)
        self._rescale_image()

    def _rescale_image(self) -> None:
        if not hasattr(self, "_pixmap"):
            return
        avail = max(self.width() - 40, 100)
        if self._pixmap.width() > avail:
            scaled = self._pixmap.scaledToWidth(
                avail, Qt.TransformationMode.SmoothTransformation
            )
        else:
            scaled = self._pixmap
        self._img_label.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_image()

    # ---- video -----------------------------------------------------------

    def _build_video(self, layout: QVBoxLayout, path: Path) -> None:
        video_widget = QVideoWidget()
        video_widget.setMinimumHeight(320)
        layout.addWidget(video_widget, stretch=1)

        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(video_widget)
        self._player.setSource(QUrl.fromLocalFile(str(path)))

        controls = QHBoxLayout()
        self._play_btn = QPushButton("▶ Play")
        self._play_btn.setFixedWidth(90)
        self._play_btn.clicked.connect(self._toggle_play)
        controls.addWidget(self._play_btn)

        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.sliderMoved.connect(self._player.setPosition)
        controls.addWidget(self._seek, stretch=1)

        self._time_label = QLabel("0:00 / 0:00")
        self._time_label.setObjectName("dimLabel")
        controls.addWidget(self._time_label)
        layout.addLayout(controls)

        self._player.durationChanged.connect(self._on_duration)
        self._player.positionChanged.connect(self._on_position)
        self._player.playbackStateChanged.connect(self._on_state)

    def _toggle_play(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _on_state(self, state) -> None:
        playing = state == QMediaPlayer.PlaybackState.PlayingState
        self._play_btn.setText("⏸ Pause" if playing else "▶ Play")

    def _on_duration(self, duration: int) -> None:
        self._seek.setRange(0, duration)
        self._update_time_label(self._player.position(), duration)

    def _on_position(self, position: int) -> None:
        if not self._seek.isSliderDown():
            self._seek.setValue(position)
        self._update_time_label(position, self._player.duration())

    def _update_time_label(self, pos_ms: int, dur_ms: int) -> None:
        self._time_label.setText(f"{_fmt_ms(pos_ms)} / {_fmt_ms(dur_ms)}")

    def stop_playback(self) -> None:
        """Called before the viewer is torn down so audio doesn't linger."""
        if self._player is not None:
            self._player.stop()

    # ---- text ------------------------------------------------------------

    def _build_text(self, layout: QVBoxLayout, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            layout.addWidget(self._note(f"Could not read file: {exc}", warn=True))
            return
        if not content:
            layout.addWidget(self._note("No content available"))
            return
        box = QPlainTextEdit(content)
        box.setObjectName("promptBox")
        box.setReadOnly(True)
        layout.addWidget(box, stretch=1)


def _fmt_ms(ms: int) -> str:
    seconds = max(ms, 0) // 1000
    return f"{seconds // 60}:{seconds % 60:02d}"
