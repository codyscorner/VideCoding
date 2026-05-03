"""AI Image Studio v2.0.0"""

import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTextEdit, QComboBox, QSlider, QSpinBox,
    QGroupBox, QFileDialog, QProgressBar, QSizePolicy, QTabWidget,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

VERSION = "2.0.0"

SETTINGS_FILE = Path(__file__).parent / "settings.json"
WORKFLOWS_DIR = Path(__file__).parent / "Comfy_Workflows"
DROPPED_DIR   = Path(__file__).parent / "dropped_images"
UPLOAD_DIR    = Path(__file__).parent / "upload_temp"

WORKFLOWS_DIR.mkdir(exist_ok=True)
DROPPED_DIR.mkdir(exist_ok=True)
UPLOAD_DIR.mkdir(exist_ok=True)

# ------------------------------------------------------------------ #
# Size presets
# ------------------------------------------------------------------ #

SIZE_PRESETS = [
    ("512 × 512   — Square (small)",        512,   512),
    ("768 × 768   — Square (medium)",       768,   768),
    ("1024 × 1024 — Square (standard)",    1024,  1024),
    ("768 × 1024  — Portrait (3:4)",        768,  1024),
    ("1024 × 1344 — Portrait (3:4 large)", 1024,  1344),
    ("1024 × 768  — Landscape (4:3)",      1024,   768),
    ("1344 × 768  — Landscape (7:4)",      1344,   768),
    ("1920 × 1080 — Full HD wallpaper",    1920,  1080),
    ("2560 × 1440 — 2K / QHD wallpaper",  2560,  1440),
    ("3840 × 2160 — 4K UHD wallpaper",    3840,  2160),
    ("2560 × 1080 — UltraWide FHD",       2560,  1080),
    ("3440 × 1440 — UltraWide QHD",       3440,  1440),
    ("3840 × 1600 — UltraWide 4K",        3840,  1600),
    ("5120 × 1440 — Super UltraWide",     5120,  1440),
]

ASPECT_RATIOS = ["1:1", "16:9", "9:16", "4:3", "3:4", "3:2", "2:3", "21:9"]
RESOLUTIONS   = ["1K", "2K", "4K"]

# ------------------------------------------------------------------ #
# Theme
# ------------------------------------------------------------------ #

BG      = "#13131f"
BG_MED  = "#1c1c2e"
BG_LT   = "#252540"
ACCENT  = "#6c5ce7"
ACCENT2 = "#7d6ff0"
FG      = "#e0e0f0"
FG_DIM  = "#7070a0"
BORDER  = "#2e2e50"
SUCCESS = "#4caf8a"
ERROR   = "#ff6b6b"

STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {BG};
        color: {FG};
        font-family: "Segoe UI";
        font-size: 10pt;
    }}
    QTabWidget::pane {{
        border: 1px solid {BORDER};
        border-radius: 4px;
        background-color: {BG};
    }}
    QTabBar::tab {{
        background-color: {BG_LT};
        color: {FG_DIM};
        border: 1px solid {BORDER};
        border-bottom: none;
        border-radius: 4px 4px 0 0;
        padding: 8px 24px;
        font-size: 10pt;
        font-weight: bold;
        margin-right: 2px;
    }}
    QTabBar::tab:selected {{
        background-color: {ACCENT};
        color: white;
        border-color: {ACCENT};
    }}
    QTabBar::tab:hover:!selected {{ background-color: {BG_MED}; color: {FG}; }}
    QGroupBox {{
        color: {ACCENT};
        font-weight: bold;
        font-size: 10pt;
        border: 1px solid {BORDER};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 4px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
        padding: 0 4px;
    }}
    QLabel {{ color: {FG}; }}
    QTextEdit {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 6px;
        font-size: 10pt;
    }}
    QTextEdit:focus {{ border: 1px solid {ACCENT}; }}
    QComboBox {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 10px;
    }}
    QComboBox::drop-down {{ border: none; width: 24px; }}
    QComboBox QAbstractItemView {{
        background-color: {BG_MED};
        color: {FG};
        selection-background-color: {ACCENT};
    }}
    QSlider::groove:horizontal {{
        background: {BG_LT};
        height: 6px;
        border-radius: 3px;
    }}
    QSlider::handle:horizontal {{
        background: {ACCENT};
        width: 16px;
        height: 16px;
        margin: -5px 0;
        border-radius: 8px;
    }}
    QSlider::sub-page:horizontal {{ background: {ACCENT}; border-radius: 3px; }}
    QSpinBox {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QPushButton {{
        background-color: {ACCENT};
        color: white;
        font-weight: bold;
        border: none;
        border-radius: 4px;
        padding: 8px 20px;
        font-size: 10pt;
    }}
    QPushButton:hover {{ background-color: {ACCENT2}; }}
    QPushButton:disabled {{ background-color: {BG_LT}; color: {FG_DIM}; }}
    QPushButton#secondary {{
        background-color: {BG_LT};
        color: {FG_DIM};
        border: 1px solid {BORDER};
    }}
    QPushButton#secondary:hover {{ background-color: {BG_MED}; color: {FG}; }}
    QPushButton#danger {{
        background-color: {BG_LT};
        color: {ERROR};
        border: 1px solid {BORDER};
    }}
    QPushButton#danger:hover {{ background-color: {ERROR}; color: white; }}
    QProgressBar {{
        background-color: {BG_LT};
        border: 1px solid {BORDER};
        border-radius: 4px;
        height: 20px;
        text-align: center;
        color: white;
        font-size: 8pt;
    }}
    QProgressBar::chunk {{ background-color: {ACCENT}; border-radius: 3px; }}
    QScrollArea {{ border: none; background: transparent; }}
