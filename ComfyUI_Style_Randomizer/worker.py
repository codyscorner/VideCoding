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


def append_daily_log(base_dir: Path, text: str):
    """Appends a line to logs/<today>.txt next to the EXE (base_dir must already
    be the frozen-EXE-aware directory — see main.py's BASE_DIR)."""
    logs_dir = base_dir / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_path = logs_dir / f"{datetime.now().strftime('%Y-%m-%d')}.txt"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(text.rstrip("\n") + "\n")


PROMPT_MODES = ("random", "sequential", "evens_odds")


class ComfyRunError(Exception):
    """ComfyUI itself said it cannot make this image - a model/node it cannot
    find, a workflow it rejected, a failure while executing. The next image
    would hit the same wall, so the run stops instead of burning through the
    rest of the list (and the pod's per-second billing) producing nothing."""


def _short(text, limit: int = 300) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= limit else text[:limit] + "…"


def describe_prompt_rejection(resp) -> str:
    """Turn a failed POST /prompt into the reason ComfyUI gave.

    A 400 carries {"error": {"message", "details"}, "node_errors": {id: {
    "class_type", "errors": [{"message", "details"}]}}} - e.g. "Value not in
    list: unet_name" when a model file is missing on the pod."""
    try:
        data = resp.json()
    except ValueError:
        return f"HTTP {resp.status_code}: {_short(resp.text) or resp.reason}"
    if not isinstance(data, dict):
        return f"HTTP {resp.status_code}: {_short(data)}"
    err = data.get("error")
    if isinstance(err, dict):
        head = err.get("message") or err.get("type") or "rejected"
        if err.get("details"):
            head += f" ({_short(err['details'])})"
    else:
        head = str(err) if err else f"HTTP {resp.status_code}"
    parts = []
    for node_id, info in (data.get("node_errors") or {}).items():
        for e in (info.get("errors") or []):
            msg = e.get("message", "")
            if e.get("details"):
                msg += f": {e['details']}"
            parts.append(f"node {node_id} ({info.get('class_type', '?')}): {_short(msg)}")
    return head + "".join(f"\n    {x}" for x in parts[:5])


def describe_history_error(entry: dict) -> str | None:
    """The failure recorded in a /history entry, or None if it did not fail."""
    status = entry.get("status") or {}
    if status.get("status_str") != "error":
        return None
    for kind, info in status.get("messages") or []:
        if kind == "execution_error" and isinstance(info, dict):
            return (f"{info.get('exception_type', 'Error')} in node {info.get('node_id', '?')} "
                    f"({info.get('node_type', '?')}): {_short(info.get('exception_message', ''))}")
    return "ComfyUI reported an execution error"


# Anything that is not a ComfyUI verdict (network blip, timeout) is retried
# on the next image, but not forever.
MAX_CONSECUTIVE_FAILURES = 3


