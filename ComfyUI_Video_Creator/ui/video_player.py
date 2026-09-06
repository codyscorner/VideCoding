from pathlib import Path

from PyQt6.QtCore import QEvent, Qt, QTimer, QUrl, pyqtSignal
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtWidgets import QDialog, QHBoxLayout, QLabel, QPushButton, QSlider, QVBoxLayout, QWidget

from ui.styles import COLORS


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02}:{s:02}" if h else f"{m}:{s:02}"


class VideoPlayerDialog(QDialog):
    closed = pyqtSignal()

    def __init__(self, video_path: str, parent=None, playlist: list[str] | None = None,
                 auto_close: bool = False):
        super().__init__(parent)
        # Closing must destroy the window, not hide it: a hidden dialog keeps
        # its QMediaPlayer, and on Windows that keeps the video file open.
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)
        self._released = False
        # auto_close: shut the window when the last video finishes (Library
        # playback) instead of sitting on the final frame until dismissed.
        self._auto_close = auto_close
        self._playlist = playlist if playlist else [video_path]
        self._index = self._playlist.index(video_path) if video_path in self._playlist else 0

        self.setMinimumSize(900, 560)
        self.resize(1100, 680)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.WindowCloseButtonHint)
        self.setStyleSheet(f"""
            QDialog, QWidget {{ background-color: #000000; color: {COLORS['fg_primary']}; font-family: "Segoe UI"; }}
            QPushButton {{ background-color: {COLORS['accent']}; color: white; font-weight: bold; border: none;
                           border-radius: 4px; padding: 6px 16px; font-size: 10pt; }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
            QPushButton:disabled {{ background-color: {COLORS['bg_light']}; color: {COLORS['fg_dim']}; }}
            QSlider::groove:horizontal {{ background: {COLORS['bg_light']}; height: 4px; border-radius: 2px; }}
            QSlider::handle:horizontal {{ background: {COLORS['accent_hover']}; width: 14px; height: 14px;
                                          margin: -5px 0; border-radius: 7px; }}
            QSlider::sub-page:horizontal {{ background: {COLORS['accent']}; border-radius: 2px; }}
            QLabel {{ background: transparent; color: {COLORS['fg_secondary']}; font-size: 9pt; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._video_widget = QVideoWidget()
        self._video_widget.installEventFilter(self)
        layout.addWidget(self._video_widget, stretch=1)

        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 0)
        self._seek.sliderMoved.connect(lambda pos: self._player.setPosition(pos))
        layout.addWidget(self._seek)

        bar_w = QWidget()
        bar_w.setStyleSheet(f"background-color: {COLORS['bg_medium']};")
        bar = QHBoxLayout(bar_w)
        bar.setContentsMargins(10, 6, 10, 6)
        bar.setSpacing(8)

        self._play_btn = QPushButton("⏸")
        self._play_btn.setFixedWidth(42)
        self._play_btn.clicked.connect(self._toggle_play)
        bar.addWidget(self._play_btn)
        stop_btn = QPushButton("■")
        stop_btn.setFixedWidth(42)
        stop_btn.clicked.connect(lambda: self._player.stop())
        bar.addWidget(stop_btn)
        fs_btn = QPushButton("⛶")
        fs_btn.setFixedWidth(42)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        bar.addWidget(fs_btn)
        self._prev_btn = QPushButton("⏮")
        self._prev_btn.setFixedWidth(42)
        self._prev_btn.clicked.connect(self._prev)
        bar.addWidget(self._prev_btn)
        self._next_btn = QPushButton("⏭")
        self._next_btn.setFixedWidth(42)
        self._next_btn.clicked.connect(self._next)
        bar.addWidget(self._next_btn)
        if len(self._playlist) <= 1:
            self._prev_btn.setVisible(False)
            self._next_btn.setVisible(False)
        bar.addStretch()
        self._track_label = QLabel("")
        bar.addWidget(self._track_label)
        self._time_label = QLabel("0:00 / 0:00")
        bar.addWidget(self._time_label)
        bar.addStretch()
        close_btn = QPushButton("✕ Close")
        close_btn.clicked.connect(self.close)
        bar.addWidget(close_btn)
        layout.addWidget(bar_w)

        self._audio = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.errorOccurred.connect(lambda _e, s: self._time_label.setText(f"Error: {s}"))
        self._player.playbackStateChanged.connect(self._on_state)
        self._player.positionChanged.connect(self._on_position)
        self._player.durationChanged.connect(self._on_duration)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._duration_ms = 0

        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_play)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self._toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)
        QShortcut(QKeySequence(Qt.Key.Key_Left), self, self._prev)
        QShortcut(QKeySequence(Qt.Key.Key_Right), self, self._next)

        self._load_current()

    def _load_current(self):
        path = self._playlist[self._index]
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()
        n = len(self._playlist)
        if n > 1:
            self._track_label.setText(f"{self._index + 1}/{n}  ")
            self.setWindowTitle(f"{self._index + 1}/{n} — {Path(path).name}")
        else:
            self._track_label.setText("")
            self.setWindowTitle(Path(path).name)
        self._prev_btn.setEnabled(self._index > 0)
        self._next_btn.setEnabled(self._index < n - 1)

    def _prev(self):
        if self._index > 0:
            self._index -= 1
            self._load_current()

    def _next(self):
        if self._index < len(self._playlist) - 1:
            self._index += 1
            self._load_current()

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _toggle_fullscreen(self):
        self._video_widget.setFullScreen(not self._video_widget.isFullScreen())

    def _on_state(self, state):
        self._play_btn.setText("⏸" if state == QMediaPlayer.PlaybackState.PlayingState else "▶")

    def _on_position(self, ms: int):
        self._seek.setValue(ms)
        self._time_label.setText(f"{_ms_to_str(ms)} / {_ms_to_str(self._duration_ms)}")

    def _on_duration(self, ms: int):
        self._duration_ms = ms
        self._seek.setRange(0, ms)
        self._time_label.setText(f"0:00 / {_ms_to_str(ms)}")

    def _on_media_status(self, status):
        if status != QMediaPlayer.MediaStatus.EndOfMedia:
            return
        if self._index < len(self._playlist) - 1:
            self._index += 1
            QTimer.singleShot(0, self._load_current)
        elif self._auto_close:
            QTimer.singleShot(0, self.close)

    def eventFilter(self, obj, event):
        if obj is self._video_widget and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Escape, Qt.Key.Key_F) and self._video_widget.isFullScreen():
                self._video_widget.setFullScreen(False)
                return True
            if key == Qt.Key.Key_Space:
                self._toggle_play()
                return True
        return super().eventFilter(obj, event)

    def holds(self, paths) -> bool:
        """True if any of `paths` is in this player's playlist."""
        mine = {str(Path(p)) for p in self._playlist}
        return any(str(Path(p)) in mine for p in paths)

    def release(self):
        """Let go of the video file.

        stop() is not enough on Windows: the Media Foundation backend keeps
        the file handle until the source is cleared or the player destroyed,
        and a locked file can't be deleted. Clear the source, detach the
        outputs, and schedule the player for destruction."""
        if self._released:
            return
        self._released = True
        try:
            self._player.stop()
            self._player.setSource(QUrl())
            self._player.setVideoOutput(None)
            self._player.setAudioOutput(None)
        except RuntimeError:
            pass
        self._player.deleteLater()
        self._audio.deleteLater()

    def closeEvent(self, event):
        self.release()
        self.closed.emit()
        event.accept()
