import csv
import json
import random
import re
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import NamedTuple

import requests
from PyQt6.QtCore import QThread, pyqtSignal

PROMPT_SEPARATOR = "---- PROMPT START -----"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".bmp"}
OUTPUT_EXTS = IMAGE_EXTS | {".mp4", ".mov", ".avi", ".mkv", ".gif"}
PROMPT_LOG_NAME = "prompt_log.csv"

# Separator may carry an optional weight suffix, e.g. "---- PROMPT START x3 -----"
_SEP_RE = re.compile(
    r"^-+\s*PROMPT START(?:\s+x\s*(\d+(?:\.\d+)?))?\s*-+\s*$",
    re.MULTILINE,
)


class PromptEntry(NamedTuple):
    text: str
    weight: float = 1.0


def parse_prompts(text: str) -> list[PromptEntry]:
    matches = list(_SEP_RE.finditer(text))
    entries = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if not body:
            continue
        weight = float(m.group(1)) if m.group(1) else 1.0
        entries.append(PromptEntry(body, weight))
    return entries


def load_prompts(path: Path) -> list[PromptEntry]:
    return parse_prompts(path.read_text(encoding="utf-8"))


def log_prompt_used(output_dir: Path, image_name: str, prompt_index: int | str,
                     prompt_preview: str, weight: float | str = "", note: str = ""):
    log_path = output_dir / PROMPT_LOG_NAME
    is_new = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "image", "prompt_index", "weight", "note", "prompt_preview"])
        writer.writerow([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            image_name,
            prompt_index,
            weight,
            note,
            prompt_preview.replace("\n", " ")[:120],
        ])


PROMPT_MODES = ("random", "sequential", "evens_odds")


