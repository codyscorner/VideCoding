"""
Video Drop Player - A simple drag-and-drop video and image player
Supports MP4 and other common video formats, plus common image formats
"""

import sys
import os
import json
from datetime import datetime
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QLabel, QStackedLayout,
    QDialog, QRadioButton, QButtonGroup, QPushButton, QHBoxLayout, QMessageBox
)
import random
from PyQt6.QtCore import Qt, QUrl, QEventLoop, QTimer
from PyQt6.QtGui import QDragEnterEvent, QDropEvent, QIcon, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from send2trash import send2trash

CONFIG_FILE = os.path.join(
    os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else __file__),
    "video_drop_player_config.json",
)
RESUME_MIN_MS = 3000            # don't bother resuming videos barely started
RESUME_END_MARGIN_MS = 5000     # don't resume within the last few seconds (treat as finished)

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
            if urls:
                file_path = urls[0].toLocalFile()
                if (self.parent_player.is_supported_video(file_path) or
                        self.parent_player.is_supported_image(file_path)):
                    event.acceptProposedAction()

    def dragMoveEvent(self, event):
        """Handle drag move events."""
        event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        """Handle drop events."""
        urls = event.mimeData().urls()
        if urls:
            video_files = []
            image_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if self.parent_player.is_supported_video(file_path):
                    video_files.append(file_path)
                elif self.parent_player.is_supported_image(file_path):
                    image_files.append(file_path)

            if video_files:
                self.parent_player.handle_video_drop(video_files)
                event.acceptProposedAction()
            elif image_files:
                self.parent_player.handle_image_drop(image_files)
                event.acceptProposedAction()


def get_icon_path():
    """Get the path to the app icon."""
    if getattr(sys, 'frozen', False):
        # Running as compiled executable
        return os.path.join(os.path.dirname(sys.executable), 'app_icon.ico')
    else:
        # Running as script
        return os.path.join(os.path.dirname(__file__), 'app_icon.ico')


