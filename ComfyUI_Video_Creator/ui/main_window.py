from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QTabWidget, QVBoxLayout, QWidget,
)

from config import ConfigManager
from media_tools import resolve_ffmpeg
from run_worker import RunRequest, RunWorker
from ui.library_tab import LibraryTab
from ui.run_panel import RunPanel
from ui.settings_dialog import SettingsDialog
from ui.styles import COLORS, STYLESHEET
from ui.video_player import VideoPlayerDialog
from ui.widgets import THUMB_SIZE, MediaBrowser

# Width that shows exactly two thumbnail columns: two grid cells plus the
# grid spacing, the list padding, the frame and a scrollbar.
TWO_COLUMN_WIDTH = 2 * (THUMB_SIZE + 14) + 3 * 4 + 12 + 2 + 14


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, version: str):
        super().__init__()
        self.config = config
        self.version = version
        self._worker: RunWorker | None = None
        self._active_panel: RunPanel | None = None
        self._player: VideoPlayerDialog | None = None
        self._tab_splitters: list[QSplitter] = []
        self._splits_initialised = False

        self.setWindowTitle(f"ComfyUI Video Creator v{version}")
        self.setStyleSheet(STYLESHEET)
        self.resize(1640, 960)
        # 1080p is the minimum supported screen; below ~860px tall the
        # prompt editors hit their floor and the Options group gets squeezed.
        self.setMinimumSize(1280, 860)
        self._build_ui()

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #

    def _ffmpeg(self) -> str:
        return resolve_ffmpeg(self.config.get("ffmpeg_path", ""), Path(self.config.get("_base_dir", ".")))

    def _build_ui(self):
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(14, 10, 14, 12)
        root.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("ComfyUI Video Creator")
        title.setObjectName("header")
        header.addWidget(title)
        sub = QLabel(f"v{self.version}  ·  single-shot ComfyUI API workflows: image → video, video → extension")
        sub.setObjectName("subtitle")
        header.addWidget(sub)
        header.addStretch()
        self._mode_lbl = QLabel("")
        self._mode_lbl.setObjectName("subtitle")
        header.addWidget(self._mode_lbl)
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("secondary_btn")
        settings_btn.clicked.connect(self._open_settings)
        header.addWidget(settings_btn)
        root.addLayout(header)

        self._tabs = QTabWidget()
        self._image_browser = MediaBrowser("image", self.config.get("image_dir", ""),
                                           self.config.get("image_sort", "Name A→Z"), self._ffmpeg)
        self._image_panel = RunPanel("image", self.config)
        self._tabs.addTab(self._make_tab(self._image_browser, self._image_panel), "🖼  Image → Video")

        self._video_browser = MediaBrowser("video", self.config.get("video_dir", ""),
                                           self.config.get("video_sort", "Newest First"), self._ffmpeg,
                                           hint="Thumbnails show each video's LAST frame — the extension's starting point")
        self._video_panel = RunPanel("video", self.config)
        self._tabs.addTab(self._make_tab(self._video_browser, self._video_panel), "🎬  Video → Extend")

        self._library = LibraryTab(self.config, self._ffmpeg)
        self._library.play_requested.connect(self._play_list)
        self._library.send_to_extend.connect(self._send_to_extend)
        self._tabs.addTab(self._library, "📚  Library")
        root.addWidget(self._tabs, stretch=1)

        self.setCentralWidget(central)
        self._wire(self._image_browser, self._image_panel, "image_dir", "image_sort")
        self._wire(self._video_browser, self._video_panel, "video_dir", "video_sort")
        # A clone made on one tab has to show up in the other tab's dropdown too.
        self._image_panel.workflows_changed.connect(self._video_panel.refresh_workflow_list)
        self._video_panel.workflows_changed.connect(self._image_panel.refresh_workflow_list)
        self._video_browser.activated.connect(lambda p: self._play(str(p)))
        self._update_mode_label()
        # Initial scans run after the signals above are wired so the run
        # panels see the restored selection state.
        self._image_browser.refresh()
        self._video_browser.refresh()
        self._library.refresh()

    def _make_tab(self, browser: MediaBrowser, panel: RunPanel) -> QWidget:
        page = QWidget()
        lay = QHBoxLayout(page)
        lay.setContentsMargins(8, 8, 8, 8)
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(browser)
        split.addWidget(panel)
        # Thumbnails start two columns wide; the prompt/settings panel takes
        # the rest. Drag the divider (or resize the window) for more thumbs.
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setChildrenCollapsible(False)
        lay.addWidget(split)
        self._tab_splitters.append(split)
        return page

    def showEvent(self, event):
        super().showEvent(event)
        if not self._splits_initialised:
            self._splits_initialised = True
            QTimer.singleShot(0, self._init_tab_splits)

    def _init_tab_splits(self):
        for split in self._tab_splitters:
            total = sum(split.sizes()) or split.width()
            if total > 0:
                split.setSizes([TWO_COLUMN_WIDTH, max(total - TWO_COLUMN_WIDTH, 560)])

    def _wire(self, browser: MediaBrowser, panel: RunPanel, dir_key: str, sort_key: str):
        browser.selection_changed.connect(panel.set_source)
        browser.folder_changed.connect(lambda f: (self.config.set(dir_key, f), self.config.save()))
        browser.sort_changed.connect(lambda s: (self.config.set(sort_key, s), self.config.save()))
        panel.run_requested.connect(self._start)
        panel.cancel_requested.connect(self._cancel)
        panel.play_requested.connect(self._play)

    def _update_mode_label(self):
        mode = "RunPod" if self.config.is_runpod() else "Local"
        url = self.config.server_url() or "(no URL set)"
        color = COLORS['warning'] if self.config.is_runpod() else COLORS['success']
        self._mode_lbl.setText(f"<span style='color:{color}'>●</span> {mode}  <span style='color:{COLORS['fg_dim']}'>{url}</span>")

    # ------------------------------------------------------------------ #
    # Settings
    # ------------------------------------------------------------------ #

    def _open_settings(self):
        before = {k: self.config.get(k) for k in ("image_dir", "video_dir", "workflow_dir", "ffmpeg_path", "loras_dir", "output_dir", "library_dir")}
        dlg = SettingsDialog(self.config, self)
        if dlg.exec() != SettingsDialog.DialogCode.Accepted:
            return
        self._update_mode_label()
        if self.config.get("image_dir") != before["image_dir"]:
            self._image_browser.set_folder(self.config.get("image_dir", ""))
        if self.config.get("video_dir") != before["video_dir"] or self.config.get("ffmpeg_path") != before["ffmpeg_path"]:
            self._video_browser.set_folder(self.config.get("video_dir", ""))
        if self.config.get("workflow_dir") != before["workflow_dir"]:
            self._image_panel.reload_workflows()
            self._video_panel.reload_workflows()
        if (self.config.get("output_dir") != before["output_dir"]
                or self.config.get("library_dir") != before["library_dir"]):
            self._library.set_folder(self._library.effective_folder())
        for panel in (self._image_panel, self._video_panel):
            panel._font_spin.setValue(int(self.config.get("prompt_font_size", 10) or 10))
            if self.config.get("loras_dir") != before["loras_dir"]:
                panel.reload_loras_from_folder()

    # ------------------------------------------------------------------ #
    # Running
    # ------------------------------------------------------------------ #

    def _start(self, req: RunRequest):
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "Busy", "A generation is already running. Wait for it to finish or cancel it.")
            return
        if not self.config.server_url():
            QMessageBox.warning(self, "No server", "Set the ComfyUI URL for the selected mode in Settings first.")
            return
        if not (self.config.get("output_dir", "") or "").strip():
            QMessageBox.warning(self, "No output folder", "Set the Output folder in Settings first.")
            return
        self.config.save()
        panel = self._image_panel if req.source_kind == "image" else self._video_panel
        self._active_panel = panel
        for p in (self._image_panel, self._video_panel):
            p.set_running(True, active=(p is panel))

        cfg = self.config.get_all()
        self._worker = RunWorker(cfg, req)
        self._worker.log.connect(panel.append_log)
        self._worker.plan.connect(panel.on_plan)
        self._worker.step.connect(panel.on_step)
        self._worker.phase.connect(panel.on_phase)
        self._worker.finished_ok.connect(self._on_done)
        self._worker.failed.connect(self._on_failed)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    def _cancel(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            if self._active_panel is not None:
                self._active_panel.append_log("Cancelling — interrupting the server…")

    def _on_done(self, paths: list):
        if self._active_panel is not None:
            self._active_panel.on_done(list(paths))
        self._library.refresh()
        # New files may have landed in the folder the Video tab is showing
        out_dir = Path((self.config.get("output_dir", "") or "").strip() or ".")
        vid_dir = Path(self._video_browser.folder) if self._video_browser.folder else None
        if vid_dir is not None and vid_dir.exists() and out_dir.exists() and vid_dir.resolve() == out_dir.resolve():
            self._video_browser.refresh()

    def _on_failed(self, message: str):
        if self._active_panel is not None:
            self._active_panel.on_failed(message)
        if message != "Cancelled":
            QMessageBox.critical(self, "Generation failed", message)

    def _on_worker_finished(self):
        for p in (self._image_panel, self._video_panel):
            p.set_running(False)
        self._worker = None
        self._active_panel = None

    # ------------------------------------------------------------------ #
    # Player
    # ------------------------------------------------------------------ #

    def _play(self, path: str):
        if not path or not Path(path).exists():
            return
        if self._player is not None:
            self._player.close()
        # Every player in this app closes itself once the video ends.
        self._player = VideoPlayerDialog(path, self, auto_close=True)
        self._player.show()

    def _play_list(self, paths: list):
        """Library playback: plays the selection back-to-back and closes
        itself when the last one ends."""
        paths = [p for p in paths if p and Path(p).exists()]
        if not paths:
            return
        if self._player is not None:
            self._player.close()
        self._player = VideoPlayerDialog(paths[0], self, playlist=paths, auto_close=True)
        self._player.show()

    def _send_to_extend(self, path: Path):
        """Library → Extend: select the video in the Extend tab (switching the
        Extend folder to the library folder if it lives elsewhere)."""
        path = Path(path)
        self._tabs.setCurrentIndex(1)
        folder = str(path.parent)
        if self._video_browser.folder and Path(self._video_browser.folder).resolve() == path.parent.resolve():
            if not self._video_browser.grid.select_key(str(path)):
                self._video_panel.set_source(path)
        else:
            self.config.set("video_dir", folder)
            self.config.save()
            self._video_browser.set_folder(folder)
            self._video_panel.set_source(path)
            self._pending_select = str(path)
            self._video_browser.grid.model().rowsInserted.connect(self._try_pending_select)
        self._video_panel.append_log(f"Source from Library: {path.name}")

    def _try_pending_select(self, *_):
        key = getattr(self, "_pending_select", None)
        if key and self._video_browser.grid.select_key(key):
            self._pending_select = None
            try:
                self._video_browser.grid.model().rowsInserted.disconnect(self._try_pending_select)
            except TypeError:
                pass

    # ------------------------------------------------------------------ #

    def closeEvent(self, event):
        if self._worker is not None and self._worker.isRunning():
            ans = QMessageBox.question(
                self, "Generation running",
                "A generation is still running. Cancel it and quit?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            )
            if ans != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            self._worker.cancel()
            self._worker.wait(5000)
        self._image_browser.shutdown()
        self._video_browser.shutdown()
        self._library.shutdown()
        self.config.save()
        event.accept()
