from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QSlider,
)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import Qt, QUrl, QEvent
from PyQt6.QtGui import QKeySequence, QShortcut

from ui.styles import COLORS


def _ms_to_str(ms: int) -> str:
    s = ms // 1000
    m, s = divmod(s, 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}:{m:02}:{s:02}"
    return f"{m}:{s:02}"


class VideoPlayerDialog(QDialog):
    def __init__(self, video_path: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(Path(video_path).name)
        self.setMinimumSize(900, 560)
        self.resize(1000, 620)
        self.setWindowFlags(
            Qt.WindowType.Dialog |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        self.setStyleSheet(f"""
            QDialog, QWidget {{
                background-color: #000000;
                color: {COLORS['fg_primary']};
                font-family: "Segoe UI";
            }}
            QPushButton {{
                background-color: {COLORS['accent']};
                color: white;
                font-weight: bold;
                border: none;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 10pt;
            }}
            QPushButton:hover {{ background-color: {COLORS['accent_hover']}; }}
            QSlider::groove:horizontal {{
                background: {COLORS['bg_light']};
                height: 4px;
                border-radius: 2px;
            }}
            QSlider::handle:horizontal {{
                background: {COLORS['accent_hover']};
                width: 14px;
                height: 14px;
                margin: -5px 0;
                border-radius: 7px;
            }}
            QSlider::sub-page:horizontal {{
                background: {COLORS['accent']};
                border-radius: 2px;
            }}
            QLabel {{ background: transparent; color: {COLORS['fg_secondary']}; font-size: 9pt; }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Video surface
        self._video_widget = QVideoWidget()
        self._video_widget.setStyleSheet("background-color: #000;")
        self._video_widget.installEventFilter(self)
        layout.addWidget(self._video_widget, stretch=1)

        # Seek bar
        self._seek = QSlider(Qt.Orientation.Horizontal)
        self._seek.setRange(0, 0)
        self._seek.setContentsMargins(8, 0, 8, 0)
        self._seek.sliderMoved.connect(self._on_seek)
        layout.addWidget(self._seek)

        # Toolbar
        toolbar_widget = QWidget()
        toolbar_widget.setStyleSheet(f"background-color: {COLORS['bg_medium']};")
        toolbar = QHBoxLayout(toolbar_widget)
        toolbar.setContentsMargins(10, 6, 10, 6)
        toolbar.setSpacing(8)

        self._play_btn = QPushButton("⏸")
        self._play_btn.setFixedWidth(42)
        self._play_btn.clicked.connect(self._toggle_play)
        toolbar.addWidget(self._play_btn)

        self._stop_btn = QPushButton("■")
        self._stop_btn.setFixedWidth(42)
        self._stop_btn.clicked.connect(self._stop)
        toolbar.addWidget(self._stop_btn)

        self._fullscreen_btn = QPushButton("⛶")
        self._fullscreen_btn.setFixedWidth(42)
        self._fullscreen_btn.clicked.connect(self._toggle_fullscreen)
        toolbar.addWidget(self._fullscreen_btn)

        toolbar.addStretch()

        self._time_label = QLabel("0:00 / 0:00")
        toolbar.addWidget(self._time_label)

        toolbar.addStretch()

        close_btn = QPushButton("✕ Close")
        close_btn.setFixedWidth(90)
        close_btn.clicked.connect(self.close)
        toolbar.addWidget(close_btn)

        layout.addWidget(toolbar_widget)

        # Player
        self._audio = QAudioOutput()
        self._player = QMediaPlayer()
        self._player.setAudioOutput(self._audio)
        self._player.setVideoOutput(self._video_widget)
        self._player.errorOccurred.connect(self._on_error)
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._duration_ms = 0

        # Keyboard shortcuts
        QShortcut(QKeySequence(Qt.Key.Key_Space), self, self._toggle_play)
        QShortcut(QKeySequence(Qt.Key.Key_F), self, self._toggle_fullscreen)
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, self.close)

        self._player.setSource(QUrl.fromLocalFile(video_path))
        self._player.play()

    def _toggle_play(self):
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        else:
            self._player.play()

    def _stop(self):
        self._player.stop()

    def _toggle_fullscreen(self):
        self._video_widget.setFullScreen(not self._video_widget.isFullScreen())

    def _on_seek(self, position):
        self._player.setPosition(position)

    def _on_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self._play_btn.setText("⏸")
        else:
            self._play_btn.setText("▶")

    def _on_position_changed(self, ms: int):
        self._seek.setValue(ms)
        self._time_label.setText(f"{_ms_to_str(ms)} / {_ms_to_str(self._duration_ms)}")

    def _on_duration_changed(self, ms: int):
        self._duration_ms = ms
        self._seek.setRange(0, ms)
        self._time_label.setText(f"0:00 / {_ms_to_str(ms)}")

    def _on_error(self, error, error_string: str):
        self._time_label.setText(f"Error: {error_string}")

    def eventFilter(self, obj, event):
        if obj is self._video_widget and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key in (Qt.Key.Key_Escape, Qt.Key.Key_F):
                if self._video_widget.isFullScreen():
                    self._video_widget.setFullScreen(False)
                    return True
            if key == Qt.Key.Key_Space:
                self._toggle_play()
                return True
        return super().eventFilter(obj, event)

    def closeEvent(self, event):
        self._player.stop()
        event.accept()