class ImageViewer(QLabel):
    """A label-based image viewer that scales images to fit."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background-color: #0a1628;")
        self._pixmap = None

    def set_image(self, file_path: str):
        """Load and display an image."""
        self._pixmap = QPixmap(file_path)
        self._scale_to_fit()

    def _scale_to_fit(self):
        if self._pixmap and not self._pixmap.isNull():
            scaled = self._pixmap.scaled(
                self.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.setPixmap(scaled)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._scale_to_fit()


class VideoDropPlayer(QMainWindow):
    """Main window for the video drop player application."""

    VERSION = "1.4.0"
    PLAYBACK_SPEEDS = [0.5, 1.0, 1.25, 1.5, 2.0]
    SUPPORTED_FORMATS = {'.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm'}
    SUPPORTED_IMAGE_FORMATS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}

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

        # Playlist state (videos)
        self.playlist = []  # List of (file_path, duration_ms) tuples
        self.current_index = 0

        # Image viewer state
        self.image_list = []
        self.image_index = 0
        self._mode = 'drop'  # 'drop', 'video', 'image'

        # Fullscreen state
        self._is_fullscreen = False

        # Playback speed
        self._speed_index = 1  # default 1.0x

        # Double-tap left arrow detection for previous video
        self._left_tap_timer = QTimer()
        self._left_tap_timer.setSingleShot(True)
        self._left_tap_timer.setInterval(400)  # ms window for double-tap
        self._left_tap_timer.timeout.connect(self._left_seek)
        self._left_tap_pending = False

        # Resume-position memory (per file path, milliseconds)
        self._positions = self._load_positions()
        self._pending_resume_ms = 0
        self._current_file_path = None

        # A-B loop
        self._loop_in_ms = None
        self._loop_out_ms = None

        # Last video frame (for screenshot capture)
        self._last_frame = None

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

        # Create image viewer
        self.image_viewer = ImageViewer()

        # Create drop overlay (top layer - always captures drops)
        self.drop_overlay = DropOverlay(self)

        # Create drop hint label (shown when no video is playing)
        self.drop_label = QLabel("Drag and drop a video or image file here")
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
        self.stacked_layout.addWidget(self.image_viewer)
        self.stacked_layout.addWidget(self.drop_label)
        self.stacked_layout.addWidget(self.drop_overlay)

        # Initially show drop screen
        self._show_drop_screen()

        # Set up media player
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)

        # Connect signals
        self.media_player.mediaStatusChanged.connect(self.on_media_status_changed)
        self.media_player.errorOccurred.connect(self.on_error)
        self.media_player.positionChanged.connect(self._on_position_changed)
        self.video_widget.videoSink().videoFrameChanged.connect(self._on_video_frame)

        # Set window style - dark blue theme
        self.setStyleSheet("""
            QMainWindow {
                background-color: #0a1628;
            }
        """)

        # Apply dark blue title bar on Windows
        if sys.platform == 'win32':
            self._apply_title_bar_color()

    def _toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True

    def _cycle_speed(self):
        self._speed_index = (self._speed_index + 1) % len(self.PLAYBACK_SPEEDS)
        speed = self.PLAYBACK_SPEEDS[self._speed_index]
        self.media_player.setPlaybackRate(speed)
        label = f"{speed:g}x"
        if len(self.playlist) > 1:
            file_path, _ = self.playlist[self.current_index]
            filename = os.path.basename(file_path)
            self.setWindowTitle(
                f"Video Drop Player v{self.VERSION} - "
                f"[{label}] Playing {self.current_index + 1}/{len(self.playlist)} - {filename}"
            )
        elif self.playlist:
            file_path, _ = self.playlist[self.current_index]
            filename = os.path.basename(file_path)
            self.setWindowTitle(f"Video Drop Player v{self.VERSION} - [{label}] {filename}")

    def _apply_title_bar_color(self):
        """Apply dark blue color to Windows title bar."""
        if sys.platform == 'win32':
            hwnd = int(self.winId())
            # BGR color: #0a1628 -> 0x28160a
            set_dark_title_bar(hwnd, 0x28160a)

    # ------------------------------------------------------------------
    # Resume-position memory

    @staticmethod
    def _load_positions() -> dict:
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f).get("positions", {})
        except Exception:
            return {}

    def _save_positions(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"positions": self._positions}, f, indent=2)
        except Exception:
            pass

    def _remember_current_position(self):
        """Store (or clear) the outgoing file's playback position before switching away."""
        if not self._current_file_path:
            return
        pos = self.media_player.position()
        duration = self.media_player.duration()
        if pos < RESUME_MIN_MS or (duration > 0 and pos >= duration - RESUME_END_MARGIN_MS):
            self._positions.pop(self._current_file_path, None)
        else:
            self._positions[self._current_file_path] = pos
        self._save_positions()

    def _on_position_changed(self, position: int):
        if self._loop_out_ms is not None and self._loop_in_ms is not None:
            if position >= self._loop_out_ms:
                self.media_player.setPosition(self._loop_in_ms)

    # ------------------------------------------------------------------
    # A-B loop

    def _set_loop_in(self):
        if self._mode != 'video':
            return
        self._loop_in_ms = self.media_player.position()
        if self._loop_out_ms is not None and self._loop_out_ms <= self._loop_in_ms:
            self._loop_out_ms = None
        self._flash_message("Loop point A set")

    def _set_loop_out(self):
        if self._mode != 'video' or self._loop_in_ms is None:
            return
        pos = self.media_player.position()
        if pos <= self._loop_in_ms:
            return
        self._loop_out_ms = pos
        self._flash_message("A-B loop active")

    def _clear_loop(self):
        self._loop_in_ms = None
        self._loop_out_ms = None
        self._flash_message("Loop cleared")

    def _flash_message(self, text: str, duration_ms: int = 1500):
        """Briefly show a status message in the title bar, then restore it."""
        restore = self.windowTitle()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION} - {text}")
        QTimer.singleShot(duration_ms, lambda: self.setWindowTitle(restore))

    # ------------------------------------------------------------------
    # Screenshot

    def _on_video_frame(self, frame):
        if frame.isValid():
            self._last_frame = frame

    def _take_screenshot(self):
        if self._mode != 'video' or self._last_frame is None or not self._last_frame.isValid():
            return
        image = self._last_frame.toImage()
        if image.isNull():
            return

        source = Path(self._current_file_path) if self._current_file_path else None
        out_dir = (source.parent if source else Path.cwd()) / "Screenshots"
        try:
            out_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return

        stem = source.stem if source else "screenshot"
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{stem}_{ts}.png"
        if image.save(str(out_path)):
            self._flash_message(f"Screenshot saved: {out_path.name}")

    # ------------------------------------------------------------------
    # Delete current file

    def _delete_current_file(self):
        if self._mode == 'video' and self.playlist:
            file_path, _ = self.playlist[self.current_index]
        elif self._mode == 'image' and self.image_list:
            file_path = self.image_list[self.image_index]
        else:
            return

        reply = QMessageBox.question(
            self, "Delete File",
            f"Send this file to the Recycle Bin?\n\n{os.path.basename(file_path)}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if self._mode == 'video':
            self.media_player.stop()
            self.media_player.setSource(QUrl())
            self._positions.pop(file_path, None)
            self._save_positions()
            try:
                send2trash(file_path)
            except Exception as exc:
                QMessageBox.warning(self, "Delete Failed", str(exc))
                return
            del self.playlist[self.current_index]
            if not self.playlist:
                self.release_video()
            else:
                if self.current_index >= len(self.playlist):
                    self.current_index = len(self.playlist) - 1
                self.play_current()
        else:
            try:
                send2trash(file_path)
            except Exception as exc:
                QMessageBox.warning(self, "Delete Failed", str(exc))
                return
            del self.image_list[self.image_index]
            if not self.image_list:
                self.release_video()
            else:
                if self.image_index >= len(self.image_list):
                    self.image_index = len(self.image_list) - 1
                self.show_current_image()

    def _show_drop_screen(self):
        self._mode = 'drop'
        self.video_widget.hide()
        self.image_viewer.hide()
        self.drop_label.show()

    def _show_video_screen(self):
        self._mode = 'video'
        self.image_viewer.hide()
        self.drop_label.hide()
        self.video_widget.show()

    def _show_image_screen(self):
        self._mode = 'image'
        self.video_widget.hide()
        self.drop_label.hide()
        self.image_viewer.show()

    def dragEnterEvent(self, event: QDragEnterEvent):
        """Handle drag enter events."""
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if urls:
                file_path = urls[0].toLocalFile()
                if self.is_supported_video(file_path) or self.is_supported_image(file_path):
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
            video_files = []
            image_files = []
            for url in urls:
                file_path = url.toLocalFile()
                if self.is_supported_video(file_path):
                    video_files.append(file_path)
                elif self.is_supported_image(file_path):
                    image_files.append(file_path)

            if video_files:
                self.handle_video_drop(video_files)
                event.acceptProposedAction()
            elif image_files:
                self.handle_image_drop(image_files)
                event.acceptProposedAction()

    def handle_video_drop(self, video_files: list):
        """Handle dropped video files - show sort dialog if multiple files."""
        if len(video_files) == 1:
            self.build_playlist(video_files)
            if self.playlist:
                self.play_current()
        else:
            dialog = SortOrderDialog(self)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                sort_order = dialog.get_sort_order()
                self.build_playlist(video_files, sort_order)
                if self.playlist:
                    self.play_current()

    def handle_image_drop(self, image_files: list):
        """Handle dropped image files."""
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.playlist = []

        # Sort by filename ascending
        self.image_list = sorted(image_files, key=lambda p: os.path.basename(p).lower())
        self.image_index = 0
        self.show_current_image()

    def show_current_image(self):
        """Display the current image."""
        if not self.image_list:
            return
        file_path = self.image_list[self.image_index]
        self.image_viewer.set_image(file_path)
        self._show_image_screen()

        filename = os.path.basename(file_path)
        if len(self.image_list) > 1:
            self.setWindowTitle(
                f"Video Drop Player v{self.VERSION} - "
                f"Image {self.image_index + 1}/{len(self.image_list)} - {filename}"
            )
        else:
            self.setWindowTitle(f"Video Drop Player v{self.VERSION} - {filename}")

    def is_supported_video(self, file_path: str) -> bool:
        """Check if the file is a supported video format."""
        return any(file_path.lower().endswith(fmt) for fmt in self.SUPPORTED_FORMATS)

    def is_supported_image(self, file_path: str) -> bool:
        """Check if the file is a supported image format."""
        return any(file_path.lower().endswith(fmt) for fmt in self.SUPPORTED_IMAGE_FORMATS)

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
                QTimer.singleShot(50, loop.quit)
            elif status in (QMediaPlayer.MediaStatus.InvalidMedia,
                           QMediaPlayer.MediaStatus.NoMedia):
                loop.quit()

        probe_player.durationChanged.connect(on_duration_changed)
        probe_player.errorOccurred.connect(on_error)
        probe_player.mediaStatusChanged.connect(on_status_changed)

        probe_player.setSource(QUrl.fromLocalFile(file_path))

        QTimer.singleShot(3000, loop.quit)
        loop.exec()

        probe_player.setSource(QUrl())

        return duration

    def build_playlist(self, file_paths: list, sort_order: str = SortOrderDialog.SORT_FILENAME_ASC):
        """Build a playlist from file paths, sorted according to sort_order."""
        def get_filename(path):
            return os.path.basename(path).lower()

        def get_creation_time(path):
            try:
                return os.path.getctime(path)
            except OSError:
                return 0

        need_durations = sort_order in (
            SortOrderDialog.SORT_DURATION_ASC,
            SortOrderDialog.SORT_DURATION_DESC
        )

        if need_durations:
            self.drop_label.setText("Loading video information...")
            self.drop_label.show()
            QApplication.processEvents()

            videos_with_duration = []
            for i, path in enumerate(file_paths):
                self.drop_label.setText(f"Scanning video {i+1}/{len(file_paths)}...")
                QApplication.processEvents()
                duration = self.get_video_duration(path)
                videos_with_duration.append((path, duration))
        else:
            videos_with_duration = [(path, 0) for path in file_paths]

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
        self._remember_current_position()
        self._loop_in_ms = None
        self._loop_out_ms = None
        self._show_video_screen()

        self._current_file_path = file_path
        self._pending_resume_ms = self._positions.get(file_path, 0)

        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.setPlaybackRate(self.PLAYBACK_SPEEDS[self._speed_index])
        self.media_player.play()

        filename = os.path.basename(file_path)
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
            self.release_video()

    def play_previous(self):
        """Play the previous video in the playlist."""
        if self.current_index > 0:
            self.current_index -= 1
            self.play_current()

    def on_media_status_changed(self, status):
        """Handle media status changes."""
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.play_next()
        elif status == QMediaPlayer.MediaStatus.LoadedMedia and self._pending_resume_ms:
            self.media_player.setPosition(self._pending_resume_ms)
            self._pending_resume_ms = 0

    def release_video(self):
        """Stop playback and release the file handle."""
        self._remember_current_position()
        self._current_file_path = None
        self._loop_in_ms = None
        self._loop_out_ms = None
        self._last_frame = None
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.playlist = []
        self.current_index = 0
        self.image_list = []
        self.image_index = 0
        self._speed_index = 1  # reset to 1.0x
        self.drop_label.setText("Drag and drop a video or image file here")
        self._show_drop_screen()
        self.setWindowTitle(f"Video Drop Player v{self.VERSION}")

    def closeEvent(self, event):
        """Persist the current file's resume position before the app closes."""
        self._remember_current_position()
        super().closeEvent(event)

    def on_error(self, error, error_string):
        """Handle media player errors."""
        print(f"Error: {error_string}")
        self.media_player.setSource(QUrl())
        self.drop_label.setText(f"Error: {error_string}\n\nDrag and drop another file")
        self._show_drop_screen()

    def _left_seek(self):
        """Seek backward 5 seconds — called after single left-tap timeout."""
        self._left_tap_pending = False
        pos = self.media_player.position() - 5000
        self.media_player.setPosition(max(0, pos))

    def keyPressEvent(self, event):
        """Handle key press events for playback control."""
        key = event.key()

        if key == Qt.Key.Key_Escape:
            if self._is_fullscreen:
                self._toggle_fullscreen()
            else:
                self.release_video()

        elif key == Qt.Key.Key_F:
            self._toggle_fullscreen()
            return

        elif key == Qt.Key.Key_Delete and self._mode in ('video', 'image'):
            self._delete_current_file()

        elif self._mode == 'video' and key == Qt.Key.Key_S:
            self._cycle_speed()

        elif self._mode == 'image':
            if key == Qt.Key.Key_Right and self.image_index < len(self.image_list) - 1:
                self.image_index += 1
                self.show_current_image()
            elif key == Qt.Key.Key_Left and self.image_index > 0:
                self.image_index -= 1
                self.show_current_image()

        elif self._mode == 'video':
            if key == Qt.Key.Key_Space:
                if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                    self.media_player.pause()
                else:
                    self.media_player.play()
            elif key == Qt.Key.Key_Left:
                if self._left_tap_pending:
                    # Double-tap: go to previous video
                    self._left_tap_timer.stop()
                    self._left_tap_pending = False
                    self.play_previous()
                else:
                    # First tap: seek back after timeout if no second tap
                    self._left_tap_pending = True
                    self._left_tap_timer.start()
            elif key == Qt.Key.Key_Right:
                pos = self.media_player.position() + 5000
                self.media_player.setPosition(pos)
            elif key == Qt.Key.Key_Up:
                volume = min(1.0, self.audio_output.volume() + 0.1)
                self.audio_output.setVolume(volume)
            elif key == Qt.Key.Key_Down:
                volume = max(0.0, self.audio_output.volume() - 0.1)
                self.audio_output.setVolume(volume)
            elif key == Qt.Key.Key_M:
                self.audio_output.setMuted(not self.audio_output.isMuted())
            elif key == Qt.Key.Key_N:
                if self.playlist and self.current_index < len(self.playlist) - 1:
                    self.play_next()
            elif key == Qt.Key.Key_P:
                self.play_previous()
            elif key == Qt.Key.Key_BracketLeft:
                self._set_loop_in()
            elif key == Qt.Key.Key_BracketRight:
                self._set_loop_out()
            elif key == Qt.Key.Key_L:
                self._clear_loop()
            elif key == Qt.Key.Key_C:
                self._take_screenshot()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    player = VideoDropPlayer()
    player.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
