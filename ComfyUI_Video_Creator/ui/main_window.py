import tempfile
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSplitter,
    QTabWidget, QVBoxLayout, QWidget,
)

from config import ConfigManager
from media_tools import extract_thumbnail, resolve_ffmpeg
from run_worker import RunRequest, RunWorker, _base_stem, _workflow_labels
from ui.library_tab import LibraryTab
from ui.pod_control import PodControl
from ui.queue_dialog import QueueDialog
from ui.run_panel import RunPanel
from ui.settings_dialog import SettingsDialog
from ui.styles import COLORS, STYLESHEET
from ui.video_player import VideoPlayerDialog
from ui.widgets import THUMB_SIZE, MediaBrowser

# Width that shows exactly two thumbnail columns: two grid cells plus the
# grid spacing, the list padding, the frame and a scrollbar.
TWO_COLUMN_WIDTH = 2 * (THUMB_SIZE + 14) + 3 * 4 + 12 + 2 + 14

# Tab positions. Library → Send to Extend and Reuse Settings jump by these.
TAB_INDEX = {"image": 0, "video": 1, "text": 2, "library": 3}


class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, version: str):
        super().__init__()
        self.config = config
        self.version = version
        self._worker: RunWorker | None = None
        self._active_panel: RunPanel | None = None
        self._active_req: RunRequest | None = None
        self._queue: list[RunRequest] = []
        self._queue_dlg: QueueDialog | None = None
        self._player: VideoPlayerDialog | None = None
        self._tab_splitters: list[QSplitter] = []
        self._splits_initialised = False
        # kind -> RunPanel, filled by _build_ui; the tab order is the
        # TAB_INDEX order.
        self._panels: dict[str, RunPanel] = {}

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
        sub = QLabel(f"v{self.version}  ·  single-shot ComfyUI API workflows: "
                     "image → video, video → extension, text → video")
        sub.setObjectName("subtitle")
        header.addWidget(sub)
        header.addStretch()
        self._mode_lbl = QLabel("")
        self._mode_lbl.setObjectName("subtitle")
        header.addWidget(self._mode_lbl)
        self._pod = PodControl(self.config, self._generation_running, self)
        self._pod.server_changed.connect(self._update_mode_label)
        self._pod.log.connect(self._log_everywhere)
        header.addWidget(self._pod)
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

        # Text → Video has nothing to pick from, so no thumbnail browser: the
        # run panel — and its prompt editor — gets the whole tab.
        self._text_panel = RunPanel("text", self.config)
        text_page = QWidget()
        text_lay = QHBoxLayout(text_page)
        text_lay.setContentsMargins(8, 8, 8, 8)
        text_lay.addWidget(self._text_panel)
        self._tabs.addTab(text_page, "✍  Text → Video")
        self._panels = {"image": self._image_panel, "video": self._video_panel, "text": self._text_panel}

        for b in (self._video_browser, self._image_browser):
            b.deleting.connect(self._on_files_deleting)
            b.deleted.connect(self._on_files_deleted)
        self._library = LibraryTab(self.config, self._ffmpeg)
        self._library.browser.deleting.connect(self._on_files_deleting)
        self._library.browser.deleted.connect(self._on_files_deleted)
        self._library.play_requested.connect(self._play_list)
        self._library.send_to_extend.connect(self._send_to_extend)
        self._library.reuse_requested.connect(self._reuse_settings)
        self._tabs.addTab(self._library, "📚  Library")
        root.addWidget(self._tabs, stretch=1)

        self.setCentralWidget(central)
        self._wire(self._image_browser, self._image_panel, "image_dir", "image_sort")
        self._wire(self._video_browser, self._video_panel, "video_dir", "video_sort")
        self._wire_panel(self._text_panel)
        # A clone made on one tab has to show up in the other tabs' dropdowns too.
        for source in self._panels.values():
            for other in self._panels.values():
                if other is not source:
                    source.workflows_changed.connect(other.refresh_workflow_list)
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
            # After the window is actually on screen, so the prompt has a
            # parent to centre on rather than appearing behind it.
            QTimer.singleShot(200, self._pod.check_on_launch)

    def _generation_running(self) -> bool:
        return self._worker is not None and self._worker.isRunning()

    def _log_everywhere(self, msg: str):
        """Pod progress isn't tied to any one tab, so it goes to every log."""
        for panel in self._panels.values():
            panel.append_log(msg)

    def _init_tab_splits(self):
        for split in self._tab_splitters:
            total = sum(split.sizes()) or split.width()
            if total > 0:
                split.setSizes([TWO_COLUMN_WIDTH, max(total - TWO_COLUMN_WIDTH, 560)])

    def _wire(self, browser: MediaBrowser, panel: RunPanel, dir_key: str, sort_key: str):
        browser.selection_changed.connect(panel.set_source)
        browser.folder_changed.connect(lambda f: (self.config.set(dir_key, f), self.config.save()))
        browser.sort_changed.connect(lambda s: (self.config.set(sort_key, s), self.config.save()))
        self._wire_panel(panel)

    def _wire_panel(self, panel: RunPanel):
        panel.run_requested.connect(self._start)
        panel.cancel_requested.connect(self._cancel)
        panel.clear_queue_requested.connect(self._clear_queue)
        panel.show_queue_requested.connect(self._show_queue)
        panel.set_queue_probe(self._queued_duplicate)
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
        for panel in self._panels.values():
            panel._font_spin.setValue(int(self.config.get("prompt_font_size", 10) or 10))
            if self.config.get("loras_dir") != before["loras_dir"]:
                panel.reload_loras_from_folder()
            panel.refresh_rewriter_status()

    # ------------------------------------------------------------------ #
    # Running
    # ------------------------------------------------------------------ #

    def _start(self, req: RunRequest):
        if not self.config.server_url():
            QMessageBox.warning(self, "No server", "Set the ComfyUI URL for the selected mode in Settings first.")
            return
        if self._pod.over_limit():
            limit = float(self.config.get("runpod_spend_limit", 0) or 0)
            QMessageBox.warning(
                self, "Spend limit reached",
                f"This pod has hit the ${limit:.2f} session limit, so no new runs are "
                "being started. It will stop once the current run finishes.\n\n"
                "Raise the limit in Settings to keep going.")
            return
        if not (self.config.get("output_dir", "") or "").strip():
            QMessageBox.warning(self, "No output folder", "Set the Output folder in Settings first.")
            return
        self.config.save()
        if self._worker is not None and self._worker.isRunning():
            # ComfyUI only works one prompt at a time - hold this one and run
            # it automatically once whatever's running now finishes.
            self._queue.append(req)
            panel = self._panel_for(req)
            panel.append_log(f"Queued #{len(self._queue)} — {req.describe()}")
            self._update_queue_label()
            return
        self._launch(req)

    def _launch(self, req: RunRequest):
        panel = self._panel_for(req)
        self._active_panel = panel
        self._active_req = req
        panel.set_running(True, active=True)

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
        self._update_queue_label()

    def _update_queue_label(self):
        n = len(self._queue)
        tooltip = "\n".join(f"{i + 1}. {r.describe()}" for i, r in enumerate(self._queue))
        next_up = f"{self._queue[0].source_name} ({self._queue[0].workflow_label})" if self._queue else ""
        for p in self._panels.values():
            p.set_queue_status(n, tooltip, next_up)
        if self._queue_dlg is not None:
            self._queue_dlg.set_items(self._active_req, list(self._queue))

    def _panel_for(self, req: RunRequest) -> RunPanel:
        return self._panels.get(req.source_kind, self._image_panel)

    def _show_queue(self):
        """Opens (or raises) the queue view — what's running plus everything
        waiting, with enough detail to spot a run that's already lined up."""
        if self._queue_dlg is None:
            dlg = QueueDialog(self)
            dlg.remove_requested.connect(self._remove_queued)
            dlg.move_requested.connect(self._move_queued)
            dlg.clear_requested.connect(self._clear_queue)
            self._queue_dlg = dlg
        self._queue_dlg.set_items(self._active_req, list(self._queue))
        self._queue_dlg.show()
        self._queue_dlg.raise_()
        self._queue_dlg.activateWindow()

    def _queued_duplicate(self, req: RunRequest) -> str:
        """Called by a run panel before it queues anything: names the run
        already running or waiting that this one repeats, or "" if it's new."""
        fp = req.fingerprint()
        if self._active_req is not None and self._active_req.fingerprint() == fp:
            return "the run going on right now"
        for i, queued in enumerate(self._queue):
            if queued.fingerprint() == fp:
                return f"queue position {i + 1}"
        return ""

    def _remove_queued(self, index: int):
        if not 0 <= index < len(self._queue):
            return
        req = self._queue.pop(index)
        self._panel_for(req).append_log(f"Removed from queue: {req.describe()}")
        self._update_queue_label()

    def _move_queued(self, index: int, delta: int):
        target = index + delta
        if not (0 <= index < len(self._queue) and 0 <= target < len(self._queue)):
            return
        self._queue[index], self._queue[target] = self._queue[target], self._queue[index]
        self._update_queue_label()
        if self._queue_dlg is not None:
            self._queue_dlg.select_position(target)

    def _clear_queue(self):
        for req in self._queue:
            self._panel_for(req).append_log(f"Removed from queue: {req.describe()}")
        self._queue.clear()
        self._update_queue_label()

    def _cancel(self):
        if self._worker is not None and self._worker.isRunning():
            self._worker.cancel()
            if self._active_panel is not None:
                self._active_panel.append_log("Cancelling — interrupting the server…")

    def _on_done(self, paths: list, timing: dict | None = None):
        if self._active_panel is not None:
            self._active_panel.on_done(list(paths), self._active_req, timing)
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
        if self._active_panel is not None:
            self._active_panel.set_running(False)
        self._worker = None
        self._active_panel = None
        self._active_req = None
        if self._queue and not self._pod.over_limit():
            self._launch(self._queue.pop(0))
        self._update_queue_label()
        # A deferred "stop when the spend limit is hit" lands here, once the
        # run it was waiting for has actually finished.
        self._pod.run_finished()

    # ------------------------------------------------------------------ #
    # Player
    # ------------------------------------------------------------------ #

    def _play(self, path: str):
        if not path or not Path(path).exists():
            return
        self._open_player(path, None)

    def _open_player(self, path: str, playlist):
        self._close_player()
        # Every player in this app closes itself once the video ends, and
        # closing destroys it, so the file it played is free again.
        dlg = VideoPlayerDialog(path, self, playlist=playlist, auto_close=True)
        dlg.closed.connect(lambda d=dlg: self._forget_player(d))
        self._player = dlg
        dlg.show()

    def _close_player(self):
        dlg, self._player = self._player, None
        if dlg is None:
            return
        try:
            dlg.close()          # runs release() via closeEvent
        except RuntimeError:     # already destroyed by WA_DeleteOnClose
            pass

    def _forget_player(self, dlg):
        if self._player is dlg:
            self._player = None

    def _on_files_deleting(self, paths: list):
        """The player holds its file open; close it before the delete runs."""
        dlg = self._player
        if dlg is None:
            return
        try:
            if dlg.holds(paths):
                self._close_player()
        except RuntimeError:
            self._player = None

    def _play_list(self, paths: list):
        """Library playback: plays the selection back-to-back and closes
        itself when the last one ends."""
        paths = [p for p in paths if p and Path(p).exists()]
        if not paths:
            return
        self._open_player(paths[0], paths)

    def _on_files_deleted(self, paths: list):
        """A file deleted in one tab is gone for the others too — the Library
        and the Extend tab often point at the same folder, and a tile for a
        file that no longer exists is worse than a slightly stale count."""
        sender = self.sender()
        for browser in (self._image_browser, self._video_browser, self._library.browser):
            if browser is not sender:
                browser.remove_paths(paths)

    def _send_to_extend(self, path: Path):
        """Library → Extend: select the video in the Extend tab (switching the
        Extend folder to the library folder if it lives elsewhere)."""
        path = Path(path)
        self._tabs.setCurrentIndex(TAB_INDEX["video"])
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

    def _reuse_settings(self, video_path: Path, wf_path: Path, entry: dict):
        """Library → Reuse Settings: switch to the tab this run was made on,
        reload its prompt/LoRAs/seed/steps/source, and let the user tweak
        before pressing Create/Extend themselves — nothing is queued here."""
        settings = entry.get("settings") or {}
        # Only the video (Extend) panel ever writes a video_input_mode, and
        # only the Text → Video panel (or the embedded-metadata fallback, for
        # a graph with no loader node) sets text_to_video.
        if settings.get("video_input_mode"):
            kind = "video"
        elif settings.get("text_to_video"):
            kind = "text"
        else:
            kind = "image"
        panel = self._panels[kind]
        browser = self._video_browser if kind == "video" else self._image_browser
        self._tabs.setCurrentIndex(TAB_INDEX[kind])

        wf_dir = Path((self.config.get("workflow_dir", "") or "").strip())
        rel = settings.get("workflow")
        if not rel:
            try:
                rel = wf_path.relative_to(wf_dir).as_posix() if str(wf_dir) else wf_path.name
            except ValueError:
                rel = wf_path.name
        if not panel.load_reused_entry(rel, entry, output_dir=video_path.parent):
            panel.append_log(f"⚠ Workflow '{rel}' is no longer on disk — pick one manually; "
                              "the prompt/settings were applied wherever they still matched.")
        panel.append_log(f"This run will save back to {video_path.parent}")

        if kind == "image":
            self._reuse_image_source(panel, video_path)
        elif kind == "video":
            self._reuse_video_source(browser, panel, entry.get("source") or "")
        else:
            panel.append_log("Reused settings from Library — text to video needs no source; "
                             "tweak the prompt, then Create.")

    def _reuse_image_source(self, panel: RunPanel, video_path: Path):
        """The image an I2V run started from is often a temp/staged upload
        that's long gone by the time someone reviews the result — the
        finished video is always right there, so its first frame is pulled
        as a stand-in starting image instead of hunting for the original."""
        try:
            cache_dir = Path(tempfile.gettempdir()) / "ComfyUI_Video_Creator_reuse"
            cache_dir.mkdir(parents=True, exist_ok=True)
            # Strip whatever the run that made this video appended (its own
            # workflow label + timestamp) so the new run's own label+stamp
            # doesn't get bolted on top of a copy that's already there.
            labels = _workflow_labels(self.config.get("workflow_dir", ""))
            base = _base_stem(video_path.stem, labels)
            frame_path = cache_dir / f"{base}.png"
            ok = extract_thumbnail(self._ffmpeg(), video_path, frame_path)
        except OSError as e:
            ok = False
            panel.append_log(f"⚠ Could not extract a starting frame from {video_path.name}: {e}")
        if ok:
            panel.set_source(frame_path)
            panel.append_log(f"Reused settings — starting image is {video_path.name}'s first frame")
        else:
            panel.append_log(
                f"⚠ Couldn't extract a starting frame from {video_path.name} — pick a source image, then Create.")

    def _reuse_video_source(self, browser: MediaBrowser, panel: RunPanel, source_name: str):
        candidate = Path(browser.folder) / source_name if (browser.folder and source_name) else None
        if candidate is not None and candidate.exists():
            if not browser.grid.select_key(str(candidate)):
                panel.set_source(candidate)
            panel.append_log(f"Reused settings from Library — source: {source_name}")
        elif source_name:
            # Moved or deleted outside the app — rescan so the grid matches
            # what's actually on disk instead of leaving a stale/missing pick.
            browser.refresh()
            panel.append_log(f"⚠ Source '{source_name}' wasn't found in {browser.folder or '(no folder set)'} "
                              "— rescanned that folder. Pick a replacement video, then Extend.")
        else:
            panel.append_log("Reused settings from Library (no source recorded for this run — pick one, then Extend).")

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
        if self._pod.pod_id and self._pod.owned and self.config.get("runpod_auto_stop_on_exit", True):
            ans = QMessageBox.question(
                self, "Stop the pod?",
                f"Stop RunPod pod {self._pod.pod_id} before quitting?\n\n"
                "Leaving it running keeps billing until you stop it in the console.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Yes,
            )
            if ans == QMessageBox.StandardButton.Cancel:
                event.ignore()
                return
            if ans == QMessageBox.StandardButton.Yes:
                self._pod.shutdown()
        self._close_player()
        if self._queue_dlg is not None:
            self._queue_dlg.close()
        self._image_browser.shutdown()
        self._video_browser.shutdown()
        self._library.shutdown()
        self.config.save()
        event.accept()