class BatchStyleWorker(QThread):
    progress = pyqtSignal(int, int)   # current, total
    log      = pyqtSignal(str)
    all_done = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, config: dict, prompts: list[PromptEntry], image_paths: list[Path],
                 fixed_prompt: str | None = None, prompt_mode: str = "random",
                 pinned: dict[str, str] | None = None):
        super().__init__()
        self._config        = config
        self._prompts       = prompts
        self._image_paths   = image_paths
        self._fixed_prompt  = fixed_prompt
        self._prompt_mode   = prompt_mode
        self._pinned        = pinned or {}
        self._cancelled     = False
        self._client_id   = str(uuid.uuid4())
        runpod = config.get("mode", "local") == "runpod"
        self._url = (
            config.get("runpod_url", "").rstrip("/")
            if runpod
            else config.get("comfyui_url", "http://127.0.0.1:8000").rstrip("/")
        )
        self._output_dir   = Path(config.get("output_dir", ""))
        self._skip_existing = config.get("skip_existing", True)

    def cancel(self):
        self._cancelled = True

    def _log(self, msg: str):
        self.log.emit(msg)

    # ------------------------------------------------------------------ #
    # Main thread entry
    # ------------------------------------------------------------------ #

    def run(self):
        try:
            workflow_path = Path(self._config.get("workflow_path", ""))
            if not workflow_path.is_file():
                self.error.emit("Workflow file not found. Select a workflow JSON in the Paths section.")
                return
            if not self._prompts:
                self.error.emit("No prompts loaded. Select a prompts file.")
                return

            self._output_dir.mkdir(parents=True, exist_ok=True)
            base_workflow = json.loads(workflow_path.read_text(encoding="utf-8"))
            total = len(self._image_paths)
            self._log(f"Starting — {total} images, {len(self._prompts)} prompts")

            texts   = [e.text for e in self._prompts]
            weights = [e.weight for e in self._prompts]

            # Build ordered prompt sequence for non-random modes
            if self._prompt_mode == "sequential":
                _seq = list(texts)
            elif self._prompt_mode == "evens_odds":
                evens = texts[0::2]
                odds  = texts[1::2]
                _seq  = evens + odds
            else:
                _seq = None  # weighted random per image

            seq_pos = 0  # cursor for sequential / evens_odds

            for i, img_path in enumerate(self._image_paths):
                if self._cancelled:
                    self._log("Cancelled.")
                    self.all_done.emit()
                    return

                if self._skip_existing and self._output_exists(img_path.stem):
                    self._log(f"[{i+1}/{total}] Skipped (exists): {img_path.name}")
                    self.progress.emit(i + 1, total)
                    continue

                note = ""
                prompt_idx: int | str = ""
                weight_used: float | str = ""

                if img_path.stem in self._pinned:
                    prompt     = self._pinned[img_path.stem]
                    note       = "pinned"
                    prompt_idx = texts.index(prompt) + 1 if prompt in texts else "custom"
                    preview    = prompt.replace("\n", " ")[:60]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  📌 {preview}…")
                elif self._fixed_prompt is not None:
                    prompt  = self._fixed_prompt
                    preview = prompt.replace("\n", " ")[:60]
                    prompt_idx = texts.index(prompt) + 1 if prompt in texts else "custom"
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  {preview}…")
                elif _seq is not None:
                    idx        = seq_pos % len(_seq)
                    prompt     = _seq[idx]
                    prompt_idx = texts.index(prompt) + 1 if prompt in texts else "custom"
                    preview    = prompt.replace("\n", " ")[:60]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  style #{prompt_idx}: {preview}…")
                    seq_pos += 1
                else:
                    idx         = random.choices(range(len(texts)), weights=weights, k=1)[0]
                    prompt      = texts[idx]
                    prompt_idx  = idx + 1
                    weight_used = weights[idx]
                    preview     = prompt.replace("\n", " ")[:60]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  style #{prompt_idx}: {preview}…")

                try:
                    workflow = json.loads(json.dumps(base_workflow))
                    seed     = random.randint(1, 2**31)

                    uploaded = self._upload_image(img_path)
                    self._patch_image(workflow, uploaded)
                    self._patch_prompt(workflow, prompt)
                    self._patch_seed(workflow, seed)

                    prompt_id = self._queue_prompt(workflow)
                    self._poll_until_done(prompt_id)

                    if self._cancelled:
                        self._log("Cancelled.")
                        self.all_done.emit()
                        return

                    saved = self._get_output(prompt_id, img_path)
                    self._log(f"  ✓ {saved.name}")
                    log_prompt_used(self._output_dir, saved.name, prompt_idx, prompt, weight_used, note)
                except Exception as exc:
                    self._log(f"  ✗ {exc}")

                self.progress.emit(i + 1, total)

            self._log(f"Done! {total} images processed.")
            self.all_done.emit()

        except Exception as exc:
            self.error.emit(str(exc))

    # ------------------------------------------------------------------ #
    # Workflow patching
    # ------------------------------------------------------------------ #

    def _patch_image(self, workflow: dict, filename: str):
        for node in workflow.values():
            if node.get("class_type") == "LoadImage":
                node["inputs"]["image"] = filename
                return

    def _patch_prompt(self, workflow: dict, prompt: str):
        # Prefer PrimitiveStringMultiline (Qwen / some custom workflows)
        for node in workflow.values():
            if node.get("class_type") == "PrimitiveStringMultiline":
                node["inputs"]["value"] = prompt
                return
        # Fall back to first non-negative CLIPTextEncode
        for node in workflow.values():
            if node.get("class_type") == "CLIPTextEncode":
                if "neg" not in node.get("_meta", {}).get("title", "").lower():
                    node["inputs"]["text"] = prompt
                    return

    def _patch_seed(self, workflow: dict, seed: int):
        for node in workflow.values():
            inp = node.get("inputs", {})
            if node.get("class_type") == "KSampler":
                inp["seed"] = seed
            if "noise_seed" in inp:
                inp["noise_seed"] = seed
            if "seed" in inp and isinstance(inp["seed"], int):
                inp["seed"] = seed

    # ------------------------------------------------------------------ #
    # ComfyUI API helpers
    # ------------------------------------------------------------------ #

    def _upload_image(self, img_path: Path) -> str:
        with open(img_path, "rb") as f:
            resp = requests.post(
                f"{self._url}/upload/image",
                files={"image": (img_path.name, f, "image/png")},
                data={"type": "input", "overwrite": "true"},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["name"]

    def _queue_prompt(self, workflow: dict) -> str:
        resp = requests.post(
            f"{self._url}/prompt",
            json={"prompt": workflow, "client_id": self._client_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["prompt_id"]

    def _poll_until_done(self, prompt_id: str):
        elapsed = 0
        while not self._cancelled:
            time.sleep(3)
            elapsed += 3
            try:
                q = requests.get(f"{self._url}/queue", timeout=10).json()
                running = [item[1] for item in q.get("queue_running", [])]
                pending = [item[1] for item in q.get("queue_pending", [])]
                if prompt_id in running or prompt_id in pending:
                    if elapsed % 60 == 0:
                        self._log(f"  Generating... ({elapsed // 60}m)")
                    continue
                h = requests.get(f"{self._url}/history/{prompt_id}", timeout=10).json()
                if prompt_id in h:
                    return
            except requests.RequestException as exc:
                self._log(f"  Poll error: {exc}")
            if elapsed % 60 == 0:
                self._log(f"  Waiting... ({elapsed // 60}m)")

    def _get_output(self, prompt_id: str, src_img: Path) -> Path:
        h     = requests.get(f"{self._url}/history/{prompt_id}", timeout=15).json()
        entry = h.get(prompt_id, {})

        for node_out in entry.get("outputs", {}).values():
            for key in ("images", "gifs", "videos"):
                files = node_out.get(key, [])
                if files:
                    fi     = files[0]
                    params = {
                        "filename": fi["filename"],
                        "subfolder": fi.get("subfolder", ""),
                        "type": fi.get("type", "output"),
                    }
                    dl  = requests.get(f"{self._url}/view", params=params, timeout=120)
                    dl.raise_for_status()
                    ext  = Path(fi["filename"]).suffix or ".png"
                    dest = self._output_dir / f"{src_img.stem}{ext}"
                    dest.write_bytes(dl.content)
                    return dest

        raise RuntimeError("No output found in ComfyUI history")

    def _output_exists(self, stem: str) -> bool:
        return any((self._output_dir / f"{stem}{ext}").exists() for ext in OUTPUT_EXTS)
