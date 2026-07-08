"""AI Image Studio v3.1.0"""

import base64
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
    QScrollArea, QFrame, QMessageBox, QLineEdit, QStackedWidget,
    QGridLayout, QCheckBox, QListWidget, QListWidgetItem, QDialog,
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QDragEnterEvent, QDropEvent

VERSION = "3.1.0"

SETTINGS_FILE = Path(__file__).parent / "settings.json"
API_KEYS_FILE = Path(__file__).parent / "api_keys.json"
HISTORY_FILE  = Path(__file__).parent / "generation_history.json"
WORKFLOWS_DIR = Path(__file__).parent / "Comfy_Workflows"
DROPPED_DIR   = Path(__file__).parent / "dropped_images"
UPLOAD_DIR    = Path(__file__).parent / "upload_temp"

for _d in (WORKFLOWS_DIR, DROPPED_DIR, UPLOAD_DIR):
    _d.mkdir(exist_ok=True)

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
    QLineEdit {{
        background-color: {BG_LT};
        color: {FG};
        border: 1px solid {BORDER};
        border-radius: 4px;
        padding: 5px 8px;
        font-size: 10pt;
    }}
    QLineEdit:focus {{ border: 1px solid {ACCENT}; }}
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
    QScrollBar:vertical {{
        background: {BG_LT};
        width: 8px;
        border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {BORDER};
        border-radius: 4px;
        min-height: 24px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
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

def load_api_keys() -> dict:
    if API_KEYS_FILE.exists():
        try:
            return json.loads(API_KEYS_FILE.read_text())
        except Exception:
            pass
    return {}

def save_api_keys(keys: dict):
    try:
        API_KEYS_FILE.write_text(json.dumps(keys, indent=2))
    except Exception:
        pass

# ------------------------------------------------------------------ #
# Generation history  (prompt recall)
# ------------------------------------------------------------------ #

_HISTORY_MAX = 500

def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
        except Exception:
            pass
    return []

def add_history_entry(entry: dict):
    try:
        hist = load_history()
        hist.insert(0, entry)
        del hist[_HISTORY_MAX:]
        HISTORY_FILE.write_text(json.dumps(hist, indent=2), encoding="utf-8")
    except Exception:
        pass

def find_history_entry(path: str) -> dict | None:
    target = str(Path(path))
    for e in load_history():
        if str(Path(e.get("path", ""))) == target:
            return e
    return None

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
    import random
    if seed < 0:
        seed = random.randint(0, 2**31)

    for _, v in workflow.items():
        if v.get("class_type") == "PrimitiveStringMultiline":
            v["inputs"]["value"] = prompt
            break
    else:
        for _, v in workflow.items():
            if v.get("class_type") == "CLIPTextEncode":
                meta = v.get("_meta", {}).get("title", "").lower()
                if "neg" not in meta:
                    v["inputs"]["text"] = prompt
                    break

    for cls in ("EmptySD3LatentImage", "EmptyLatentImage"):
        result = _find_node_by_class(workflow, cls)
        if result:
            _, node = result
            node["inputs"]["width"] = width
            node["inputs"]["height"] = height
            break

    result = _find_node_by_class(workflow, "KSampler")
    if result:
        _, node = result
        node["inputs"]["seed"] = seed
        node["inputs"]["steps"] = steps

    for v in workflow.values():
        inp = v.get("inputs", {})
        if "noise_seed" in inp:
            inp["noise_seed"] = seed

    return workflow


def _patch_workflow_edit(workflow: dict, prompt: str, seed: int, steps: int) -> dict:
    import random
    if seed < 0:
        seed = random.randint(0, 2**31)

    for _, v in workflow.items():
        if v.get("class_type") == "PrimitiveStringMultiline":
            v["inputs"]["value"] = prompt
            break

    result = _find_node_by_class(workflow, "KSampler")
    if result:
        _, node = result
        node["inputs"]["seed"] = seed
        node["inputs"]["steps"] = steps

    for v in workflow.values():
        inp = v.get("inputs", {})
        if "noise_seed" in inp:
            inp["noise_seed"] = seed
        if "seed" in inp and isinstance(inp["seed"], int):
            inp["seed"] = seed

    return workflow


def _patch_workflow_i2i(workflow: dict, prompt: str, seed: int, steps: int,
                        denoise: float) -> dict:
    """Patch an img2img workflow: prompt (if given), seed, steps, and denoise strength."""
    import random
    if seed < 0:
        seed = random.randint(0, 2**31)

    if prompt:
        for _, v in workflow.items():
            if v.get("class_type") == "PrimitiveStringMultiline":
                v["inputs"]["value"] = prompt
                break
        else:
            for _, v in workflow.items():
                if v.get("class_type") == "CLIPTextEncode":
                    meta = v.get("_meta", {}).get("title", "").lower()
                    if "neg" not in meta:
                        v["inputs"]["text"] = prompt
                        break

    result = _find_node_by_class(workflow, "KSampler")
    if result:
        _, node = result
        node["inputs"]["seed"] = seed
        node["inputs"]["steps"] = steps

    for v in workflow.values():
        inp = v.get("inputs", {})
        if "noise_seed" in inp:
            inp["noise_seed"] = seed
        if "seed" in inp and isinstance(inp["seed"], int):
            inp["seed"] = seed
        if "denoise" in inp and isinstance(inp["denoise"], (int, float)):
            inp["denoise"] = round(denoise, 2)

    return workflow

# ------------------------------------------------------------------ #
# Local ComfyUI workers
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

                except Exception:
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

            for f in UPLOAD_DIR.iterdir():
                try:
                    f.unlink()
                except Exception:
                    pass

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
                if i == 0:
                    img = img.resize((target_w, target_h), PILImage.LANCZOS)
                px = img.load()
                r, g, b = px[0, 0]
                px[0, 0] = ((r + 1) % 256, g, b)
                img.save(str(upload_path))

                uploaded_name = self._upload_image(str(upload_path), requests, upload_name)
                self._workflow[node_id]["inputs"]["image"] = uploaded_name

            super().run()

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


# ------------------------------------------------------------------ #
# RunPod workers
# ------------------------------------------------------------------ #

class RunPodWorker(QThread):
    """Submits a text-to-image workflow to a RunPod serverless endpoint."""
    status   = pyqtSignal(str)
    progress = pyqtSignal(int)
    done     = pyqtSignal(str)
    error    = pyqtSignal(str)

    def __init__(self, api_key: str, endpoint_id: str, workflow: dict,
                 output_dir: Path, prefix: str = "runpod"):
        super().__init__()
        self._api_key = api_key
        self._endpoint_id = endpoint_id.strip()
        self._workflow = workflow
        self._output_dir = output_dir
        self._prefix = prefix
        self._base = f"https://api.runpod.io/v2/{self._endpoint_id}"

    def _headers(self) -> dict:
        return {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

    def _poll_and_save(self, requests, job_id: str):
        import time
        elapsed = 0
        while True:
            time.sleep(4)
            elapsed += 4
            if elapsed > 900:
                raise RuntimeError("RunPod job timed out after 15 minutes")

            r = requests.get(
                f"{self._base}/status/{job_id}",
                headers=self._headers(),
                timeout=30,
            )
            r.raise_for_status()
            data = r.json()
            status = data.get("status", "")

            if status in ("IN_QUEUE", "IN_PROGRESS"):
                self.status.emit(f"RunPod: {status} ({elapsed}s)")
                self.progress.emit(min(20 + elapsed, 85))
            elif status == "FAILED":
                raise RuntimeError(f"RunPod job failed: {data.get('error', 'unknown')}")
            elif status == "COMPLETED":
                output = data.get("output", {})
                images = output.get("images", [])
                if not images:
                    raise RuntimeError("RunPod returned no images in output")

                self.status.emit("Saving image...")
                self.progress.emit(92)

                img_entry = images[0]
                raw_b64 = img_entry.get("data") or img_entry.get("image", "")
                if not raw_b64:
                    raise RuntimeError("Unexpected RunPod output format — no base64 data")

                raw_bytes = base64.b64decode(raw_b64)
                self._output_dir.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                out_path = self._output_dir / f"{self._prefix}_{ts}.png"
                out_path.write_bytes(raw_bytes)

                self.progress.emit(100)
                self.done.emit(str(out_path))
                return
            else:
                self.status.emit(f"RunPod: {status} ({elapsed}s)")
                self.progress.emit(min(20 + elapsed, 85))

    def run(self):
        try:
            import requests

            self.status.emit("Submitting to RunPod...")
            self.progress.emit(10)

            resp = requests.post(
                f"{self._base}/run",
                json={"input": {"prompt": self._workflow}},
                headers=self._headers(),
                timeout=30,
            )
            resp.raise_for_status()
            job_id = resp.json()["id"]

            self.status.emit(f"Job queued ({job_id[:8]}...)")
            self.progress.emit(15)
            self._poll_and_save(requests, job_id)

        except Exception as e:
            import traceback
            self.error.emit(f"{e}\n\n{traceback.format_exc()}")


class RunPodEditorWorker(RunPodWorker):
    """Uploads reference images as base64 and runs a scene-compose workflow on RunPod."""

    def __init__(self, api_key: str, endpoint_id: str, workflow: dict,
                 output_dir: Path, ref_images: list[str], target_size: tuple[int, int]):
        super().__init__(api_key, endpoint_id, workflow, output_dir, "runpod_edit")
        self._ref_images = ref_images
        self._target_size = target_size

    def run(self):
        try:
            import requests, random, string
            from PIL import Image as PILImage

            load_nodes = [
                (k, v) for k, v in self._workflow.items()
                if v.get("class_type") == "LoadImage"
            ]
            load_nodes.sort(key=lambda x: x[0])

            target_w, target_h = self._target_size
            image_inputs = []

            for i, img_path in enumerate(self._ref_images[:len(load_nodes)]):
                node_id, _ = load_nodes[i]
                self.status.emit(f"Encoding image {i+1}...")
                self.progress.emit(5 + i * 8)

                rand = ''.join(random.choices(string.ascii_lowercase, k=8))
                upload_name = f"img_{rand}.png"

                img = PILImage.open(img_path).convert("RGB")
                if i == 0:
                    img = img.resize((target_w, target_h), PILImage.LANCZOS)
                px = img.load()
                r, g, b = px[0, 0]
                px[0, 0] = ((r + 1) % 256, g, b)

                import io
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                encoded = base64.b64encode(buf.getvalue()).decode()

                image_inputs.append({"name": upload_name, "image": encoded})
                self._workflow[node_id]["inputs"]["image"] = upload_name

            self.status.emit("Submitting to RunPod...")
            self.progress.emit(35)

            resp = requests.post(
                f"{self._base}/run",
                json={"input": {"prompt": self._workflow, "images": image_inputs}},
                headers=self._headers(),
                timeout=60,
            )
            resp.raise_for_status()
            job_id = resp.json()["id"]

            self.status.emit(f"Job queued ({job_id[:8]}...)")
            self.progress.emit(40)
            self._poll_and_save(requests, job_id)

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
        self._preview.setMinimumSize(200, 200)
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
# Connection widget  (Local ComfyUI  /  RunPod Serverless)
# ------------------------------------------------------------------ #

class ConnectionWidget(QGroupBox):
    """Toggle between Local ComfyUI and RunPod with the appropriate fields."""
    changed = pyqtSignal()

    def __init__(self, settings: dict, api_keys: dict, prefix: str, parent=None):
        super().__init__("Connection", parent)
        self._settings = settings
        self._api_keys = api_keys
        self._prefix = prefix
        self._build_ui()

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setSpacing(6)

        mode_row = QHBoxLayout()
        mode_lbl = QLabel("Mode:")
        mode_lbl.setFixedWidth(42)
        self._mode_combo = QComboBox()
        self._mode_combo.addItem("Local ComfyUI", "local")
        self._mode_combo.addItem("RunPod Serverless", "runpod")
        saved_mode = self._settings.get(f"{self._prefix}_conn_mode", "local")
        idx = 1 if saved_mode == "runpod" else 0
        self._mode_combo.setCurrentIndex(idx)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_change)
        mode_row.addWidget(mode_lbl)
        mode_row.addWidget(self._mode_combo, stretch=1)
        outer.addLayout(mode_row)

        # Local ComfyUI row (show/hide instead of stacked widget to avoid height reservation)
        self._local_widget = QWidget()
        ll = QHBoxLayout(self._local_widget)
        ll.setContentsMargins(0, 0, 0, 0)
        ll.setSpacing(6)
        url_lbl = QLabel("URL:")
        url_lbl.setFixedWidth(30)
        self._url_edit = QLineEdit(self._settings.get(f"{self._prefix}_url",
                                                       "http://127.0.0.1:8188"))
        self._url_edit.textChanged.connect(self._on_change)
        ll.addWidget(url_lbl)
        ll.addWidget(self._url_edit)
        outer.addWidget(self._local_widget)

        # RunPod rows
        self._runpod_widget = QWidget()
        rl = QVBoxLayout(self._runpod_widget)
        rl.setContentsMargins(0, 0, 0, 0)
        rl.setSpacing(4)
        key_row = QHBoxLayout()
        key_lbl = QLabel("Key:")
        key_lbl.setFixedWidth(30)
        self._key_edit = QLineEdit()
        self._key_edit.setPlaceholderText("rp_xxxxxxxxxxxx")
        self._key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_edit.setText(self._api_keys.get("runpod_api_key", ""))
        self._key_edit.textChanged.connect(self._on_change)
        key_row.addWidget(key_lbl)
        key_row.addWidget(self._key_edit)
        ep_row = QHBoxLayout()
        ep_lbl = QLabel("EP:")
        ep_lbl.setFixedWidth(30)
        self._ep_edit = QLineEdit()
        self._ep_edit.setPlaceholderText("abc1def234ghij56")
        self._ep_edit.setText(self._settings.get(f"{self._prefix}_runpod_endpoint", ""))
        self._ep_edit.textChanged.connect(self._on_change)
        ep_row.addWidget(ep_lbl)
        ep_row.addWidget(self._ep_edit)
        rl.addLayout(key_row)
        rl.addLayout(ep_row)
        outer.addWidget(self._runpod_widget)

        self._local_widget.setVisible(idx == 0)
        self._runpod_widget.setVisible(idx == 1)

    def _on_mode_change(self, idx: int):
        self._local_widget.setVisible(idx == 0)
        self._runpod_widget.setVisible(idx == 1)
        self._on_change()

    def _on_change(self):
        mode = self._mode_combo.currentData()
        self._settings[f"{self._prefix}_conn_mode"] = mode
        self._settings[f"{self._prefix}_url"] = self._url_edit.text().strip()
        self._settings[f"{self._prefix}_runpod_endpoint"] = self._ep_edit.text().strip()
        key = self._key_edit.text().strip()
        if key:
            self._api_keys["runpod_api_key"] = key
            save_api_keys(self._api_keys)
        save_settings(self._settings)
        self.changed.emit()

    @property
    def mode(self) -> str:
        return self._mode_combo.currentData()

    @property
    def local_url(self) -> str:
        return self._url_edit.text().strip()

    @property
    def runpod_api_key(self) -> str:
        return self._key_edit.text().strip()

    @property
    def runpod_endpoint(self) -> str:
        return self._ep_edit.text().strip()


# ------------------------------------------------------------------ #
# Library thumbnail card
# ------------------------------------------------------------------ #

_CARD_W  = 174
_CARD_H  = 210
_THUMB_W = 158
_THUMB_H = 138
_LIB_COLS = 4


class ThumbnailCard(QFrame):
    selected_signal = pyqtSignal(str)

    def __init__(self, img_path: str, favorite: bool = False, parent=None):
        super().__init__(parent)
        self._path = img_path
        self._favorite = favorite
        self.setFixedSize(_CARD_W, _CARD_H)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build_ui()
        self._set_style(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(3)

        self._thumb = QLabel()
        self._thumb.setFixedSize(_THUMB_W, _THUMB_H)
        self._thumb.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb.setStyleSheet(f"background-color: {BG}; border-radius: 3px;")
        pix = QPixmap(self._path)
        if not pix.isNull():
            scaled = pix.scaled(_THUMB_W, _THUMB_H,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._thumb.setPixmap(scaled)
        else:
            self._thumb.setText("?")
        layout.addWidget(self._thumb)

        self._name = Path(self._path).name
        if len(self._name) > 22:
            self._name = self._name[:19] + "..."
        self._name_lbl = QLabel()
        self._name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_lbl.setStyleSheet(f"color: {FG}; font-size: 8pt; background: transparent; border: none;")
        layout.addWidget(self._name_lbl)
        self._update_name_label()

        try:
            mtime = Path(self._path).stat().st_mtime
            date_str = datetime.fromtimestamp(mtime).strftime("%m/%d  %H:%M")
        except Exception:
            date_str = ""
        date_lbl = QLabel(date_str)
        date_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        date_lbl.setStyleSheet(f"color: {FG_DIM}; font-size: 7pt; background: transparent; border: none;")
        layout.addWidget(date_lbl)

    def _set_style(self, selected: bool):
        border = ACCENT if selected else BORDER
        bg = BG_MED if selected else BG_LT
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {bg};
                border: 2px solid {border};
                border-radius: 6px;
            }}
        """)

    def set_selected(self, selected: bool):
        self._set_style(selected)

    def _update_name_label(self):
        if self._favorite:
            self._name_lbl.setText(f'<span style="color:#f5c04a;">★</span> {self._name}')
        else:
            self._name_lbl.setText(self._name)

    def set_favorite(self, favorite: bool):
        self._favorite = favorite
        self._update_name_label()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.selected_signal.emit(self._path)
        super().mousePressEvent(event)

    @property
    def path(self) -> str:
        return self._path


# ------------------------------------------------------------------ #
# A/B compare dialog
# ------------------------------------------------------------------ #

class CompareDialog(QDialog):
    def __init__(self, path_a: str, path_b: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Compare  A ⇆ B")
        self.resize(1280, 760)
        self.setStyleSheet(STYLESHEET)
        self._pix_a = QPixmap(path_a)
        self._pix_b = QPixmap(path_b)

        layout = QHBoxLayout(self)
        layout.setSpacing(12)
        self._img_labels: list[tuple[QLabel, QPixmap]] = []

        for tag, path, pix in (("A", path_a, self._pix_a), ("B", path_b, self._pix_b)):
            col = QVBoxLayout()
            col.setSpacing(6)

            img_lbl = QLabel()
            img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            img_lbl.setMinimumSize(300, 300)
            img_lbl.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
            img_lbl.setStyleSheet(f"background-color: {BG_MED}; border-radius: 4px;")
            self._img_labels.append((img_lbl, pix))
            col.addWidget(img_lbl, stretch=1)

            p = Path(path)
            cap = QLabel(f"<b style='color:{ACCENT};'>{tag}</b>   {p.name}")
            cap.setAlignment(Qt.AlignmentFlag.AlignCenter)
            cap.setStyleSheet(f"color:{FG}; font-size:9pt;")
            col.addWidget(cap)

            try:
                stat = p.stat()
                mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M")
                dims = f"{pix.width()} × {pix.height()}" if not pix.isNull() else "?"
                detail = QLabel(f"{dims}   ·   {stat.st_size / 1024:.0f} KB   ·   {mtime}")
            except Exception:
                detail = QLabel("")
            detail.setAlignment(Qt.AlignmentFlag.AlignCenter)
            detail.setStyleSheet(f"color:{FG_DIM}; font-size:8pt;")
            col.addWidget(detail)

            layout.addLayout(col, stretch=1)

    def _update_pixmaps(self):
        for lbl, pix in self._img_labels:
            if not pix.isNull():
                lbl.setPixmap(pix.scaled(
                    lbl.size(),
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                ))

    def showEvent(self, event):
        super().showEvent(event)
        self._update_pixmaps()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_pixmaps()


# ------------------------------------------------------------------ #
# Tab 1 — Text to Image
# ------------------------------------------------------------------ #

class TextToImageTab(QWidget):
    def __init__(self, settings: dict, api_keys: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._api_keys = api_keys
        self._worker: QThread | None = None
        self._queue: list[dict] = []
        self._queue_running = False
        self._queue_total = 0
        self._queue_done = 0
        self._queue_failed = 0
        self._active_job: dict | None = None
        self._build_ui()
        self._reload_workflows()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(4, 4, 4, 4)

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(280)
        left_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Connection (Local / RunPod)
        self._conn = ConnectionWidget(self._settings, self._api_keys, "t2i")
        left.addWidget(self._conn)

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

        # Batch queue
        queue_group = QGroupBox("Batch Queue")
        queue_layout = QVBoxLayout(queue_group)
        queue_layout.setSpacing(6)
        self._queue_list = QListWidget()
        self._queue_list.setFixedHeight(96)
        self._queue_list.setStyleSheet(
            f"QListWidget {{ background-color: {BG_LT}; border: 1px solid {BORDER};"
            f" border-radius: 4px; font-size: 8pt; color: {FG}; }}"
            f"QListWidget::item:selected {{ background-color: {ACCENT}; color: white; }}"
        )
        queue_layout.addWidget(self._queue_list)
        qbtn_row = QHBoxLayout()
        qbtn_row.setSpacing(6)
        add_q_btn = QPushButton("➕ Add to Queue")
        add_q_btn.setObjectName("secondary")
        add_q_btn.clicked.connect(self._add_to_queue)
        self._run_q_btn = QPushButton("▶ Run Queue")
        self._run_q_btn.setObjectName("secondary")
        self._run_q_btn.clicked.connect(self._run_queue)
        rm_q_btn = QPushButton("✕")
        rm_q_btn.setObjectName("secondary")
        rm_q_btn.setFixedSize(30, 30)
        rm_q_btn.setToolTip("Remove selected job")
        rm_q_btn.clicked.connect(self._remove_queue_item)
        clr_q_btn = QPushButton("🗑")
        clr_q_btn.setObjectName("secondary")
        clr_q_btn.setFixedSize(30, 30)
        clr_q_btn.setToolTip("Clear queue")
        clr_q_btn.clicked.connect(self._clear_queue)
        qbtn_row.addWidget(add_q_btn, stretch=1)
        qbtn_row.addWidget(self._run_q_btn, stretch=1)
        qbtn_row.addWidget(rm_q_btn)
        qbtn_row.addWidget(clr_q_btn)
        queue_layout.addLayout(qbtn_row)
        left.addWidget(queue_group)

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

        root.addWidget(left_scroll, stretch=1)

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
        self._settings["t2i_prompt"] = self._prompt.toPlainText()
        self._settings["t2i_steps"] = self._steps.value()
        self._settings["t2i_workflow"] = self._wf_combo.currentData() or ""
        self._settings["t2i_size"] = list(self._size_combo.currentData() or (1024, 1024))
        self._settings["t2i_output_dir"] = self._out_edit.toPlainText().strip()
        save_settings(self._settings)

    def _browse_output(self):
        f = QFileDialog.getExistingDirectory(self, "Select output folder",
                                              self._out_edit.toPlainText().strip())
        if f:
            self._out_edit.setPlainText(f)
            self._settings["t2i_output_dir"] = f
            save_settings(self._settings)

    def _collect_job(self) -> dict | None:
        """Validate the current form and return a job dict, or None (with status set)."""
        workflow_path = self._wf_combo.currentData()
        prompt = self._prompt.toPlainText().strip()
        out = self._out_edit.toPlainText().strip()

        if not workflow_path or not Path(workflow_path).exists():
            self._status.setText("Select a valid workflow.")
            return None
        if not prompt:
            self._status.setText("Enter a prompt.")
            return None
        if not out:
            self._status.setText("Select an output folder.")
            return None

        w, h = self._size_combo.currentData()
        return {
            "workflow_path": workflow_path,
            "prompt": prompt,
            "size": [w, h],
            "steps": self._steps.value(),
            "seed": self._seed.value(),
            "output_dir": out,
        }

    def _start_job(self, job: dict) -> bool:
        """Kick off one generation job. Returns False if it could not start."""
        import random

        with open(job["workflow_path"], "r", encoding="utf-8") as f:
            workflow = json.load(f)

        seed = job["seed"]
        if seed < 0:
            seed = random.randint(0, 2**31)

        w, h = job["size"]
        workflow = _patch_workflow_t2i(workflow, job["prompt"], w, h,
                                        seed, job["steps"])

        out = Path(job["output_dir"])
        if self._conn.mode == "runpod":
            api_key = self._conn.runpod_api_key
            endpoint = self._conn.runpod_endpoint
            if not api_key or not endpoint:
                self._status.setText("Enter RunPod API key and endpoint ID.")
                return False
            self._worker = RunPodWorker(api_key, endpoint, workflow, out, "t2i")
        else:
            self._worker = ComfyWorker(self._conn.local_url, workflow, out, "t2i")

        self._active_job = dict(job, seed=seed)
        self._gen_btn.setEnabled(False)
        self._run_q_btn.setEnabled(False)
        self._progress.setValue(0)
        self._preview_panel.set_message("Generating...")

        self._worker.status.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()
        return True

    def _generate(self):
        if self._worker and self._worker.isRunning():
            return
        job = self._collect_job()
        if not job:
            return
        self._queue_running = False
        self._save_state()
        self._start_job(job)

    # ---- Batch queue ---------------------------------------------- #

    def _add_to_queue(self):
        job = self._collect_job()
        if not job:
            return
        self._queue.append(job)
        self._refresh_queue_list()
        self._status.setText(f"Queued job {len(self._queue)} — "
                             f"{len(self._queue)} waiting")

    def _refresh_queue_list(self):
        self._queue_list.clear()
        for i, job in enumerate(self._queue, 1):
            w, h = job["size"]
            text = job["prompt"].replace("\n", " ")
            if len(text) > 46:
                text = text[:43] + "..."
            self._queue_list.addItem(f"{i}.  {text}   [{w}×{h}, {job['steps']}st]")
        n = len(self._queue)
        self._run_q_btn.setText(f"▶ Run Queue ({n})" if n else "▶ Run Queue")

    def _remove_queue_item(self):
        row = self._queue_list.currentRow()
        if 0 <= row < len(self._queue):
            self._queue.pop(row)
            self._refresh_queue_list()

    def _clear_queue(self):
        self._queue.clear()
        self._refresh_queue_list()

    def _run_queue(self):
        if self._worker and self._worker.isRunning():
            return
        if not self._queue:
            self._status.setText("Queue is empty — add jobs first.")
            return
        self._queue_running = True
        self._queue_total = len(self._queue)
        self._queue_done = 0
        self._queue_failed = 0
        self._start_next_queued()

    def _start_next_queued(self):
        if not self._queue:
            self._finish_queue()
            return
        job = self._queue.pop(0)
        self._refresh_queue_list()
        self._status.setText(f"Queue: job {self._queue_done + self._queue_failed + 1} "
                             f"of {self._queue_total}...")
        if not self._start_job(job):
            self._queue_failed += 1
            self._start_next_queued()

    def _finish_queue(self):
        self._queue_running = False
        self._gen_btn.setEnabled(True)
        self._run_q_btn.setEnabled(True)
        msg = f"Queue complete — {self._queue_done} done"
        if self._queue_failed:
            msg += f", {self._queue_failed} failed"
        self._status.setText(msg)

    # ---- Completion ------------------------------------------------ #

    def _record_history(self, path: str):
        job = self._active_job or {}
        add_history_entry({
            "path": str(path),
            "tab": "t2i",
            "prompt": job.get("prompt", ""),
            "workflow": job.get("workflow_path", ""),
            "size": job.get("size", []),
            "steps": job.get("steps", 0),
            "seed": job.get("seed", -1),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

    def _on_done(self, path: str):
        self._record_history(path)
        self._preview_panel.show_image(path)
        if self._queue_running:
            self._queue_done += 1
            self._start_next_queued()
        else:
            self._gen_btn.setEnabled(True)
            self._run_q_btn.setEnabled(True)
            self._status.setText(f"Done! {Path(path).name}")

    def _on_error(self, msg: str):
        self._progress.setValue(0)
        if self._queue_running:
            self._queue_failed += 1
            self._preview_panel.set_message(f"Job failed:\n{msg[:300]}")
            self._start_next_queued()
        else:
            self._gen_btn.setEnabled(True)
            self._run_q_btn.setEnabled(True)
            self._status.setText("Error — see preview panel")
            self._preview_panel.set_message(f"Error:\n{msg[:400]}")

    # ---- Prompt recall --------------------------------------------- #

    def apply_history(self, entry: dict):
        self._prompt.setPlainText(entry.get("prompt", ""))
        steps = entry.get("steps")
        if isinstance(steps, int) and steps > 0:
            self._steps.setValue(steps)
        seed = entry.get("seed")
        if isinstance(seed, int):
            self._seed.setValue(seed)
        size = entry.get("size") or []
        if len(size) == 2:
            for i in range(self._size_combo.count()):
                if self._size_combo.itemData(i) == tuple(size):
                    self._size_combo.setCurrentIndex(i)
                    break
        wf = entry.get("workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == wf:
                self._wf_combo.setCurrentIndex(i)
                break
        self._save_state()


# ------------------------------------------------------------------ #
# Tab 2 — Scene Composer
# ------------------------------------------------------------------ #

class SceneComposerTab(QWidget):
    def __init__(self, settings: dict, api_keys: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._api_keys = api_keys
        self._worker: QThread | None = None
        self._build_ui()
        self._reload_workflows()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(4, 4, 4, 4)

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(280)
        left_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Connection (Local / RunPod)
        self._conn = ConnectionWidget(self._settings, self._api_keys, "edit")
        left.addWidget(self._conn)

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

        # Image slots — 2×2 grid so each slot stays 160px wide
        refs_group = QGroupBox("Reference Images  (drag & drop or click)")
        refs_layout = QVBoxLayout(refs_group)
        refs_layout.setContentsMargins(6, 10, 6, 10)
        slot_grid = QGridLayout()
        slot_grid.setSpacing(8)
        self._slots: list[ImageSlot] = []
        saved_images = self._settings.get("edit_images", [None, None, None, None])
        for i, lbl in enumerate(["Image 1", "Image 2", "Image 3", "Image 4"]):
            slot = ImageSlot(lbl)
            slot.image_changed.connect(self._save_state)
            self._slots.append(slot)
            slot_grid.addWidget(slot, i // 2, i % 2)
            saved = saved_images[i] if i < len(saved_images) else None
            if saved and Path(saved).exists():
                slot.set_image(saved, copy=False)
        refs_layout.addLayout(slot_grid)
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
            "Describe the scene, e.g.:\n"
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

        self._compose_btn = QPushButton("🎨  Compose Scene")
        self._compose_btn.setFixedHeight(50)
        self._compose_btn.setStyleSheet(f"font-size:13pt; background-color:{ACCENT}; border-radius:6px;")
        self._compose_btn.clicked.connect(self._compose)
        left.addWidget(self._compose_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        left.addWidget(self._progress)

        self._status = QLabel("Load reference images and describe your scene")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color:{FG_DIM}; font-size:9pt;")
        self._status.setWordWrap(True)
        left.addWidget(self._status)

        root.addWidget(left_scroll, stretch=1)

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
        self._settings["edit_prompt"] = self._instruction.toPlainText()
        self._settings["edit_steps"] = self._steps.value()
        self._settings["edit_workflow"] = self._wf_combo.currentData() or ""
        self._settings["edit_images"] = [s.path for s in self._slots]
        self._settings["edit_size"] = list(self._size_combo.currentData() or (1024, 1024))
        self._settings["edit_output_dir"] = self._out_edit.toPlainText().strip()
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

        import random
        seed = self._seed.value()
        if seed < 0:
            seed = random.randint(0, 2**31)

        workflow = _patch_workflow_edit(workflow, instruction, seed, self._steps.value())

        w, h = self._size_combo.currentData()

        self._active_job = {
            "prompt": instruction,
            "workflow_path": workflow_path,
            "size": [w, h],
            "steps": self._steps.value(),
            "seed": seed,
        }

        self._compose_btn.setEnabled(False)
        self._progress.setValue(0)
        self._preview_panel.set_message("Sending to ComfyUI...")
        self._save_state()

        if self._conn.mode == "runpod":
            api_key = self._conn.runpod_api_key
            endpoint = self._conn.runpod_endpoint
            if not api_key or not endpoint:
                self._status.setText("Enter RunPod API key and endpoint ID.")
                self._compose_btn.setEnabled(True)
                return
            self._worker = RunPodEditorWorker(
                api_key, endpoint, workflow, Path(out), ref_images, (w, h)
            )
        else:
            self._worker = EditorWorker(
                self._conn.local_url, workflow, Path(out), ref_images, (w, h)
            )

        self._worker.status.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str):
        self._compose_btn.setEnabled(True)
        self._status.setText(f"Done! {Path(path).name}")
        self._preview_panel.show_image(path)
        job = getattr(self, "_active_job", None) or {}
        add_history_entry({
            "path": str(path),
            "tab": "edit",
            "prompt": job.get("prompt", ""),
            "workflow": job.get("workflow_path", ""),
            "size": job.get("size", []),
            "steps": job.get("steps", 0),
            "seed": job.get("seed", -1),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

    def _on_error(self, msg: str):
        self._compose_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Error — see preview panel")
        self._preview_panel.set_message(f"Error:\n{msg[:400]}")

    def apply_history(self, entry: dict):
        self._instruction.setPlainText(entry.get("prompt", ""))
        steps = entry.get("steps")
        if isinstance(steps, int) and steps > 0:
            self._steps.setValue(steps)
        seed = entry.get("seed")
        if isinstance(seed, int):
            self._seed.setValue(seed)
        size = entry.get("size") or []
        if len(size) == 2:
            for i in range(self._size_combo.count()):
                if self._size_combo.itemData(i) == tuple(size):
                    self._size_combo.setCurrentIndex(i)
                    break
        wf = entry.get("workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == wf:
                self._wf_combo.setCurrentIndex(i)
                break
        self._save_state()


# ------------------------------------------------------------------ #
# Tab 3 — Img2img Variations
# ------------------------------------------------------------------ #

class ImageVariationsTab(QWidget):
    def __init__(self, settings: dict, api_keys: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._api_keys = api_keys
        self._worker: QThread | None = None
        self._active_job: dict | None = None
        self._build_ui()
        self._reload_workflows()

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(12)

        left_widget = QWidget()
        left = QVBoxLayout(left_widget)
        left.setSpacing(10)
        left.setContentsMargins(4, 4, 4, 4)

        left_scroll = QScrollArea()
        left_scroll.setWidget(left_widget)
        left_scroll.setWidgetResizable(True)
        left_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        left_scroll.setMinimumWidth(280)
        left_scroll.setStyleSheet("QScrollArea { border: none; background: transparent; }")

        # Connection (Local / RunPod)
        self._conn = ConnectionWidget(self._settings, self._api_keys, "i2i")
        left.addWidget(self._conn)

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

        # Source image slot
        src_group = QGroupBox("Source Image  (drag & drop or click)")
        src_layout = QHBoxLayout(src_group)
        src_layout.setContentsMargins(6, 10, 6, 10)
        self._src_slot = ImageSlot("Source Image")
        self._src_slot.image_changed.connect(self._save_state)
        src_layout.addStretch()
        src_layout.addWidget(self._src_slot)
        src_layout.addStretch()
        left.addWidget(src_group)

        saved_src = self._settings.get("i2i_source", "")
        if saved_src and Path(saved_src).exists():
            self._src_slot.set_image(saved_src, copy=False)

        # Prompt (optional)
        prompt_group = QGroupBox("Prompt  (optional)")
        prompt_layout = QVBoxLayout(prompt_group)
        self._prompt = QTextEdit()
        self._prompt.setPlaceholderText(
            "Optional — describe the changes you want.\n"
            "Leave blank to keep the workflow's own prompt."
        )
        self._prompt.setPlainText(self._settings.get("i2i_prompt", ""))
        self._prompt.setFixedHeight(90)
        self._prompt.textChanged.connect(self._save_state)
        prompt_layout.addWidget(self._prompt)
        left.addWidget(prompt_group)

        # Output size
        size_group = QGroupBox("Output Size")
        size_layout = QVBoxLayout(size_group)
        self._size_combo = QComboBox()
        for label, w, h in SIZE_PRESETS:
            self._size_combo.addItem(label, (w, h))
        saved_size = tuple(self._settings.get("i2i_size", [1024, 1024]))
        for i, (_, w, h) in enumerate(SIZE_PRESETS):
            if (w, h) == saved_size:
                self._size_combo.setCurrentIndex(i)
                break
        self._size_combo.currentIndexChanged.connect(self._save_state)
        size_layout.addWidget(self._size_combo)
        left.addWidget(size_group)

        # Strength (denoise)
        strength_group = QGroupBox("Variation Strength  (denoise)")
        strength_inner = QHBoxLayout(strength_group)
        self._strength = QSlider(Qt.Orientation.Horizontal)
        self._strength.setRange(5, 100)
        self._strength.setValue(self._settings.get("i2i_strength", 60))
        self._strength_lbl = QLabel(f"{self._strength.value() / 100:.2f}")
        self._strength_lbl.setFixedWidth(38)
        self._strength_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._strength_lbl.setStyleSheet(f"color:{ACCENT}; font-weight:bold;")
        self._strength.valueChanged.connect(
            lambda v: (self._strength_lbl.setText(f"{v / 100:.2f}"), self._save_state()))
        strength_inner.addWidget(self._strength)
        strength_inner.addWidget(self._strength_lbl)
        hint = QLabel("Low = subtle variation  ·  High = mostly new image")
        hint.setStyleSheet(f"color:{FG_DIM}; font-size:8pt;")
        left.addWidget(strength_group)
        left.addWidget(hint)

        # Steps + Seed
        params_row = QHBoxLayout()

        steps_group = QGroupBox("Steps")
        steps_inner = QHBoxLayout(steps_group)
        self._steps = QSlider(Qt.Orientation.Horizontal)
        self._steps.setRange(1, 60)
        self._steps.setValue(self._settings.get("i2i_steps", 20))
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
        self._out_edit = QTextEdit(self._settings.get("i2i_output_dir",
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

        self._gen_btn = QPushButton("🔄  Generate Variation")
        self._gen_btn.setFixedHeight(50)
        self._gen_btn.setStyleSheet(f"font-size:13pt; background-color:{ACCENT}; border-radius:6px;")
        self._gen_btn.clicked.connect(self._generate)
        left.addWidget(self._gen_btn)

        self._progress = QProgressBar()
        self._progress.setRange(0, 100)
        left.addWidget(self._progress)

        self._status = QLabel("Load a source image and set the variation strength")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setStyleSheet(f"color:{FG_DIM}; font-size:9pt;")
        self._status.setWordWrap(True)
        left.addWidget(self._status)

        root.addWidget(left_scroll, stretch=1)

        self._preview_panel = PreviewPanel()
        root.addWidget(self._preview_panel, stretch=2)

    def _reload_workflows(self):
        self._wf_combo.clear()
        workflows = sorted(WORKFLOWS_DIR.glob("i2i_*.json"))
        for wf in workflows:
            self._wf_combo.addItem(wf.stem.replace("_", " ").replace("i2i ", ""), str(wf))
        if not workflows:
            self._wf_combo.addItem("No workflows found — add i2i_*.json to Comfy_Workflows/", "")
        saved_wf = self._settings.get("i2i_workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == saved_wf:
                self._wf_combo.setCurrentIndex(i)
                break

    def _save_state(self):
        if not hasattr(self, '_out_edit'):
            return
        self._settings["i2i_prompt"] = self._prompt.toPlainText()
        self._settings["i2i_steps"] = self._steps.value()
        self._settings["i2i_strength"] = self._strength.value()
        self._settings["i2i_workflow"] = self._wf_combo.currentData() or ""
        self._settings["i2i_size"] = list(self._size_combo.currentData() or (1024, 1024))
        self._settings["i2i_source"] = self._src_slot.path or ""
        self._settings["i2i_output_dir"] = self._out_edit.toPlainText().strip()
        save_settings(self._settings)

    def _browse_output(self):
        f = QFileDialog.getExistingDirectory(self, "Select output folder",
                                              self._out_edit.toPlainText().strip())
        if f:
            self._out_edit.setPlainText(f)
            self._settings["i2i_output_dir"] = f
            save_settings(self._settings)

    def set_source_image(self, path: str):
        """Called from the Library's Variations button."""
        if path and Path(path).exists():
            self._src_slot.set_image(path, copy=False)
            self._status.setText(f"Source: {Path(path).name}")

    def _generate(self):
        if self._worker and self._worker.isRunning():
            return

        workflow_path = self._wf_combo.currentData()
        prompt = self._prompt.toPlainText().strip()
        out = self._out_edit.toPlainText().strip()
        src = self._src_slot.path

        if not workflow_path or not Path(workflow_path).exists():
            self._status.setText("Select a valid workflow (i2i_*.json).")
            return
        if not src or not Path(src).exists():
            self._status.setText("Load a source image.")
            return
        if not out:
            self._status.setText("Select an output folder.")
            return

        with open(workflow_path, "r", encoding="utf-8") as f:
            workflow = json.load(f)

        import random
        seed = self._seed.value()
        if seed < 0:
            seed = random.randint(0, 2**31)

        denoise = self._strength.value() / 100
        workflow = _patch_workflow_i2i(workflow, prompt, seed,
                                       self._steps.value(), denoise)

        w, h = self._size_combo.currentData()

        self._active_job = {
            "prompt": prompt,
            "workflow_path": workflow_path,
            "size": [w, h],
            "steps": self._steps.value(),
            "seed": seed,
            "strength": denoise,
            "source": src,
        }

        self._gen_btn.setEnabled(False)
        self._progress.setValue(0)
        self._preview_panel.set_message("Generating variation...")
        self._save_state()

        if self._conn.mode == "runpod":
            api_key = self._conn.runpod_api_key
            endpoint = self._conn.runpod_endpoint
            if not api_key or not endpoint:
                self._status.setText("Enter RunPod API key and endpoint ID.")
                self._gen_btn.setEnabled(True)
                return
            self._worker = RunPodEditorWorker(
                api_key, endpoint, workflow, Path(out), [src], (w, h)
            )
        else:
            self._worker = EditorWorker(
                self._conn.local_url, workflow, Path(out), [src], (w, h)
            )

        self._worker.status.connect(self._status.setText)
        self._worker.progress.connect(self._progress.setValue)
        self._worker.done.connect(self._on_done)
        self._worker.error.connect(self._on_error)
        self._worker.start()

    def _on_done(self, path: str):
        self._gen_btn.setEnabled(True)
        self._status.setText(f"Done! {Path(path).name}")
        self._preview_panel.show_image(path)
        job = self._active_job or {}
        add_history_entry({
            "path": str(path),
            "tab": "i2i",
            "prompt": job.get("prompt", ""),
            "workflow": job.get("workflow_path", ""),
            "size": job.get("size", []),
            "steps": job.get("steps", 0),
            "seed": job.get("seed", -1),
            "strength": job.get("strength", 0),
            "source": job.get("source", ""),
            "timestamp": datetime.now().isoformat(timespec="seconds"),
        })

    def _on_error(self, msg: str):
        self._gen_btn.setEnabled(True)
        self._progress.setValue(0)
        self._status.setText("Error — see preview panel")
        self._preview_panel.set_message(f"Error:\n{msg[:400]}")

    def apply_history(self, entry: dict):
        self._prompt.setPlainText(entry.get("prompt", ""))
        steps = entry.get("steps")
        if isinstance(steps, int) and steps > 0:
            self._steps.setValue(steps)
        seed = entry.get("seed")
        if isinstance(seed, int):
            self._seed.setValue(seed)
        strength = entry.get("strength")
        if isinstance(strength, (int, float)) and strength > 0:
            self._strength.setValue(int(strength * 100))
        size = entry.get("size") or []
        if len(size) == 2:
            for i in range(self._size_combo.count()):
                if self._size_combo.itemData(i) == tuple(size):
                    self._size_combo.setCurrentIndex(i)
                    break
        wf = entry.get("workflow", "")
        for i in range(self._wf_combo.count()):
            if self._wf_combo.itemData(i) == wf:
                self._wf_combo.setCurrentIndex(i)
                break
        src = entry.get("source", "")
        if src and Path(src).exists():
            self._src_slot.set_image(src, copy=False)
        self._save_state()


# ------------------------------------------------------------------ #
# Tab 4 — Library
# ------------------------------------------------------------------ #

class LibraryTab(QWidget):
    recall_requested = pyqtSignal(dict)
    variations_requested = pyqtSignal(str)

    def __init__(self, settings: dict, parent=None):
        super().__init__(parent)
        self._settings = settings
        self._cards: list[ThumbnailCard] = []
        self._selected_card: ThumbnailCard | None = None
        self._all_paths: list[str] = []
        self._selected_entry: dict | None = None
        self._compare_a: str | None = None
        self._build_ui()

    def _favorites(self) -> list[str]:
        favs = self._settings.get("lib_favorites", [])
        return favs if isinstance(favs, list) else []

    def _is_fav(self, path: str) -> bool:
        return str(path) in self._favorites()

    def _build_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(8)

        # Toolbar
        toolbar = QHBoxLayout()
        refresh_btn = QPushButton("↻  Refresh")
        refresh_btn.setObjectName("secondary")
        refresh_btn.clicked.connect(self.refresh)
        filter_lbl = QLabel("Filter:")
        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText("Filename...")
        self._filter_edit.setFixedWidth(200)
        self._filter_edit.textChanged.connect(self._apply_filter)
        clear_filter_btn = QPushButton("✕")
        clear_filter_btn.setObjectName("secondary")
        clear_filter_btn.setFixedSize(28, 28)
        clear_filter_btn.setToolTip("Clear filter")
        clear_filter_btn.clicked.connect(lambda: self._filter_edit.clear())
        self._fav_only_chk = QCheckBox("★ Favorites only")
        self._fav_only_chk.setStyleSheet(f"color:{FG}; font-size:9pt;")
        self._fav_only_chk.stateChanged.connect(self._apply_filter)
        self._count_lbl = QLabel("0 images")
        self._count_lbl.setStyleSheet(f"color:{FG_DIM}; font-size:9pt;")
        toolbar.addWidget(refresh_btn)
        toolbar.addSpacing(12)
        toolbar.addWidget(filter_lbl)
        toolbar.addWidget(self._filter_edit)
        toolbar.addWidget(clear_filter_btn)
        toolbar.addSpacing(12)
        toolbar.addWidget(self._fav_only_chk)
        toolbar.addStretch()
        toolbar.addWidget(self._count_lbl)
        root.addLayout(toolbar)

        # Split: grid left | preview right
        split = QHBoxLayout()
        split.setSpacing(12)

        # Left — scrollable thumbnail grid
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._grid_widget = QWidget()
        self._grid_widget.setStyleSheet(f"background-color: {BG};")
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setSpacing(8)
        self._grid_layout.setContentsMargins(4, 4, 4, 4)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        self._scroll.setWidget(self._grid_widget)
        split.addWidget(self._scroll, stretch=3)

        # Right — preview + info + actions
        right_widget = QWidget()
        right_widget.setFixedWidth(370)
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self._lib_preview = PreviewPanel()
        self._lib_preview.set_message("Select an image")
        right_layout.addWidget(self._lib_preview, stretch=1)

        info_group = QGroupBox("Info")
        info_layout = QVBoxLayout(info_group)
        info_layout.setSpacing(3)
        self._meta_name = QLabel("—")
        self._meta_name.setWordWrap(True)
        self._meta_name.setStyleSheet(f"font-size:9pt; color:{FG};")
        self._meta_date = QLabel("—")
        self._meta_date.setStyleSheet(f"font-size:8pt; color:{FG_DIM};")
        self._meta_size = QLabel("—")
        self._meta_size.setStyleSheet(f"font-size:8pt; color:{FG_DIM};")
        self._meta_prompt = QLabel("—")
        self._meta_prompt.setWordWrap(True)
        self._meta_prompt.setMaximumHeight(76)
        self._meta_prompt.setStyleSheet(f"font-size:8pt; color:{FG_DIM}; font-style:italic;")
        info_layout.addWidget(self._meta_name)
        info_layout.addWidget(self._meta_date)
        info_layout.addWidget(self._meta_size)
        info_layout.addWidget(self._meta_prompt)
        right_layout.addWidget(info_group)

        fav_row = QHBoxLayout()
        self._lib_fav_btn = QPushButton("☆  Favorite")
        self._lib_fav_btn.setObjectName("secondary")
        self._lib_fav_btn.setEnabled(False)
        self._lib_fav_btn.clicked.connect(self._toggle_favorite)
        self._lib_compare_btn = QPushButton("⇆  Set A")
        self._lib_compare_btn.setObjectName("secondary")
        self._lib_compare_btn.setEnabled(False)
        self._lib_compare_btn.setToolTip(
            "Select an image and click to set it as A;\n"
            "then select another image and click again to compare."
        )
        self._lib_compare_btn.clicked.connect(self._compare_clicked)
        fav_row.addWidget(self._lib_fav_btn)
        fav_row.addWidget(self._lib_compare_btn)
        right_layout.addLayout(fav_row)

        recall_row = QHBoxLayout()
        self._lib_recall_btn = QPushButton("↩  Recall Prompt")
        self._lib_recall_btn.setObjectName("secondary")
        self._lib_recall_btn.setEnabled(False)
        self._lib_recall_btn.setToolTip("Restore this image's prompt and settings to the tab that generated it")
        self._lib_recall_btn.clicked.connect(self._recall_prompt)
        self._lib_vary_btn = QPushButton("🔄  Variations")
        self._lib_vary_btn.setObjectName("secondary")
        self._lib_vary_btn.setEnabled(False)
        self._lib_vary_btn.setToolTip("Send this image to the Variations tab")
        self._lib_vary_btn.clicked.connect(self._send_to_variations)
        recall_row.addWidget(self._lib_recall_btn)
        recall_row.addWidget(self._lib_vary_btn)
        right_layout.addLayout(recall_row)

        action_row = QHBoxLayout()
        self._lib_open_btn = QPushButton("📁  Open Folder")
        self._lib_open_btn.setObjectName("secondary")
        self._lib_open_btn.setEnabled(False)
        self._lib_open_btn.clicked.connect(self._open_folder)
        self._lib_delete_btn = QPushButton("🗑  Delete")
        self._lib_delete_btn.setObjectName("danger")
        self._lib_delete_btn.setEnabled(False)
        self._lib_delete_btn.clicked.connect(self._delete_selected)
        action_row.addWidget(self._lib_open_btn)
        action_row.addWidget(self._lib_delete_btn)
        right_layout.addLayout(action_row)

        split.addWidget(right_widget)
        root.addLayout(split, stretch=1)

    def refresh(self):
        dirs = []
        for key in ("t2i_output_dir", "edit_output_dir", "i2i_output_dir"):
            d = self._settings.get(key, "")
            if d and Path(d).exists():
                dirs.append(Path(d))

        imgs: list[Path] = []
        for d in dirs:
            for ext in ("*.png", "*.jpg", "*.jpeg", "*.webp"):
                imgs.extend(d.glob(ext))

        # Deduplicate and sort newest first
        seen: set[str] = set()
        unique: list[Path] = []
        for p in imgs:
            if str(p) not in seen:
                seen.add(str(p))
                unique.append(p)
        unique.sort(key=lambda p: p.stat().st_mtime, reverse=True)

        self._all_paths = [str(p) for p in unique[:200]]
        self._apply_filter()

    def _apply_filter(self):
        query = self._filter_edit.text().lower()
        fav_only = self._fav_only_chk.isChecked()
        filtered = [p for p in self._all_paths
                    if (not query or query in Path(p).name.lower())
                    and (not fav_only or self._is_fav(p))]
        self._rebuild_grid(filtered)

    def _rebuild_grid(self, paths: list[str]):
        for card in self._cards:
            self._grid_layout.removeWidget(card)
            card.setParent(None)
            card.deleteLater()
        self._cards.clear()
        self._selected_card = None

        for i, path in enumerate(paths):
            card = ThumbnailCard(path, favorite=self._is_fav(path))
            card.selected_signal.connect(self._on_card_clicked)
            self._cards.append(card)
            row, col = divmod(i, _LIB_COLS)
            self._grid_layout.addWidget(card, row, col)

        self._count_lbl.setText(f"{len(paths)} image{'s' if len(paths) != 1 else ''}")

    def _on_card_clicked(self, path: str):
        if self._selected_card:
            self._selected_card.set_selected(False)

        for card in self._cards:
            if card.path == path:
                card.set_selected(True)
                self._selected_card = card
                break

        self._lib_preview.show_image(path)

        p = Path(path)
        self._meta_name.setText(p.name)
        try:
            stat = p.stat()
            mtime = datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d  %H:%M:%S")
            size_kb = stat.st_size / 1024
            self._meta_date.setText(f"Modified: {mtime}")
            self._meta_size.setText(f"Size: {size_kb:.1f} KB   ({p.suffix.upper().lstrip('.')})")
        except Exception:
            pass

        # History lookup — prompt display + recall availability
        self._selected_entry = find_history_entry(path)
        if self._selected_entry and self._selected_entry.get("prompt"):
            prompt = self._selected_entry["prompt"].replace("\n", " ")
            if len(prompt) > 220:
                prompt = prompt[:217] + "..."
            self._meta_prompt.setText(f"“{prompt}”")
        elif self._selected_entry:
            self._meta_prompt.setText("(generated — no prompt recorded)")
        else:
            self._meta_prompt.setText("(no generation history for this image)")
        self._lib_recall_btn.setEnabled(self._selected_entry is not None)

        self._lib_fav_btn.setEnabled(True)
        self._lib_fav_btn.setText("★  Unfavorite" if self._is_fav(path) else "☆  Favorite")
        self._lib_compare_btn.setEnabled(True)
        self._update_compare_button()
        self._lib_vary_btn.setEnabled(True)
        self._lib_open_btn.setEnabled(True)
        self._lib_delete_btn.setEnabled(True)

    # ---- Favorites -------------------------------------------------- #

    def _toggle_favorite(self):
        if not self._selected_card:
            return
        path = str(self._selected_card.path)
        favs = self._favorites()
        if path in favs:
            favs.remove(path)
        else:
            favs.append(path)
        self._settings["lib_favorites"] = favs
        save_settings(self._settings)
        self._selected_card.set_favorite(path in favs)
        self._lib_fav_btn.setText("★  Unfavorite" if path in favs else "☆  Favorite")
        if self._fav_only_chk.isChecked():
            self._apply_filter()

    # ---- A/B compare ------------------------------------------------- #

    def _update_compare_button(self):
        if self._compare_a:
            self._lib_compare_btn.setText("⇆  Compare with A")
        else:
            self._lib_compare_btn.setText("⇆  Set A")

    def _compare_clicked(self):
        if not self._selected_card:
            return
        path = self._selected_card.path
        if not self._compare_a:
            self._compare_a = path
            self._update_compare_button()
            self._count_lbl.setText(f"A = {Path(path).name}")
            return
        if path == self._compare_a:
            # Clicking again on A cancels the pending compare
            self._compare_a = None
            self._update_compare_button()
            return
        dlg = CompareDialog(self._compare_a, path, self)
        self._compare_a = None
        self._update_compare_button()
        dlg.exec()

    # ---- Prompt recall / variations ---------------------------------- #

    def _recall_prompt(self):
        if self._selected_entry:
            self.recall_requested.emit(self._selected_entry)

    def _send_to_variations(self):
        if self._selected_card:
            self.variations_requested.emit(self._selected_card.path)

    def _open_folder(self):
        if self._selected_card:
            subprocess.Popen(f'explorer "{Path(self._selected_card.path).parent}"')

    def _delete_selected(self):
        if not self._selected_card:
            return
        path = self._selected_card.path
        reply = QMessageBox.question(
            self, "Delete Image",
            f"Permanently delete:\n{Path(path).name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            try:
                Path(path).unlink()
                self.refresh()
            except Exception as e:
                QMessageBox.warning(self, "Error", f"Could not delete file:\n{e}")

    def showEvent(self, event):
        super().showEvent(event)
        if not self._all_paths:
            self.refresh()


# ------------------------------------------------------------------ #
# Main window
# ------------------------------------------------------------------ #

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._settings = load_settings()
        self._api_keys = load_api_keys()

        self.setWindowTitle(f"AI Image Studio  v{VERSION}")
        self.setMinimumSize(800, 600)
        self.resize(1400, 900)
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

        self._tabs = QTabWidget()
        self._t2i_tab     = TextToImageTab(self._settings, self._api_keys)
        self._compose_tab = SceneComposerTab(self._settings, self._api_keys)
        self._i2i_tab     = ImageVariationsTab(self._settings, self._api_keys)
        self._library_tab = LibraryTab(self._settings)
        self._tabs.addTab(self._t2i_tab,     "✨  Text to Image")
        self._tabs.addTab(self._compose_tab, "🎨  Scene Composer")
        self._tabs.addTab(self._i2i_tab,     "🔄  Variations")
        self._tabs.addTab(self._library_tab, "🖼  Library")
        root.addWidget(self._tabs)

        self._library_tab.recall_requested.connect(self._on_recall)
        self._library_tab.variations_requested.connect(self._on_variations)

    def _on_recall(self, entry: dict):
        tab_key = entry.get("tab", "t2i")
        target = {
            "t2i":  self._t2i_tab,
            "edit": self._compose_tab,
            "i2i":  self._i2i_tab,
        }.get(tab_key, self._t2i_tab)
        target.apply_history(entry)
        self._tabs.setCurrentWidget(target)

    def _on_variations(self, path: str):
        self._i2i_tab.set_source_image(path)
        self._tabs.setCurrentWidget(self._i2i_tab)

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
