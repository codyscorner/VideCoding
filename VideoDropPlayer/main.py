"""
Video Drop Player - A simple drag-and-drop video player
Supports MP4 and other common video formats
"""

import sys
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QStackedLayout,
    QDialog, QRadioButton, QButtonGroup, QPushButton, QHBoxLayout
)
import random
from PyQt6.QtCore import Qt, QUrl, QEventLoop, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget

class SortOrderDialog(QDialog):
    """Dialog for choosing playlist sort order."""

    SORT_FILENAME_ASC = "filename_asc"
    SORT_FILENAME_DESC = "filename_desc"
    SORT_DATE_ASC = "date_asc"
    SORT_DATE_DESC = "date_desc"
    SORT_DURATION_ASC = "duration_asc"
    SORT_DURATION_DESC = "duration_desc"
    SORT_RANDOM = "random"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Choose Play Order")
        self.setModal(True)
        self.setFixedWidth(280)

        layout = QVBoxLayout(self)

        # Radio buttons for sort options
        self.button_group = QButtonGroup(self)

        self.radio_filename_asc = QRadioButton("Filename (A → Z)")
        self.radio_filename_desc = QRadioButton("Filename (Z → A)")
        self.radio_date_asc = QRadioButton("Date created (oldest first)")
        self.radio_date_desc = QRadioButton("Date created (newest first)")
        self.radio_duration_asc = QRadioButton("Duration (shortest first)")
        self.radio_duration_desc = QRadioButton("Duration (longest first)")
        self.radio_random = QRadioButton("Random")

        self.radio_filename_asc.setChecked(True)

        self.button_group.addButton(self.radio_filename_asc, 0)
        self.button_group.addButton(self.radio_filename_desc, 1)
        self.button_group.addButton(self.radio_date_asc, 2)
        self.button_group.addButton(self.radio_date_desc, 3)
        self.button_group.addButton(self.radio_duration_asc, 4)
        self.button_group.addButton(self.radio_duration_desc, 5)
        self.button_group.addButton(self.radio_random, 6)

        layout.addWidget(self.radio_filename_asc)
        layout.addWidget(self.radio_filename_desc)
        layout.addWidget(self.radio_date_asc)
        layout.addWidget(self.radio_date_desc)
        layout.addWidget(self.radio_duration_asc)
        layout.addWidget(self.radio_duration_desc)
        layout.addWidget(self.radio_random)

        # Buttons
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("Play")
        self.cancel_button = QPushButton("Cancel")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #0d1a2d;
            }
            QRadioButton {
                color: #99bbee;
                font-size: 13px;
                padding: 5px;
            }
            QRadioButton::indicator {
                width: 14px;
                height: 14px;
            }
            QPushButton {
                background-color: #1a3a5c;
                color: #99bbee;
                border: 1px solid #2a4a6d;
                border-radius: 4px;
                padding: 6px 16px;
                font-size: 13px;
            }
            QPushButton:hover {
                background-color: #2a4a6d;
            }
            QPushButton:pressed {
                background-color: #3a5a7d;
            }
        """)

    def get_sort_order(self) -> str:
        """Return the selected sort order."""
        button_id = self.button_group.checkedId()
        orders = [
            self.SORT_FILENAME_ASC,
            self.SORT_FILENAME_DESC,
            self.SORT_DATE_ASC,
            self.SORT_DATE_DESC,
            self.SORT_DURATION_ASC,
            self.SORT_DURATION_DESC,
            self.SORT_RANDOM,
        ]
        return orders[button_id]


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
                self.parent_player.handle_video_drop(video_files)
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

    VERSION = "1.2.0"
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION}")
        self.resize(800, 600)
        self.setMinimumSize(400, 300)

        # Center window on screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - 800) // 2
        y = (screen.height() - 600) // 2
        self.move(x, y)

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
                self.handle_video_drop(video_files)
                event.acceptProposedAction()

    def handle_video_drop(self, video_files: list):
        """Handle dropped video files - show sort dialog if multiple files."""
        if len(video_files) == 1:
            # Single file - play directly without dialog
            self.build_playlist(video_files)
            if self.playlist:
                self.play_current()
        else:
            # Multiple files - show sort order dialog
            dialog = SortOrderDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                sort_order = dialog.get_sort_order()
                self.build_playlist(video_files, sort_order)
                if self.playlist:
                    self.play_current()

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

    def build_playlist(self, file_paths: list, sort_order: str = SortOrderDialog.SORT_FILENAME_ASC):
        """
        Build a playlist from file paths, sorted according to sort_order.
        """
        # Helper to get filename from path
        def get_filename(path):
            return os.path.basename(path).lower()

        # Helper to get file creation time
        def get_creation_time(path):
            try:
                return os.path.getctime(path)
            except OSError:
                return 0

        # Check if we need durations (only for duration-based sorting)
        need_durations = sort_order in (
            SortOrderDialog.SORT_DURATION_ASC,
            SortOrderDialog.SORT_DURATION_DESC
        )

        if need_durations:
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
        else:
            # No duration needed, use 0 as placeholder
            videos_with_duration = [(path, 0) for path in file_paths]

        # Sort based on selected order
        if sort_order == SortOrderDialog.SORT_FILENAME_ASC:
            videos_with_duration.sort(key=lambda x: get_filename(x[0]))
        elif sort_order == SortOrderDialog.SORT_FILENAME_DESC:
            videos_with_duration.sort(key=lambda x: get_filename(x[0]), reverse=True)
        elif sort_order == SortOrderDialog.SORT_DATE_ASC:
            videos_with_duration.sort(key=lambda x: get_creation_time(x[0]))
        elif sort_order == SortOrderDialog.SORT_DATE_DESC:
            videos_with_duration.sort(key=lambda x: get_creation_time(x[0]), reverse=True)
        elif sort_order == SortOrderDialog.SORT_DURATION_ASC:
            videos_with_duration.sort(key=lambda x: x[1])
        elif sort_order == SortOrderDialog.SORT_DURATION_DESC:
            videos_with_duration.sort(key=lambda x: x[1], reverse=True)
        elif sort_order == SortOrderDialog.SORT_RANDOM:
            random.shuffle(videos_with_duration)

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