class BatchStyleWorker(QThread):
    progress = pyqtSignal(int, int)   # current, total
    log      = pyqtSignal(str)
    all_done = pyqtSignal()
    error    = pyqtSignal(str)

    def __init__(self, config: dict, prompts: list[PromptEntry], image_paths: list[Path],
                 fixed_prompt: str | None = None, prompt_mode: str = "random",
                 pinned: dict[str, str] | None = None, base_dir: Path | None = None):
        super().__init__()
        self._config        = config
        self._prompts       = prompts
        self._image_paths   = image_paths
        self._fixed_prompt  = fixed_prompt
        self._prompt_mode   = prompt_mode
        self._pinned        = pinned or {}
        self._base_dir      = base_dir
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

    @property
    def cancelled(self) -> bool:
        return self._cancelled

    def _log(self, msg: str):
        self.log.emit(msg)

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        total = int(seconds)
        h, rem = divmod(total, 3600)
        m, s = divmod(rem, 60)
        if h:
            return f"{h}h {m}m {s}s"
        if m:
            return f"{m}m {s}s"
        return f"{s}s"

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
            start_time = time.time()
            self._log(f"Starting — {total} images, {len(self._prompts)} prompts")
            if self._base_dir:
                append_daily_log(
                    self._base_dir,
                    f"\n=== Run started {datetime.now().strftime('%H:%M:%S')} — "
                    f"{total} images, {len(self._prompts)} prompts ===",
                )

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
            failures = 0  # consecutive non-ComfyUI failures

            for i, img_path in enumerate(self._image_paths):
                if self._cancelled:
                    elapsed = self._format_elapsed(time.time() - start_time)
                    self._log(f"Cancelled. ({elapsed})")
                    if self._base_dir:
                        append_daily_log(self._base_dir, f"=== Cancelled ({elapsed}) ===")
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
                    preview    = prompt.replace("\n", " ")[:255]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  📌 {preview}…")
                elif self._fixed_prompt is not None:
                    prompt  = self._fixed_prompt
                    preview = prompt.replace("\n", " ")[:255]
                    prompt_idx = texts.index(prompt) + 1 if prompt in texts else "custom"
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  {preview}…")
                elif _seq is not None:
                    idx        = seq_pos % len(_seq)
                    prompt     = _seq[idx]
                    prompt_idx = texts.index(prompt) + 1 if prompt in texts else "custom"
                    preview    = prompt.replace("\n", " ")[:255]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  style #{prompt_idx}: {preview}…")
                    seq_pos += 1
                else:
                    idx         = random.choices(range(len(texts)), weights=weights, k=1)[0]
                    prompt      = texts[idx]
                    prompt_idx  = idx + 1
                    weight_used = weights[idx]
                    preview     = prompt.replace("\n", " ")[:255]
                    self._log(f"[{i+1}/{total}] {img_path.name}  →  style #{prompt_idx}: {preview}…")

                if self._base_dir:
                    append_daily_log(
                        self._base_dir,
                        f"{datetime.now().strftime('%H:%M:%S')}  {img_path.name}  ->  "
                        f"{prompt.replace(chr(10), ' ')}",
                    )

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
                        elapsed = self._format_elapsed(time.time() - start_time)
                        self._log(f"Cancelled. ({elapsed})")
                        if self._base_dir:
                            append_daily_log(self._base_dir, f"=== Cancelled ({elapsed}) ===")
                        self.all_done.emit()
                        return

                    saved = self._get_output(prompt_id, img_path)
                    self._log(f"  ✓ {saved.name}")
                    log_prompt_used(self._output_dir, saved.name, prompt_idx, prompt, weight_used, note)
                    failures = 0
                except ComfyRunError as exc:
                    self._log(f"  ✗ {exc}")
                    self._abort(f"{img_path.name}: {exc}", start_time)
                    return
                except Exception as exc:
                    self._log(f"  ✗ {exc}")
                    failures += 1
                    if failures >= MAX_CONSECUTIVE_FAILURES:
                        self._abort(
                            f"{failures} images in a row failed - last: {img_path.name}: {exc}",
                            start_time)
                        return

                self.progress.emit(i + 1, total)

            elapsed = self._format_elapsed(time.time() - start_time)
            self._log(f"Done! {total} images processed in {elapsed}.")
            if self._base_dir:
                append_daily_log(self._base_dir, f"=== Done: {total} images processed in {elapsed} ===")
            self.all_done.emit()

        except Exception as exc:
            self.error.emit(str(exc))

    def _abort(self, msg: str, start_time: float):
        """Stop the whole run: log it, tell the window (which shows the error)."""
        elapsed = self._format_elapsed(time.time() - start_time)
        self._log(f"STOPPED - run aborted after {elapsed}")
        if self._base_dir:
            append_daily_log(self._base_dir, f"=== STOPPED ({elapsed}): {msg} ===")
        self.error.emit(msg)

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
        if resp.status_code == 400:
            raise ComfyRunError("ComfyUI rejected the workflow - " + describe_prompt_rejection(resp))
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
                    why = describe_history_error(h[prompt_id])
                    if why:
                        raise ComfyRunError(f"ComfyUI failed while generating - {why}")
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

        raise ComfyRunError(
            "ComfyUI finished but produced no image - does the workflow end in a "
            "SaveImage node? (no output found in ComfyUI history)")

    def _output_exists(self, stem: str) -> bool:
        return any((self._output_dir / f"{stem}{ext}").exists() for ext in OUTPUT_EXTS)
