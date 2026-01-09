"""
Video Drop Player - A simple drag-and-drop video player
Supports MP4 and other common video formats
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QStackedLayout
)
from PyQt6.QtCore import Qt, QUrl
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
            file_path = urls[0].toLocalFile()
            if self.parent_player.is_supported_video(file_path):
                self.parent_player.play_video(file_path)
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

    VERSION = "1.0.6"
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION}")
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(400, 300)

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
            file_path = urls[0].toLocalFile()
            if self.is_supported_video(file_path):
                self.play_video(file_path)
                event.acceptProposedAction()

    def is_supported_video(self, file_path: str) -> bool:
        """Check if the file is a supported video format."""
        return any(file_path.lower().endswith(fmt) for fmt in self.SUPPORTED_FORMATS)

    def play_video(self, file_path: str):
        """Play the specified video file."""
        # Hide label, show video widget
        self.drop_label.hide()
        self.video_widget.show()

        # Set and play the video
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.play()

        # Update window title with filename
        filename = file_path.split('/')[-1].split('\\')[-1]
        self.setWindowTitle(f"Video Drop Player v{self.VERSION} - {filename}")

    def on_media_status_changed(self, status):
        """Handle media status changes."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            # Video finished - return to drop screen and release file
            self.release_video()

    def release_video(self):
        """Stop playback and release the file handle."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())  # Clear source to release file handle
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


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    player = VideoDropPlayer()
    player.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
