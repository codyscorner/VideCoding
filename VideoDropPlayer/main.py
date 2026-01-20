"""
Video Drop Player - A simple drag-and-drop video player
Supports MP4 and other common video formats
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QStackedLayout
)
from PyQt6.QtCore import Qt, QUrl, QEventLoop, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

# Windows dark title bar support
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes

    def set_dark_title_bar(hwnd, color):
        """Set dark title bar color on Windows."""
        DWMWA_CAPTION_COLOR = 35
        ctypes.windll.dwmapi.DwmSetWindowAttribute(
            hwnd,
            DWMWA_CAPTION_COLOR,
            ctypes.byref(ctypes.c_int(color)),
            ctypes.sizeof(ctypes.c_int)
        )


class DropOverlay(QWidget):
    """Transparent overlay widget that captures drag and drop events."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.parent_player = parent
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet("background: transparent;")

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and self.parent_player.is_supported_video(urls[0].toLocalFile()):
                event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move events."""
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        urls = event.mimeData().urls()
        if urls:
            # Collect all supported video files
            video_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if self.parent_player.is_supported_video(file_path):
                    video_files.append(file_path)

            if video_files:
                # Build playlist and start playing
                self.parent_player.build_playlist(video_files)
                if self.parent_player.playlist:
                    self.parent_player.play_current()
                event.acceptProposedAction()


def get_icon_path():
    """Get the path to the app icon."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(os.path.dirname(sys.executable), 'app_icon.ico')
    else:
        # Running as script
        return os.path.join(os.path.dirname(__file__), 'app_icon.ico')


