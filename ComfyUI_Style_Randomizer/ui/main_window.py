from datetime import datetime
from pathlib import Path

from PIL import Image, ImageOps
from PyQt6.QtCore import Qt, QSize, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QIcon, QPainter, QImage
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QLabel, QPushButton, QLineEdit,
    QProgressBar, QListWidget, QGroupBox, QVBoxLayout, QHBoxLayout,
    QSplitter, QFileDialog, QAbstractItemView, QPlainTextEdit, QCheckBox,
    QStatusBar,
)

from config import ConfigManager
from worker import BatchStyleWorker, load_prompts, IMAGE_EXTS
from ui.styles import COLORS
from ui.settings_dialog import SettingsDialog
from ui.prompt_editor import PromptEditorDialog

THUMB_SIZE = 120


# ------------------------------------------------------------------ #
# Background image loader
# ------------------------------------------------------------------ #

class ImageLoaderThread(QThread):
    image_ready      = pyqtSignal(QImage, str, str)  # img, abs_path, label
    finished_loading = pyqtSignal(int)

    def __init__(self, input_dir: Path):
        super().__init__()
        self._input_dir = input_dir
        self._cancelled = False

    def cancel(self):
        self._cancelled = True

    def run(self):
        try:
            images = sorted(
                (p for p in self._input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTS),
                key=lambda p: p.name.lower(),
            )
        except OSError:
            self.finished_loading.emit(0)
            return

        loaded = 0
        for img_path in images:
            if self._cancelled:
                return
            try:
                pil = Image.open(img_path)
                pil = ImageOps.exif_transpose(pil).convert("RGBA")
                data = pil.tobytes("raw", "RGBA")
                img  = QImage(data, pil.width, pil.height, QImage.Format.Format_RGBA8888)
            except Exception:
                img = QImage(str(img_path))
            if img.isNull():
                continue
            img = img.scaled(
                THUMB_SIZE, THUMB_SIZE,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.image_ready.emit(img, str(img_path), img_path.name)
            loaded += 1

        self.finished_loading.emit(loaded)


# ------------------------------------------------------------------ #
# Thumbnail grid
# ------------------------------------------------------------------ #

class ThumbnailGrid(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setViewMode(QListWidget.ViewMode.IconMode)
        self.setIconSize(QSize(THUMB_SIZE, THUMB_SIZE))
        self.setGridSize(QSize(THUMB_SIZE + 12, THUMB_SIZE + 28))
        self.setSpacing(4)
        self.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.setWrapping(True)
        self.setUniformItemSizes(True)
        self.setStyleSheet(
            f"QListWidget {{ background-color: {COLORS['bg_medium']};"
            f" border: 1px solid {COLORS['border']}; border-radius: 3px; }}"
            f"QListWidget::item {{ border: 1px solid transparent; border-radius: 3px; }}"
        )

    def add_item(self, img: QImage, key: str, label: str):
        pix    = QPixmap.fromImage(img)
        canvas = QPixmap(THUMB_SIZE, THUMB_SIZE)
        canvas.fill(Qt.GlobalColor.black)
        painter = QPainter(canvas)
        painter.drawPixmap((THUMB_SIZE - pix.width()) // 2,
                           (THUMB_SIZE - pix.height()) // 2, pix)
        painter.end()
        from PyQt6.QtWidgets import QListWidgetItem
        item = QListWidgetItem(QIcon(canvas), label)
        item.setData(Qt.ItemDataRole.UserRole, key)
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)
        self.addItem(item)

    def all_paths(self) -> list[Path]:
        return [Path(self.item(i).data(Qt.ItemDataRole.UserRole))
                for i in range(self.count())]


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self, config: ConfigManager, base_dir: Path):
        super().__init__()
        self._config  = config
        self._base_dir = base_dir
        self._prompts: list[str] = []
        self._worker: BatchStyleWorker | None = None
        self._loader: ImageLoaderThread | None = None

        self._build_ui()
        self._load_initial_state()

    # ------------------------------------------------------------------ #
    # UI construction
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        self.setWindowTitle("ComfyUI Style Randomizer")
        self.setMinimumSize(1100, 700)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setSpacing(8)
        root.setContentsMargins(12, 12, 12, 12)

        # Header
        hdr_row = QHBoxLayout()
        hdr_lbl = QLabel("ComfyUI Style Randomizer")
        hdr_lbl.setObjectName("header")
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()
        self._mode_lbl = QLabel("● Local")
        self._mode_lbl.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        hdr_row.addWidget(self._mode_lbl)
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("small_btn")
        settings_btn.setFixedWidth(100)
        settings_btn.clicked.connect(self._open_settings)
        hdr_row.addWidget(settings_btn)
        root.addLayout(hdr_row)

        # Path selectors
        paths_box = QGroupBox("Paths")
        paths_v   = QVBoxLayout(paths_box)
        paths_v.setSpacing(6)

        self._input_edit  = self._add_path_row(paths_v, "Input Folder:",  "input_dir",    folder=True)
        self._output_edit = self._add_path_row(paths_v, "Output Folder:", "output_dir",   folder=True)
        self._wf_edit     = self._add_path_row(paths_v, "Workflow JSON:", "workflow_path", folder=False,
                                                file_filter="JSON Files (*.json)")
        self._pr_edit     = self._add_path_row(paths_v, "Prompts File:",  "prompts_file", folder=False,
                                                file_filter="Text Files (*.txt)", extra_btn=("Edit", self._open_prompt_editor))

        skip_row = QHBoxLayout()
        self._skip_cb = QCheckBox("Skip already-processed images  (checks output folder by filename stem)")
        self._skip_cb.setChecked(self._config.get("skip_existing", True))
        self._skip_cb.toggled.connect(lambda v: self._config.set("skip_existing", v))
        skip_row.addWidget(self._skip_cb)
        skip_row.addStretch()
        paths_v.addLayout(skip_row)

        root.addWidget(paths_box)

        # Splitter: thumbnails | prompts+log
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left — thumbnails
        left_w = QWidget()
        left_v = QVBoxLayout(left_w)
        left_v.setContentsMargins(0, 0, 0, 0)
        self._img_count_lbl = QLabel("Images: 0")
        self._img_count_lbl.setObjectName("subtitle")
        left_v.addWidget(self._img_count_lbl)
        self._thumb_grid = ThumbnailGrid()
        left_v.addWidget(self._thumb_grid)
        splitter.addWidget(left_w)

        # Right — prompts list + log
        right_w = QWidget()
        right_v = QVBoxLayout(right_w)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(6)

        prompt_group = QGroupBox("Style Prompts")
        pg_v = QVBoxLayout(prompt_group)
        self._prompt_count_lbl = QLabel("0 prompts loaded")
        self._prompt_count_lbl.setObjectName("subtitle")
        pg_v.addWidget(self._prompt_count_lbl)
        self._prompt_list = QListWidget()
        self._prompt_list.setMaximumHeight(190)
        pg_v.addWidget(self._prompt_list)
        right_v.addWidget(prompt_group)

        log_group = QGroupBox("Processing Log")
        lg_v = QVBoxLayout(log_group)
        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        lg_v.addWidget(self._log_view)
        right_v.addWidget(log_group, stretch=1)

        splitter.addWidget(right_w)
        splitter.setSizes([620, 430])
        root.addWidget(splitter, stretch=1)

        # Bottom — progress + controls
        bottom_row = QHBoxLayout()
        self._progress = QProgressBar()
        self._progress.setFormat("%v / %m")
        self._progress.setValue(0)
        bottom_row.addWidget(self._progress, stretch=1)

        self._start_btn = QPushButton("Start")
        self._start_btn.setFixedWidth(100)
        self._start_btn.clicked.connect(self._start)
        bottom_row.addWidget(self._start_btn)

        self._cancel_btn = QPushButton("Cancel")
        self._cancel_btn.setObjectName("cancel_btn")
        self._cancel_btn.setFixedWidth(100)
        self._cancel_btn.setEnabled(False)
        self._cancel_btn.clicked.connect(self._cancel)
        bottom_row.addWidget(self._cancel_btn)

        root.addLayout(bottom_row)

        # Status bar
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._update_status()

    def _add_path_row(self, parent_layout, label: str, config_key: str,
                       folder: bool, file_filter: str = "",
                       extra_btn: tuple | None = None) -> QLineEdit:
        row  = QHBoxLayout()
        lbl  = QLabel(label)
        lbl.setFixedWidth(112)
        edit = QLineEdit()
        edit.setText(self._config.get(config_key, ""))
        edit.setPlaceholderText("Browse or paste path…")
        edit.editingFinished.connect(lambda: self._on_path_edited(edit, config_key))

        browse_btn = QPushButton("Browse")
        browse_btn.setObjectName("small_btn")
        browse_btn.setFixedWidth(70)
        browse_btn.clicked.connect(lambda: self._browse_path(edit, config_key, folder, file_filter))

        row.addWidget(lbl)
        row.addWidget(edit)
        row.addWidget(browse_btn)

        if extra_btn:
            btn_label, callback = extra_btn
            xbtn = QPushButton(btn_label)
            xbtn.setObjectName("small_btn")
            xbtn.setFixedWidth(50)
            xbtn.clicked.connect(callback)
            row.addWidget(xbtn)

        parent_layout.addLayout(row)
        return edit

    # ------------------------------------------------------------------ #
    # Path handling
    # ------------------------------------------------------------------ #

    def _browse_path(self, edit: QLineEdit, config_key: str, folder: bool, file_filter: str):
        if folder:
            path = QFileDialog.getExistingDirectory(self, "Select Folder", edit.text())
        else:
            path, _ = QFileDialog.getOpenFileName(self, "Select File", edit.text(), file_filter)
        if path:
            edit.setText(path)
            self._on_path_edited(edit, config_key)

    def _on_path_edited(self, edit: QLineEdit, config_key: str):
        self._config.set(config_key, edit.text())
        if config_key == "input_dir":
            self._reload_images()
        elif config_key == "prompts_file":
            self._reload_prompts()

    # ------------------------------------------------------------------ #
    # Data loading
    # ------------------------------------------------------------------ #

    def _load_initial_state(self):
        self._reload_images()
        self._reload_prompts()
        self._update_mode_label()

    def _reload_images(self):
        input_dir = Path(self._config.get("input_dir", ""))
        if not input_dir.is_dir():
            return
        if self._loader:
            self._loader.cancel()
            self._loader.wait()
        self._thumb_grid.clear()
        self._img_count_lbl.setText("Loading…")
        self._loader = ImageLoaderThread(input_dir)
        self._loader.image_ready.connect(
            lambda img, key, lbl: self._thumb_grid.add_item(img, key, lbl)
        )
        self._loader.finished_loading.connect(self._on_images_loaded)
        self._loader.start()

    def _on_images_loaded(self, count: int):
        self._img_count_lbl.setText(f"Images: {count}")
        self._progress.setMaximum(max(count, 1))

    def _reload_prompts(self):
        prompts_file = Path(self._config.get("prompts_file", ""))
        if not prompts_file.is_file():
            return
        try:
            self._prompts = load_prompts(prompts_file)
        except Exception:
            self._prompts = []
        self._refresh_prompt_list()

    def _refresh_prompt_list(self):
        self._prompt_list.clear()
        for i, p in enumerate(self._prompts):
            preview = p.replace("\n", " ")[:90]
            self._prompt_list.addItem(f"{i+1}.  {preview}")
        n = len(self._prompts)
        self._prompt_count_lbl.setText(f"{n} style prompt{'s' if n != 1 else ''} loaded")

    # ------------------------------------------------------------------ #
    # Dialogs
    # ------------------------------------------------------------------ #

    def _open_prompt_editor(self):
        prompts_file = Path(self._config.get("prompts_file", ""))
        if not prompts_file.is_file():
            self._append_log("Select a prompts file first.")
            return
        dlg = PromptEditorDialog(prompts_file, self)
        if dlg.exec():
            self._reload_prompts()

    def _open_settings(self):
        dlg = SettingsDialog(self._config, self)
        if dlg.exec():
            self._config.save()
            self._update_mode_label()
            self._update_status()

    # ------------------------------------------------------------------ #
    # Worker control
    # ------------------------------------------------------------------ #

    def _start(self):
        images = self._thumb_grid.all_paths()
        if not images:
            self._append_log("No images found. Select an input folder.")
            return
        if not self._prompts:
            self._append_log("No prompts loaded. Select a prompts file.")
            return
        if not Path(self._config.get("workflow_path", "")).is_file():
            self._append_log("No workflow JSON selected.")
            return
        if not self._config.get("output_dir", ""):
            self._append_log("No output folder selected.")
            return

        self._config.save()
        self._progress.setValue(0)
        self._progress.setMaximum(len(images))
        self._start_btn.setEnabled(False)
        self._cancel_btn.setEnabled(True)

        self._worker = BatchStyleWorker(
            config=self._config.get_all(),
            prompts=self._prompts,
            image_paths=images,
        )
        self._worker.progress.connect(lambda cur, _: self._progress.setValue(cur))
        self._worker.log.connect(self._append_log)
        self._worker.all_done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _cancel(self):
        if self._worker:
            self._worker.cancel()
        self._cancel_btn.setEnabled(False)

    def _on_done(self):
        self._append_log("All done!")
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

    def _on_error(self, msg: str):
        self._append_log(f"ERROR: {msg}")
        self._start_btn.setEnabled(True)
        self._cancel_btn.setEnabled(False)

    # ------------------------------------------------------------------ #
    # UI helpers
    # ------------------------------------------------------------------ #

    def _append_log(self, msg: str):
        now = datetime.now().strftime("%H:%M:%S")
        self._log_view.appendPlainText(f"[{now}] {msg}")

    def _update_mode_label(self):
        mode = self._config.get("mode", "local")
        if mode == "runpod":
            self._mode_lbl.setText("● RunPod")
            self._mode_lbl.setStyleSheet(f"color: {COLORS['warning']}; font-weight: bold;")
        else:
            self._mode_lbl.setText("● Local")
            self._mode_lbl.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")

    def _update_status(self):
        mode = self._config.get("mode", "local")
        url  = (self._config.get("runpod_url", "")
                if mode == "runpod"
                else self._config.get("comfyui_url", "http://127.0.0.1:8000"))
        self._status.showMessage(f"ComfyUI:  {url}")

    def closeEvent(self, event):
        if self._loader:
            self._loader.cancel()
        if self._worker:
            self._worker.cancel()
        self._config.save()
        super().closeEvent(event)
