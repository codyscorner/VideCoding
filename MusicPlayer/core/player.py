"""Audio playback wrapper around Qt Multimedia.

Owns a ``QMediaPlayer`` + ``QAudioOutput`` and re-exposes the handful of signals
and methods the UI needs, so the rest of the app never touches Qt Multimedia
directly.
"""

from __future__ import annotations

from PyQt6.QtCore import QObject, QUrl, pyqtSignal
from PyQt6.QtMultimedia import QAudioOutput, QMediaPlayer


class Player(QObject):
    positionChanged = pyqtSignal(int)   # current position, ms
    durationChanged = pyqtSignal(int)   # total duration, ms
    playingChanged = pyqtSignal(bool)   # True when actively playing
    trackEnded = pyqtSignal()           # media reached the end on its own
    errorOccurred = pyqtSignal(str)     # playback failed; arg is a description

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._player = QMediaPlayer(self)
        self._audio = QAudioOutput(self)
        self._player.setAudioOutput(self._audio)
        self._current_path = ""

        self._player.positionChanged.connect(lambda ms: self.positionChanged.emit(int(ms)))
        self._player.durationChanged.connect(lambda ms: self.durationChanged.emit(int(ms)))
        self._player.playbackStateChanged.connect(self._on_state_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status)
        self._player.errorOccurred.connect(self._on_error)

        self._audio.setVolume(0.8)

    # ------------------------------------------------------------- controls
    def play_file(self, path: str) -> None:
        """Load and immediately play the file at ``path``."""
        self._current_path = path
        self._player.setSource(QUrl.fromLocalFile(path))
        self._player.play()

    def toggle_pause(self) -> None:
        if self._player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self._player.pause()
        elif self._current_path:
            self._player.play()

    def stop(self) -> None:
        self._player.stop()

    def seek(self, position_ms: int) -> None:
        self._player.setPosition(position_ms)

    def seek_relative(self, delta_ms: int) -> None:
        """Jump forward/back by delta_ms, clamped to the track length."""
        if not self._current_path:
            return
        duration = self._player.duration()
        target = self._player.position() + delta_ms
        target = max(0, min(target, duration) if duration else max(0, target))
        self._player.setPosition(target)

    def set_volume(self, value_0_100: int) -> None:
        self._audio.setVolume(max(0.0, min(1.0, value_0_100 / 100.0)))

    # ------------------------------------------------------------- state
    @property
    def current_path(self) -> str:
        return self._current_path

    def is_playing(self) -> bool:
        return (
            self._player.playbackState()
            == QMediaPlayer.PlaybackState.PlayingState
        )

    # ------------------------------------------------------------- internal
    def _on_state_changed(self, state: QMediaPlayer.PlaybackState) -> None:
        self.playingChanged.emit(state == QMediaPlayer.PlaybackState.PlayingState)

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.trackEnded.emit()

    def _on_error(self, error: QMediaPlayer.Error, error_string: str = "") -> None:
        if error == QMediaPlayer.Error.NoError:
            return
        self.errorOccurred.emit(error_string or "Could not play this file")
