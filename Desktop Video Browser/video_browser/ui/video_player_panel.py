from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QUrl, QEvent, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtMultimediaWidgets import QVideoWidget


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


class VideoPlayerPanel(QWidget):
    navigateRequested = Signal(int)  # +1 = next, -1 = previous

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Video widget ---
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #000;")
        self.video_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.video_widget.installEventFilter(self)
        layout.addWidget(self.video_widget)

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(6, 4, 6, 4)
        toolbar.setSpacing(6)

        self.play_pause_btn = QPushButton("▶")
        self.play_pause_btn.setFixedWidth(36)
        self.play_pause_btn.clicked.connect(self.toggle_play_pause)
        toolbar.addWidget(self.play_pause_btn)

        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedWidth(36)
        self.stop_btn.clicked.connect(self._stop)
        toolbar.addWidget(self.stop_btn)

        self.fullscreen_btn = QPushButton("⛶")
        self.fullscreen_btn.setFixedWidth(36)
        self.fullscreen_btn.clicked.connect(self.toggle_fullscreen)
        toolbar.addWidget(self.fullscreen_btn)

        toolbar.addStretch()

        self.time_label = QLabel("0:00 / 0:00")
        self.time_label.setStyleSheet("color: #ccc; font-size: 12px;")
        toolbar.addWidget(self.time_label)

        toolbar_widget = QWidget()
        toolbar_widget.setLayout(toolbar)
        toolbar_widget.setStyleSheet("background-color: #1e1e1e;")
        layout.addWidget(toolbar_widget)

        # --- Error label ---
        self.error_label = QLabel()
        self.error_label.setAlignment(Qt.AlignCenter)
        self.error_label.setStyleSheet("color: #f88; padding: 4px;")
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

        # --- Player ---
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.player.setVideoOutput(self.video_widget)
        self.player.errorOccurred.connect(self._on_error)
        self.player.playbackStateChanged.connect(self._on_playback_state_changed)
        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)

        self._duration_ms = 0

        # --- Keyboard shortcuts ---
        QShortcut(QKeySequence(Qt.Key_Space), self, self.toggle_play_pause)
        QShortcut(QKeySequence(Qt.Key_F), self, self.toggle_fullscreen)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def release(self) -> None:
        self.player.stop()
        self.player.setSource(QUrl())
        self._duration_ms = 0
        self.time_label.setText("0:00 / 0:00")

    def load_video(self, path: str) -> None:
        self.error_label.setVisible(False)
        self.player.stop()
        self.player.setSource(QUrl.fromLocalFile(path))
        self.player.play()

    def toggle_play_pause(self) -> None:
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def toggle_fullscreen(self) -> None:
        self.video_widget.setFullScreen(not self.video_widget.isFullScreen())

    def eventFilter(self, obj, event) -> bool:
        if obj is self.video_widget and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key_Escape or key == Qt.Key_F:
                if self.video_widget.isFullScreen():
                    self.video_widget.setFullScreen(False)
                    return True
            if key == Qt.Key_Space:
                self.toggle_play_pause()
                return True
            if key == Qt.Key_Down:
                self.navigateRequested.emit(1)
                return True
            if key == Qt.Key_Up:
                self.navigateRequested.emit(-1)
                return True
        return super().eventFilter(obj, event)

    # ------------------------------------------------------------------
    # Private slots
    # ------------------------------------------------------------------

    def _stop(self) -> None:
        self.player.stop()

    def _on_playback_state_changed(self, state) -> None:
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.play_pause_btn.setText("⏸")
        else:
            self.play_pause_btn.setText("▶")

    def _on_position_changed(self, position_ms: int) -> None:
        self.time_label.setText(f"{_ms_to_str(position_ms)} / {_ms_to_str(self._duration_ms)}")

    def _on_duration_changed(self, duration_ms: int) -> None:
        self._duration_ms = duration_ms
        self.time_label.setText(f"0:00 / {_ms_to_str(duration_ms)}")

    def _on_error(self, error, error_string: str) -> None:
        self.error_label.setText(f"Cannot play file: {error_string}")
        self.error_label.setVisible(True)