"""

# ------------------------------------------------------------------ #
# Settings
# ------------------------------------------------------------------ #

def load_settings() -> dict:
    if SETTINGS_FILE.exists():
        try:
            return json.loads(SETTINGS_FILE.read_text())
        except Exception:
            pass
    return {}

def save_settings(s: dict):
    try:
        SETTINGS_FILE.write_text(json.dumps(s, indent=2))
    except Exception:
        pass

# ------------------------------------------------------------------ #
# Workflow introspection helpers
# ------------------------------------------------------------------ #

def _find_node_by_class(workflow: dict, class_type: str) -> tuple[str, dict] | None:
    for k, v in workflow.items():
        if v.get("class_type") == class_type:
            return k, v
    return None

def _patch_workflow_t2i(workflow: dict, prompt: str, width: int, height: int,
                         seed: int, steps: int) -> dict:
    """Patch a text-to-image workflow with prompt, size, seed, steps."""
    import random
    if seed < 0:
        seed = random.randint(0, 2**31)

    # Patch prompt — PrimitiveStringMultiline or CLIPTextEncode positive
    for _, v in workflow.items():
        if v.get("class_type") == "PrimitiveStringMultiline":
            v["inputs"]["value"] = prompt
            break
    else:
        # fallback: find positive CLIPTextEncode (not negative)
        for _, v in workflow.items():
            if v.get("class_type") == "CLIPTextEncode":
                meta = v.get("_meta", {}).get("title", "").lower()
                if "neg" not in meta:
                    v["inputs"]["text"] = prompt
                    break

    # Patch size — EmptySD3LatentImage or EmptyLatentImage
    for cls in ("EmptySD3LatentImage", "EmptyLatentImage"):
        result = _find_node_by_class(workflow, cls)
        if result:
            _, node = result
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            break

    # Patch KSampler seed + steps
    result = _find_node_by_class(workflow, "KSampler")
    if result:
        _, node = result
        node["inputs"]["seed"] = seed
        node["inputs"]["steps"] = steps

    # Bust cache on any other seed fields
    for v in workflow.values():
        inp = v.get("inputs", {})
        if "noise_seed" in inp:
            inp["noise_seed"] = seed

    return workflow


def _patch_workflow_edit(workflow: dict, prompt: str, seed: int, steps: int) -> dict:
    """Patch an image-edit workflow with prompt, seed, steps."""
    import random
    if seed < 0:
        seed = random.randint(0, 2**31)

    # Patch prompt node
    for _, v in workflow.items():
        if v.get("class_type") == "PrimitiveStringMultiline":
            v["inputs"]["value"] = prompt
            break

    # Patch KSampler
    result = _find_node_by_class(workflow, "KSampler")
    if result:
        _, node = result
        node["inputs"]["seed"] = seed
        node["inputs"]["steps"] = steps

    # Bust noise_seed fields
    for v in workflow.values():
        inp = v.get("inputs", {})
        if "noise_seed" in inp:
            inp["noise_seed"] = seed
        if "seed" in inp and isinstance(inp["seed"], int):
            inp["seed"] = seed

    return workflow

# ------------------------------------------------------------------ #
# Shared ComfyUI worker
# ------------------------------------------------------------------ #

class ComfyWorker(QThread):
    status   = pyqtSignal(str)
    progress = pyqtSignal(int)
    done     = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, comfy_url: str, workflow: dict, output_dir: Path,
                 filename_prefix: str = "ComfyUI"):
        super().__init__()
        url = comfy_url.rstrip("/")
        if not url.startswith("http"):
            url = "http://" + url
        self._url = url
        self._workflow = workflow
        self._output_dir = output_dir
        self._prefix = filename_prefix
        self._client_id = str(__import__("uuid").uuid4())

    def run(self):
        try:
            import requests, time

            self.status.emit("Queuing prompt...")
            self.progress.emit(10)

            resp = requests.post(
                f"{self._url}/prompt",
                json={"prompt": self._workflow, "client_id": self._client_id},
                timeout=30,
            )
            resp.raise_for_status()
            prompt_id = resp.json()["prompt_id"]

            self.status.emit("Generating...")
            elapsed = 0
            while True:
                time.sleep(3)
                elapsed += 3
                if elapsed > 600:
                    raise RuntimeError("Timed out after 10 minutes")

                try:
                    q = requests.get(f"{self._url}/queue", timeout=10).json()
                    running = [item[1] for item in q.get("queue_running", [])]
                    pending = [item[1] for item in q.get("queue_pending", [])]

                    if prompt_id in running or prompt_id in pending:
                        self.status.emit(f"Generating... ({elapsed}s)")
                        self.progress.emit(min(10 + elapsed, 85))
                        continue

                    h = requests.get(f"{self._url}/history/{prompt_id}", timeout=10).json()
                    if prompt_id in h:
                        hist = h
                        break

                except Exception as e:
                    self.status.emit(f"Polling... ({elapsed}s)")
                    continue

            self.status.emit("Downloading result...")
            self.progress.emit(90)

            hist_data = hist[prompt_id]
            outputs = hist_data.get("outputs", {})

            img_info = None
            for node_out in outputs.values():
                imgs = node_out.get("images", [])
                if imgs:
                    img_info = imgs[0]
                    break

            if not img_info:
                raise RuntimeError(
                    f"No output image found. "
                    f"Status: {hist_data.get('status', {}).get('status_str', 'unknown')}"
                )

            params = {
                "filename": img_info["filename"],
                "subfolder": img_info.get("subfolder", ""),
                "type": img_info.get("type", "output"),
            }
            img_resp = requests.get(f"{self._url}/view", params=params, timeout=60)
            img_resp.raise_for_status()

            self._output_dir.mkdir(parents=True, exist_ok=True)
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            out_path = self._output_dir / f"{self._prefix}_{ts}.png"
            out_path.write_bytes(img_resp.content)

            self.progress.emit(100)
            self.done.emit(str(out_path))

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")

    def _upload_image(self, img_path: str, requests, filename: str) -> str:
        with open(img_path, "rb") as f:
            resp = requests.post(
                f"{self._url}/upload/image",
                files={"image": (filename, f, "image/png")},
                data={"type": "input", "overwrite": "true"},
                timeout=60,
            )
        resp.raise_for_status()
        return resp.json()["name"]


# ------------------------------------------------------------------ #
# Image Editor worker (uploads images then runs ComfyWorker logic)
# ------------------------------------------------------------------ #

class EditorWorker(ComfyWorker):
    def __init__(self, comfy_url: str, workflow: dict, output_dir: Path,
                 ref_images: list[str], target_size: tuple[int, int]):
        super().__init__(comfy_url, workflow, output_dir, "edited")
        self._ref_images = ref_images
        self._target_size = target_size

    def run(self):
        try:
            import requests, random, string
            from PIL import Image as PILImage

            # Clear upload temp
            for f in UPLOAD_DIR.iterdir():
                try:
                    f.unlink()
                except Exception:
                    pass

            # Find LoadImage nodes in order
            load_nodes = [
                (k, v) for k, v in self._workflow.items()
                if v.get("class_type") == "LoadImage"
            ]
            load_nodes.sort(key=lambda x: x[0])

            target_w, target_h = self._target_size

            for i, img_path in enumerate(self._ref_images[:len(load_nodes)]):
                node_id, _ = load_nodes[i]
                self.status.emit(f"Uploading image {i+1}...")
                self.progress.emit(5 + i * 8)

                rand = ''.join(random.choices(string.ascii_lowercase, k=8))
                upload_name = f"img_{rand}.png"
                upload_path = UPLOAD_DIR / upload_name

                img = PILImage.open(img_path).convert("RGB")
                # Resize first image to drive output dimensions
                if i == 0:
                    img = img.resize((target_w, target_h), PILImage.LANCZOS)
                # 1-pixel tweak busts ComfyUI content cache
                px = img.load()
                r, g, b = px[0, 0]
                px[0, 0] = ((r + 1) % 256, g, b)
                img.save(str(upload_path))

                uploaded_name = self._upload_image(str(upload_path), requests, upload_name)
                self._workflow[node_id]["inputs"]["image"] = uploaded_name

            # Now run the base ComfyWorker poll loop
            super().run()

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


# ------------------------------------------------------------------ #
# Image drop slot widget
# ------------------------------------------------------------------ #

class ImageSlot(QLabel):
    image_changed = pyqtSignal(str)

    def __init__(self, label: str, parent=None):
        super().__init__(parent)
        self._path: str | None = None
        self._label = label
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedSize(160, 160)
        self.setAcceptDrops(True)
        self._set_empty()
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def _set_empty(self):
        self._path = None
        self.setPixmap(QPixmap())
        self.setText(f"+ {self._label}\n\nDrag & drop\nor click")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_LT};
                border: 2px dashed {BORDER};
                border-radius: 6px;
                color: {FG_DIM};
                font-size: 9pt;
            }}
        """)

    def set_image(self, path: str, copy: bool = True):
        if self._path and Path(self._path).exists():
            self._archive(self._path)

        if copy and Path(path).parent != DROPPED_DIR:
            safe_name = Path(path).name.replace(" ", "_")
            dest = DROPPED_DIR / safe_name
            if dest.exists():
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = DROPPED_DIR / f"{Path(safe_name).stem}_{ts}{Path(safe_name).suffix}"
            shutil.copy2(path, dest)
            path = str(dest)

        self._path = path
        pix = QPixmap(path).scaled(
            156, 156,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self.setPixmap(pix)
        self.setText("")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {BG_MED};
                border: 2px solid {ACCENT};
                border-radius: 6px;
            }}
        """)
        self.image_changed.emit(path)

    def clear_image(self):
        if self._path and Path(self._path).exists():
            self._archive(self._path)
        self._set_empty()
        self.image_changed.emit("")

    def _archive(self, path: str):
        archive_dir = DROPPED_DIR / "archive"
        archive_dir.mkdir(exist_ok=True)
        src = Path(path)
        if src.exists() and src.parent == DROPPED_DIR:
            dest = archive_dir / src.name
            if dest.exists():
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                dest = archive_dir / f"{src.stem}_{ts}{src.suffix}"
            shutil.move(str(src), str(dest))

    @property
    def path(self) -> str | None:
        return self._path

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            path, _ = QFileDialog.getOpenFileName(
                self, f"Select {self._label}",
                str(Path.home()),
                "Images (*.png *.jpg *.jpeg *.webp *.bmp)"
            )
            if path:
                self.set_image(path)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).suffix.lower() in {".png", ".jpg", ".jpeg", ".webp", ".bmp"}:
                self.set_image(path)


# ------------------------------------------------------------------ #
# Shared preview panel
# ------------------------------------------------------------------ #

class PreviewPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_path: str | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        preview_layout.setContentsMargins(4, 4, 4, 4)

        self._preview = QLabel("Output will appear here")
        self._preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._preview.setStyleSheet(
            f"color: {FG_DIM}; background-color: {BG_MED}; border-radius: 4px;"
        )
        self._preview.setMinimumSize(400, 400)
        self._preview.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        preview_layout.addWidget(self._preview)
        layout.addWidget(preview_group, stretch=1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._save_btn = QPushButton("💾  Save As...")
        self._save_btn.setObjectName("secondary")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._save_as)
        self._open_btn = QPushButton("📁  Open Folder")
        self._open_btn.setObjectName("secondary")
        self._open_btn.setEnabled(False)
        self._open_btn.clicked.connect(self._open_folder)
        btn_row.addWidget(self._save_btn)
        btn_row.addSpacing(8)
        btn_row.addWidget(self._open_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def show_image(self, path: str):
        self._last_path = path
        self._save_btn.setEnabled(True)
        self._open_btn.setEnabled(True)
        pix = QPixmap(path)
        if not pix.isNull():
            self._update_pixmap(pix)

    def _update_pixmap(self, pix: QPixmap):
        scaled = pix.scaled(
            self._preview.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        self._preview.setPixmap(scaled)

    def set_message(self, msg: str):
        self._preview.setPixmap(QPixmap())
        self._preview.setText(msg)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._last_path:
            pix = QPixmap(self._last_path)
            if not pix.isNull():
                self._update_pixmap(pix)

    def _save_as(self):
        if not self._last_path:
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save Image", self._last_path,
            "Images (*.png *.jpg *.webp)"
        )
        if dest:
            shutil.copy2(self._last_path, dest)

    def _open_folder(self):
        if self._last_path:
            subprocess.Popen(f'explorer "{Path(self._last_path).parent}"')


# ------------------------------------------------------------------ #
# Tab 1 — Text to Image
# ------------------------------------------------------------------ #

class TextToImageTab(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._worker: ComfyWorker | None = None
        self._build_ui()
        self._reload_workflows()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)

        # URL
        url_group = QGroupBox("ComfyUI Server URL")
        url_row = QHBoxLayout(url_group)
        self._url_edit = QTextEdit(self._settings.get("t2i_url", "http://127.0.0.1:8188"))
        self._url_edit.setFixedHeight(36)
        self._url_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._url_edit.textChanged.connect(self._save_state)
        url_row.addWidget(self._url_edit)
        left.addWidget(url_group)

        # Workflow
        wf_group = QGroupBox("Workflow")
        wf_row = QHBoxLayout(wf_group)
        self._wf_combo = QComboBox()
        wf_reload = QPushButton("↻")
        wf_reload.setObjectName("secondary")
        wf_reload.setFixedSize(34, 34)
        wf_reload.setToolTip("Reload workflows")
        wf_reload.clicked.connect(self._reload_workflows)
        wf_row.addWidget(self._wf_combo, stretch=1)
        wf_row.addWidget(wf_reload)
        left.addWidget(wf_group)

        # Prompt
        prompt_group = QGroupBox("Prompt")
        prompt_layout = QVBoxLayout(prompt_group)
        self._prompt = QTextEdit()
        self._prompt.setPlaceholderText("Describe the image you want to generate...")
        self._prompt.setPlainText(self._settings.get("t2i_prompt", ""))
        self._prompt.setFixedHeight(120)
        self._prompt.textChanged.connect(self._save_state)
        prompt_layout.addWidget(self._prompt)
        left.addWidget(prompt_group)

        # Size
        size_group = QGroupBox("Output Size")
        size_layout = QVBoxLayout(size_group)
        self._size_combo = QComboBox()
        for label, w, h in SIZE_PRESETS:
            self._size_combo.addItem(label, (w, h))
        saved_size = tuple(self._settings.get("t2i_size", [1024, 1024]))
        for i, (_, w, h) in enumerate(SIZE_PRESETS):
            if (w, h) == saved_size:
                self._size_combo.setCurrentIndex(i)
                break
        self._size_combo.currentIndexChanged.connect(self._save_state)
        size_layout.addWidget(self._size_combo)
        left.addWidget(size_group)

        # Steps + Seed
        params_row = QHBoxLayout()

        steps_group = QGroupBox("Steps")
        steps_inner = QHBoxLayout(steps_group)
        self._steps = QSlider(Qt.Orientation.Horizontal)
        self._steps.setRange(1, 60)
        self._steps.setValue(self._settings.get("t2i_steps", 20))
        self._steps_lbl = QLabel(str(self._steps.value()))
        self._steps_lbl.setFixedWidth(28)
        self._steps_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._steps_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold;")
        self._steps.valueChanged.connect(lambda v: (self._steps_lbl.setText(str(v)), self._save_state()))
        steps_inner.addWidget(self._steps)
        steps_inner.addWidget(self._steps_lbl)
        params_row.addWidget(steps_group, stretch=2)

        seed_group = QGroupBox("Seed  (-1 = random)")
        seed_inner = QHBoxLayout(seed_group)
        self._seed = QSpinBox()
        self._seed.setRange(-1, 2147483647)
        self._seed.setValue(-1)
        rand_btn = QPushButton("🎲")
        rand_btn.setObjectName("secondary")
        rand_btn.setFixedSize(30, 30)
        rand_btn.clicked.connect(lambda: self._seed.setValue(-1))
        seed_inner.addWidget(self._seed)
        seed_inner.addWidget(rand_btn)
        params_row.addWidget(seed_group, stretch=1)
        left.addLayout(params_row)

        # Output folder
        out_group = QGroupBox("Output Folder")
        out_row = QHBoxLayout(out_group)
        self._out_edit = QTextEdit(self._settings.get("t2i_output_dir",
                                   str(Path.home() / "AI_Images")))
        self._out_edit.setFixedHeight(36)
        self._out_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        out_browse = QPushButton("...")
        out_browse.setObjectName("secondary")
        out_browse.setFixedSize(36, 36)
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_edit)
        out_row.addWidget(out_browse)
        left.addWidget(out_group)

        left.addStretch()

        self._gen_btn = QPushButton("✨  Generate")
        self._gen_btn.setFixedHeight(50)
        self._gen_btn.setStyleSheet(f"font-size:13pt; background-color:{ACCENT}; border-radius:6px;")
        self._gen_btn.clicked.connect(self._generate)
        left.addWidget(self._gen_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        left.addWidget(self._progress)

        self._status = QLabel("Select a workflow and enter a prompt")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color:{FG_DIM}; font-size:9pt;")
        self._status.setWordWrap(True)
        left.addWidget(self._status)

        root.addLayout(left, stretch=1)

        self._preview_panel = PreviewPanel()
        root.addWidget(self._preview_panel, stretch=2)

    def _reload_workflows(self):
        self._wf_combo.clear()
        workflows = sorted(WORKFLOWS_DIR.glob("t2i_*.json"))
        for wf in workflows:
            self._wf_combo.addItem(wf.stem.replace("_", " ").replace("t2i ", ""), str(wf))
        if not workflows:
            self._wf_combo.addItem("No workflows found — add t2i_*.json to Comfy_Workflows/", "")
        saved_wf = self._settings.get("t2i_workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == saved_wf:
                self._wf_combo.setCurrentIndex(i)
                break

    def _save_state(self):
        if not hasattr(self, '_prompt'):
            return
        self._settings["t2i_url"] = self._url_edit.toPlainText().strip()
        self._settings["t2i_prompt"] = self._prompt.toPlainText()
        self._settings["t2i_steps"] = self._steps.value()
        self._settings["t2i_workflow"] = self._wf_combo.currentData() or ""
        self._settings["t2i_size"] = list(self._size_combo.currentData() or (1024, 1024))
        save_settings(self._settings)

    def _browse_output(self):
        f = QFileDialog.getExistingDirectory(self, "Select output folder",
                                              self._out_edit.toPlainText().strip())
        if f:
            self._out_edit.setPlainText(f)
            self._settings["t2i_output_dir"] = f
            save_settings(self._settings)

    def _generate(self):
        url = self._url_edit.toPlainText().strip()
        workflow_path = self._wf_combo.currentData()
        prompt = self._prompt.toPlainText().strip()
        out = self._out_edit.toPlainText().strip()

        if not workflow_path or not Path(workflow_path).exists():
            self._status.setText("Select a valid workflow.")
            return
        if not prompt:
            self._status.setText("Enter a prompt.")
            return
        if not out:
            self._status.setText("Select an output folder.")
            return

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        w, h = self._size_combo.currentData()
        workflow = _patch_workflow_t2i(workflow, prompt, w, h,
                                        self._seed.value(), self._steps.value())

        self._gen_btn.setEnabled(False)
        self._progress.setValue(0)
        self._preview_panel.set_message("Generating...")
        self._save_state()

        self._worker = ComfyWorker(url, workflow, Path(out), "t2i")
        self._worker.status.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str):
        self._gen_btn.setEnabled(True)
        self._status.setText(f"Done! {Path(path).name}")
        self._preview_panel.show_image(path)

    def _on_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Error — see preview panel")
        self._preview_panel.set_message(f"Error:\n{msg[:400]}")


# ------------------------------------------------------------------ #
# Tab 2 — Image Editor
# ------------------------------------------------------------------ #

class ImageEditorTab(QWidget):
    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._worker: EditorWorker | None = None
        self._build_ui()
        self._reload_workflows()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left = QVBoxLayout()
        left.setSpacing(10)

        # URL
        url_group = QGroupBox("ComfyUI Server URL")
        url_row = QHBoxLayout(url_group)
        self._url_edit = QTextEdit(self._settings.get("edit_url", "http://127.0.0.1:8188"))
        self._url_edit.setFixedHeight(36)
        self._url_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self._url_edit.textChanged.connect(self._save_state)
        url_row.addWidget(self._url_edit)
        left.addWidget(url_group)

        # Workflow
        wf_group = QGroupBox("Workflow")
        wf_row = QHBoxLayout(wf_group)
        self._wf_combo = QComboBox()
        wf_reload = QPushButton("↻")
        wf_reload.setObjectName("secondary")
        wf_reload.setFixedSize(34, 34)
        wf_reload.setToolTip("Reload workflows")
        wf_reload.clicked.connect(self._reload_workflows)
        wf_row.addWidget(self._wf_combo, stretch=1)
        wf_row.addWidget(wf_reload)
        left.addWidget(wf_group)

        # Output size
        size_group = QGroupBox("Output Size")
        size_layout = QVBoxLayout(size_group)
        self._size_combo = QComboBox()
        for label, w, h in SIZE_PRESETS:
            self._size_combo.addItem(label, (w, h))
        saved_size = tuple(self._settings.get("edit_size", [1024, 1024]))
        for i, (_, w, h) in enumerate(SIZE_PRESETS):
            if (w, h) == saved_size:
                self._size_combo.setCurrentIndex(i)
                break
        self._size_combo.currentIndexChanged.connect(self._save_state)
        size_layout.addWidget(self._size_combo)
        left.addWidget(size_group)

        # Image slots
        refs_group = QGroupBox("Reference Images  (drag & drop or click)")
        refs_layout = QVBoxLayout(refs_group)
        refs_layout.setContentsMargins(6, 10, 6, 16)
        slot_row = QHBoxLayout()
        slot_row.setSpacing(8)
        self._slots: list[ImageSlot] = []
        saved_images = self._settings.get("edit_images", [None, None, None, None])
        for i, lbl in enumerate(["Image 1", "Image 2", "Image 3", "Image 4"]):
            slot = ImageSlot(lbl)
            slot.image_changed.connect(self._save_state)
            self._slots.append(slot)
            slot_row.addWidget(slot)
            saved = saved_images[i] if i < len(saved_images) else None
            if saved and Path(saved).exists():
                slot.set_image(saved, copy=False)
        refs_layout.addLayout(slot_row)
        left.addWidget(refs_group)

        clear_row = QHBoxLayout()
        clear_row.addStretch()
        clear_lbl = QLabel('<a href="#" style="color:#ff6b6b; font-size:8pt; text-decoration:none;">✕ clear all</a>')
        clear_lbl.setTextInteractionFlags(Qt.TextInteractionFlag.LinksAccessibleByMouse)
        clear_lbl.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_lbl.linkActivated.connect(lambda _: self._clear_slots())
        clear_row.addWidget(clear_lbl)
        left.addLayout(clear_row)

        # Prompt
        instr_group = QGroupBox("Prompt / Instruction")
        instr_layout = QVBoxLayout(instr_group)
        self._instruction = QTextEdit()
        self._instruction.setPlaceholderText(
            "Describe the edit, e.g.:\n"
            "\"Place these two people on a beach at sunset\""
        )
        self._instruction.setPlainText(self._settings.get("edit_prompt", ""))
        self._instruction.setFixedHeight(100)
        self._instruction.textChanged.connect(self._save_state)
        instr_layout.addWidget(self._instruction)
        left.addWidget(instr_group)

        # Steps + Seed
        params_row = QHBoxLayout()

        steps_group = QGroupBox("Steps")
        steps_inner = QHBoxLayout(steps_group)
        self._steps = QSlider(Qt.Orientation.Horizontal)
        self._steps.setRange(1, 60)
        self._steps.setValue(self._settings.get("edit_steps", 6))
        self._steps_lbl = QLabel(str(self._steps.value()))
        self._steps_lbl.setFixedWidth(28)
        self._steps_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._steps_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold;")
        self._steps.valueChanged.connect(lambda v: (self._steps_lbl.setText(str(v)), self._save_state()))
        steps_inner.addWidget(self._steps)
        steps_inner.addWidget(self._steps_lbl)
        params_row.addWidget(steps_group, stretch=2)

        seed_group = QGroupBox("Seed  (-1 = random)")
        seed_inner = QHBoxLayout(seed_group)
        self._seed = QSpinBox()
        self._seed.setRange(-1, 2147483647)
        self._seed.setValue(-1)
        rand_btn = QPushButton("🎲")
        rand_btn.setObjectName("secondary")
        rand_btn.setFixedSize(30, 30)
        rand_btn.clicked.connect(lambda: self._seed.setValue(-1))
        seed_inner.addWidget(self._seed)
        seed_inner.addWidget(rand_btn)
        params_row.addWidget(seed_group, stretch=1)
        left.addLayout(params_row)

        # Output folder
        out_group = QGroupBox("Output Folder")
        out_row = QHBoxLayout(out_group)
        self._out_edit = QTextEdit(self._settings.get("edit_output_dir",
                                   str(Path.home() / "AI_Images")))
        self._out_edit.setFixedHeight(36)
        self._out_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        out_browse = QPushButton("...")
        out_browse.setObjectName("secondary")
        out_browse.setFixedSize(36, 36)
        out_browse.clicked.connect(self._browse_output)
        out_row.addWidget(self._out_edit)
        out_row.addWidget(out_browse)
        left.addWidget(out_group)

        left.addStretch()

        self._compose_btn = QPushButton("🎨  Generate Edit")
        self._compose_btn.setFixedHeight(50)
        self._compose_btn.setStyleSheet(f"font-size:13pt; background-color:{ACCENT}; border-radius:6px;")
        self._compose_btn.clicked.connect(self._compose)
        left.addWidget(self._compose_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        left.addWidget(self._progress)

        self._status = QLabel("Load reference images and describe your edit")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color:{FG_DIM}; font-size:9pt;")
        self._status.setWordWrap(True)
        left.addWidget(self._status)

        root.addLayout(left, stretch=1)

        self._preview_panel = PreviewPanel()
        root.addWidget(self._preview_panel, stretch=2)

    def _reload_workflows(self):
        self._wf_combo.clear()
        workflows = sorted(WORKFLOWS_DIR.glob("edit_*.json"))
        for wf in workflows:
            self._wf_combo.addItem(wf.stem.replace("_", " ").replace("edit ", ""), str(wf))
        if not workflows:
            self._wf_combo.addItem("No workflows found — add edit_*.json to Comfy_Workflows/", "")
        saved_wf = self._settings.get("edit_workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == saved_wf:
                self._wf_combo.setCurrentIndex(i)
                break

    def _save_state(self):
        if not hasattr(self, '_instruction'):
            return
        self._settings["edit_url"] = self._url_edit.toPlainText().strip()
        self._settings["edit_prompt"] = self._instruction.toPlainText()
        self._settings["edit_steps"] = self._steps.value()
        self._settings["edit_workflow"] = self._wf_combo.currentData() or ""
        self._settings["edit_images"] = [s.path for s in self._slots]
        self._settings["edit_size"] = list(self._size_combo.currentData() or (1024, 1024))
        save_settings(self._settings)

    def _browse_output(self):
        f = QFileDialog.getExistingDirectory(self, "Select output folder",
                                              self._out_edit.toPlainText().strip())
        if f:
            self._out_edit.setPlainText(f)
            self._settings["edit_output_dir"] = f
            save_settings(self._settings)

    def _clear_slots(self):
        for slot in self._slots:
            slot.clear_image()

    def _compose(self):
        url = self._url_edit.toPlainText().strip()
        workflow_path = self._wf_combo.currentData()
        instruction = self._instruction.toPlainText().strip()
        out = self._out_edit.toPlainText().strip()
        ref_images = [s.path for s in self._slots if s.path]

        if not workflow_path or not Path(workflow_path).exists():
            self._status.setText("Select a valid workflow.")
            return
        if not ref_images:
            self._status.setText("Add at least one reference image.")
            return
        if not instruction:
            self._status.setText("Enter a prompt or instruction.")
            return
        if not out:
            self._status.setText("Select an output folder.")
            return

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        workflow = _patch_workflow_edit(workflow, instruction,
                                        self._seed.value(), self._steps.value())

        w, h = self._size_combo.currentData()

        self._compose_btn.setEnabled(False)
        self._progress.setValue(0)
        self._preview_panel.set_message("Sending to ComfyUI...")
        self._save_state()

        self._worker = EditorWorker(url, workflow, Path(out), ref_images, (w, h))
        self._worker.status.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str):
        self._compose_btn.setEnabled(True)
        self._status.setText(f"Done! {Path(path).name}")
        self._preview_panel.show_image(path)

    def _on_error(self, msg: str):
        self._compose_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Error — see preview panel")
        self._preview_panel.set_message(f"Error:\n{msg[:400]}")


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = load_settings()

        self.setWindowTitle(f"AI Image Studio  v{VERSION}")
        self.setMinimumSize(1200, 820)
        self.resize(1500, 940)
        self.setStyleSheet(STYLESHEET)

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        title = QLabel("AI Image Studio")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"font-size:18pt; font-weight:bold; color:{ACCENT};")
        root.addWidget(title)

        tabs = QTabWidget()
        self._t2i_tab = TextToImageTab(self._settings)
        self._edit_tab = ImageEditorTab(self._settings)
        tabs.addTab(self._t2i_tab, "✨  Text to Image")
        tabs.addTab(self._edit_tab, "🎨  Image Editor")
        root.addWidget(tabs)

    def closeEvent(self, event):
        save_settings(self._settings)
        event.accept()


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #

if __name__ == "__main__":
    import traceback
    log_file = Path(__file__).parent / "error_log.txt"
    try:
        app = QApplication(sys.argv)
        app.setApplicationName("AI Image Studio")
        window = MainWindow()
        window.show()
        sys.exit(app.exec())
    except Exception as e:
        with open(log_file, "w") as f:
            f.write(traceback.format_exc())
        raise