class VideoDropPlayer(QMainWindow):
    """Main window for the video drop player application."""

    VERSION = "1.1.0"
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION}")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(400, 300)

        # Playlist state
        self.playlist = []  # List of (file_path, duration_ms) tuples
        self.current_index = 0

        # Set window icon
        icon_path = get_icon_path()
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # Enable drag and drop on main window
        self.setAcceptDrops(True)

        # Create central widget with stacked layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.stacked_layout = QStackedLayout(self.central_widget)
        self.stacked_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        self.stacked_layout.setContentsMargins(0, 0, 0, 0)

        # Create video widget (bottom layer)
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: #0a1628;")

        # Create drop overlay (top layer - always captures drops)
        self.drop_overlay = DropOverlay(self)

        # Create drop hint label (shown when no video is playing)
        self.drop_label = QLabel("Drag and drop a video file here")
        self.drop_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drop_label.setStyleSheet("""
            QLabel {
                color: #7799cc;
                font-size: 18px;
                background-color: #0d1a2d;
                border: 2px dashed #2a4a6d;
                border-radius: 10px;
                padding: 50px;
            }
        """)

        # Add widgets to stacked layout (order matters: bottom to top)
        self.stacked_layout.addWidget(self.video_widget)
        self.stacked_layout.addWidget(self.drop_label)
        self.stacked_layout.addWidget(self.drop_overlay)

        # Initially show label on top
        self.drop_label.show()
        self.video_widget.hide()

        # Set up media player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect signals
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_error)

        # Set window style - dark blue theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a1628;
            }
        """)

        # Apply dark blue title bar on Windows
        if sys.platform == 'win32':
            # Color format is BGR (0x00BBGGRR)
            # #0a1628 -> R=0x0a, G=0x16, B=0x28 -> BGR = 0x28160a
            self._apply_title_bar_color()

    def _apply_title_bar_color(self):
        """Apply dark blue color to Windows title bar."""
        if sys.platform == 'win32':
            hwnd = int(self.winId())
            # BGR color: #0a1628 -> 0x28160a
            set_dark_title_bar(hwnd, 0x28160a)

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls and self.is_supported_video(urls[0].toLocalFile()):
                event.acceptProposedAction()
                self.drop_label.setStyleSheet("""
                    QLabel {
                        color: #99bbee;
                        font-size: 18px;
                        background-color: #152a45;
                        border: 2px dashed #3a6a9d;
                        border-radius: 10px;
                        padding: 50px;
                    }
                """)

    def dragLeaveEvent(self, event):
        """Handle drag leave events."""
        self.drop_label.setStyleSheet("""
            QLabel {
                color: #7799cc;
                font-size: 18px;
                background-color: #0d1a2d;
                border: 2px dashed #2a4a6d;
                border-radius: 10px;
                padding: 50px;
            }
        """)

    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        urls = event.mimeData().urls()
        if urls:
            # Collect all supported video files
            video_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if self.is_supported_video(file_path):
                    video_files.append(file_path)

            if video_files:
                # Build playlist and start playing
                self.build_playlist(video_files)
                if self.playlist:
                    self.play_current()
                event.acceptProposedAction()

    def is_supported_video(self, file_path: str) -> bool:
        """Check if the file is a supported video format."""
        return any(file_path.lower().endswith(fmt) for fmt in self.SUPPORTED_FORMATS)

    def get_video_duration(self, file_path: str) -> int:
        """
        Get the duration of a video file in milliseconds.
        Returns 0 if duration cannot be determined.
        """
        probe_player = QMediaPlayer()
        duration = 0

        loop = QEventLoop()

        def on_duration_changed(d):
            nonlocal duration
            duration = d
            loop.quit()

        def on_error(error, error_string):
            loop.quit()

        def on_status_changed(status):
            if status == QMediaPlayer.MediaStatus.LoadedMedia:
                # Give a moment for duration to be available
                QTimer.singleShot(50, loop.quit)
            elif status in (QMediaPlayer.MediaStatus.InvalidMedia,
                           QMediaPlayer.MediaStatus.NoMedia):
                loop.quit()

        probe_player.durationChanged.connect(on_duration_changed)
        probe_player.errorOccurred.connect(on_error)
        probe_player.mediaStatusChanged.connect(on_status_changed)

        probe_player.setSource(QUrl.fromLocalFile(file_path))

        # Timeout after 3 seconds
        QTimer.singleShot(3000, loop.quit)
        loop.exec()

        # Clean up
        probe_player.setSource(QUrl())

        return duration

    def build_playlist(self, file_paths: list):
        """
        Build a playlist from file paths, sorted by duration (shortest first).
        """
        self.drop_label.setText("Loading video information...")
        self.drop_label.show()
        QApplication.processEvents()

        # Get durations for all files
        videos_with_duration = []
        for i, path in enumerate(file_paths):
            self.drop_label.setText(f"Scanning video {i+1}/{len(file_paths)}...")
            QApplication.processEvents()
            duration = self.get_video_duration(path)
            videos_with_duration.append((path, duration))

        # Sort by duration (shortest first)
        videos_with_duration.sort(key=lambda x: x[1])

        self.playlist = videos_with_duration
        self.current_index = 0

    def play_video(self, file_path: str):
        """Play the specified video file."""
        # Hide label, show video widget
        self.drop_label.hide()
        self.video_widget.show()

        # Set and play the video
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()

        # Update window title with filename and playlist position
        filename = file_path.split('/')[-1].split('\\')[-1]
        if len(self.playlist) > 1:
            self.setWindowTitle(
                f"Video Drop Player v{self.VERSION} - "
                f"Playing {self.current_index + 1}/{len(self.playlist)} - {filename}"
            )
        else:
            self.setWindowTitle(f"Video Drop Player v{self.VERSION} - {filename}")

    def play_current(self):
        """Play the current video in the playlist."""
        if 0 <= self.current_index < len(self.playlist):
            file_path, _ = self.playlist[self.current_index]
            self.play_video(file_path)

    def play_next(self):
        """Play the next video in the playlist, or release if at end."""
        self.current_index += 1
        if self.current_index < len(self.playlist):
            self.play_current()
        else:
            # End of playlist
            self.release_video()

    def play_previous(self):
        """Play the previous video in the playlist."""
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current()

    def on_media_status_changed(self, status):
        """Handle media status changes."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Video finished - play next or return to drop screen
            self.play_next()

    def release_video(self):
        """Stop playback and release the file handle."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())  # Clear source to release file handle
        self.playlist = []
        self.current_index = 0
        self.video_widget.hide()
        self.drop_label.setText("Drag and drop a video file here")
        self.drop_label.show()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION}")

    def on_error(self, error, error_string):
        """Handle media player errors."""
        print(f"Error: {error_string}")
        self.media_player.setSource(QUrl())  # Release file handle
        self.drop_label.setText(f"Error: {error_string}\n\nDrag and drop another video file")
        self.drop_label.show()
        self.video_widget.hide()

    def keyPressEvent(self, event):
        """Handle key press events for playback control."""
        if event.key() == Qt.Key.Key_Space:
            # Toggle play/pause
            if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.media_player.pause()
            else:
                self.media_player.play()
        elif event.key() == Qt.Key.Key_Escape:
            # Stop and release file
            self.release_video()
        elif event.key() == Qt.Key.Key_Left:
            # Seek backward 5 seconds
            pos = self.media_player.position() - 5000
            self.media_player.setPosition(max(0, pos))
        elif event.key() == Qt.Key.Key_Right:
            # Seek forward 5 seconds
            pos = self.media_player.position() + 5000
            self.media_player.setPosition(pos)
        elif event.key() == Qt.Key.Key_Up:
            # Volume up
            volume = min(1.0, self.audio_output.volume() + 0.1)
            self.audio_output.setVolume(volume)
        elif event.key() == Qt.Key.Key_Down:
            # Volume down
            volume = max(0.0, self.audio_output.volume() - 0.1)
            self.audio_output.setVolume(volume)
        elif event.key() == Qt.Key.Key_M:
            # Toggle mute
            self.audio_output.setMuted(not self.audio_output.isMuted())
        elif event.key() == Qt.Key.Key_N:
            # Next video in playlist
            if self.playlist and self.current_index < len(self.playlist) - 1:
                self.play_next()
        elif event.key() == Qt.Key.Key_P:
            # Previous video in playlist
            self.play_previous()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    player = VideoDropPlayer()
    player.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
