"""Background thread that runs ONE workflow against ONE source (image or
video) on the configured ComfyUI server and downloads the result."""

from __future__ import annotations

import logging
import random
import shutil
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

from comfy_client import ComfyClient
from media_tools import concat_videos, extract_last_frame, resolve_ffmpeg
from workflow_tools import (
    ValueField, analyze, apply_prompts, apply_seed, apply_value,
    load_workflow, set_output_prefix,
)

logger = logging.getLogger("video_creator")
logger.setLevel(logging.DEBUG)

RUN_LOG_NAME = "video_creator_run.log"
RUN_DELIM = "=== New run started ==="


@dataclass
class RunRequest:
    workflow_path: Path
    workflow_label: str
    source_path: Path
    source_kind: str                              # "image" | "video"
    prompts: dict[tuple[str, str], str] = field(default_factory=dict)
    seed: int | None = None                       # None = random
    length_field: ValueField | None = None
    length_value: float | None = None
    video_input_mode: str = "auto"                # auto | last_frame | upload_video
    extend_stitch: bool = False


class RunWorker(QThread):
    log = pyqtSignal(str)
    plan = pyqtSignal(int, int)          # total sampler steps, post-sampler phases
    step = pyqtSignal(int, int)          # value, max (one sampler pass)
    phase = pyqtSignal(str)              # a post-sampler phase started
    finished_ok = pyqtSignal(list)       # list[str] of local output paths
    failed = pyqtSignal(str)

    def __init__(self, config: dict, req: RunRequest):
        super().__init__()
        self._cfg = config
        self._req = req
        self._cancelled = False
        self._prompt_id = ""
        self._runpod = config.get("mode", "local") == "runpod"
        url = config.get("runpod_url", "") if self._runpod else config.get("comfyui_url", "")
        self._client = ComfyClient((url or "").strip(), log=self._log)
        self._base_dir = Path(config.get("_base_dir", str(Path(__file__).parent)))
        self._temp_dir = self._base_dir / "temp"
        self._run_id = time.strftime("%Y%m%d_%H%M%S")
        self._ffmpeg = resolve_ffmpeg(config.get("ffmpeg_path", ""), self._base_dir)

        log_path = self._base_dir / RUN_LOG_NAME
        _trim_log(log_path, keep=50)
        fh = logging.FileHandler(str(log_path), mode="a", encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S"))
        logger.handlers.clear()
        logger.addHandler(fh)

    # ------------------------------------------------------------------ #

    def cancel(self):
        self._cancelled = True
        # Stop it on the server too — otherwise the prompt keeps running
        # (and keeps billing on RunPod) after the UI says cancelled.
        threading.Thread(target=self._client.interrupt, args=(self._prompt_id,), daemon=True).start()

    def _log(self, msg: str):
        self.log.emit(msg)
        logger.info(msg)

    def _check_cancel(self):
        if self._cancelled:
            raise _Cancelled()

    # ------------------------------------------------------------------ #

    def run(self):
        req = self._req
        try:
            logger.info(RUN_DELIM)
            t0 = time.time()
            if not self._client.url:
                raise RuntimeError("No server URL configured for the selected mode — open Settings.")
            self._temp_dir.mkdir(exist_ok=True)
            self._log(f"Server: {self._client.url} ({'RunPod' if self._runpod else 'Local'})")
            self._log(f"Workflow: {req.workflow_label}")
            self._log(f"Source {req.source_kind}: {req.source_path.name}")

            workflow = load_workflow(req.workflow_path)
            info = analyze(workflow)

            # Text / seed / length edits
            if req.prompts:
                apply_prompts(workflow, req.prompts)
            seed = req.seed if req.seed is not None else random.randint(0, 2**32 - 1)
            n_seed = apply_seed(workflow, seed)
            if n_seed:
                self._log(f"Seed: {seed} ({n_seed} field{'s' if n_seed != 1 else ''})")
            if req.length_field is not None and req.length_value is not None:
                apply_value(workflow, req.length_field, req.length_value)
                self._log(f"{req.length_field.label}: {req.length_value:g}")

            # Feed the source into the graph
            if req.source_kind == "image":
                if not info.accepts_image:
                    raise RuntimeError(
                        "This workflow has no image input (LoadImage or Load Image List From Dir). "
                        "Pick an image-to-video workflow for this tab."
                    )
                self._feed_image(workflow, info, req.source_path)
            else:
                self._feed_video(workflow, info, req.source_path)
            self._check_cancel()

            # Route outputs into a run-specific folder on the server so the
            # history lookup can't confuse them with older files.
            stem = _safe(req.source_path.stem)
            set_output_prefix(workflow, f"VideoCreator/{self._run_id}/{stem}")

            self.plan.emit(sum(info.sampler_steps), info.post_phases)
            self._log("Queuing workflow...")
            self._prompt_id = self._client.queue(workflow)
            self._log(f"Queued ({self._prompt_id[:8]}...) — waiting for ComfyUI")

            self._client.wait(
                self._prompt_id, workflow,
                on_step=lambda v, m: self.step.emit(v, m),
                on_phase=self._on_phase,
                cancelled=lambda: self._cancelled,
            )
            self._check_cancel()

            if self._runpod:
                time.sleep(3)  # let the proxy catch up with the written file
            outputs = self._download_outputs(info, req)
            self._check_cancel()

            results = [str(p) for p in outputs]
            if req.source_kind == "video" and req.extend_stitch and outputs:
                stitched = self._stitch_extension(req.source_path, outputs[0], req)
                results.append(str(stitched))

            self._log(f"Done in {_fmt(time.time() - t0)}")
            self.finished_ok.emit(results)
        except _Cancelled:
            self._log("Cancelled.")
            self.failed.emit("Cancelled")
        except Exception as e:  # noqa: BLE001
            logger.exception("Run failed")
            self.failed.emit(str(e))

    # ------------------------------------------------------------------ #
    # Input handling
    # ------------------------------------------------------------------ #

    def _feed_image(self, workflow: dict, info, image_path: Path):
        if info.image_nodes:
            nid, title = info.image_nodes[0]
            self._log(f"Uploading image {image_path.name}...")
            name = self._client.upload(image_path, subfolder="VideoCreator")
            workflow[nid]["inputs"]["image"] = name
            self._log(f"Image → node {nid} ({title or 'Load Image'}) as {name}")
            if len(info.image_nodes) > 1:
                others = ", ".join(i for i, _ in info.image_nodes[1:])
                self._log(f"Note: other LoadImage nodes ({others}) keep the image saved in the workflow")
            return

        # Folder-loader workflow (batch style): stage the single image in a
        # fresh run folder and point the loader's directory at it.
        nid, title = info.list_loaders[0]
        if self._runpod:
            sub = f"VideoCreator/{self._run_id}"
            self._log(f"Uploading image {image_path.name} to {sub}/ ...")
            self._client.upload(image_path, subfolder=sub)
            input_root = (self._cfg.get("runpod_input_dir", "") or "/workspace/runpod-slim/ComfyUI/input").rstrip("/")
            directory = f"{input_root}/{sub}"
        else:
            root = (self._cfg.get("staging_dir_local", "") or "").strip()
            stage = Path(root) if root else self._temp_dir / "staging"
            stage = stage / "VideoCreator" / self._run_id
            stage.mkdir(parents=True, exist_ok=True)
            shutil.copy2(image_path, stage / image_path.name)
            directory = str(stage)
            self._log(f"Staged image in {directory}")
        workflow[nid]["inputs"]["directory"] = directory
        for key in ("image_load_cap", "start_index"):
            if key in workflow[nid]["inputs"]:
                workflow[nid]["inputs"][key] = 0
        self._log(f"Folder → node {nid} ({title or 'Load Image List From Dir'})")

    def _feed_video(self, workflow: dict, info, video_path: Path):
        mode = self._req.video_input_mode
        if mode == "auto":
            if info.video_nodes:
                mode = "upload_video"
            elif info.accepts_image:
                mode = "last_frame"
            else:
                raise RuntimeError(
                    "This workflow has neither a video input (LoadVideo / VHS_LoadVideo) nor an "
                    "image input (LoadImage). Pick a workflow that can take the selected video or its last frame."
                )

        if mode == "upload_video":
            if not info.video_nodes:
                raise RuntimeError(
                    "Input mode is 'Upload video' but this workflow has no LoadVideo / VHS_LoadVideo node. "
                    "Switch the input mode to 'Last frame → image' or pick a video-input workflow."
                )
            nid, title, key = info.video_nodes[0]
            self._log(f"Uploading video {video_path.name} ({video_path.stat().st_size // 1024} KB)...")
            name = self._client.upload(video_path, subfolder="VideoCreator")
            workflow[nid]["inputs"][key] = name
            self._log(f"Video → node {nid} ({title or 'Load Video'}) as {name}")
            return

        # last_frame
        if not info.accepts_image:
            raise RuntimeError(
                "Input mode is 'Last frame → image' but this workflow has no LoadImage / folder loader node."
            )
        frame = self._temp_dir / f"{_safe(video_path.stem)}_lastframe_{self._run_id}.png"
        self._log(f"Extracting last frame of {video_path.name}...")
        extract_last_frame(self._ffmpeg, video_path, frame)
        self._feed_image(workflow, info, frame)

    def _on_phase(self, label: str):
        self._log(label)
        self.phase.emit(label)

    # ------------------------------------------------------------------ #
    # Outputs
    # ------------------------------------------------------------------ #

    def _download_outputs(self, info, req: RunRequest) -> list[Path]:
        history = self._client.history(self._prompt_id)
        files = self._client.collect_outputs(history, info.output_nodes)
        if not files:
            raise RuntimeError(
                "ComfyUI finished but reported no output file. Make sure the workflow ends in a "
                "SaveVideo or VHS_VideoCombine node (Preview nodes don't write files)."
            )
        out_dir = Path((self._cfg.get("output_dir", "") or "").strip() or (self._base_dir / "output"))
        out_dir.mkdir(parents=True, exist_ok=True)
        stem = _safe(req.source_path.stem)
        label = _safe(req.workflow_label)
        results: list[Path] = []
        for idx, f in enumerate(files, 1):
            ext = Path(f["filename"]).suffix or ".mp4"
            suffix = f"_{idx}" if len(files) > 1 else ""
            dest = out_dir / f"{stem}_{label}_{self._run_id}{suffix}{ext}"
            self._log(f"Downloading {f['filename']} → {dest.name}")
            self._client.download(f, dest)
            results.append(dest)
            self._log(f"Saved {dest.name} ({dest.stat().st_size // 1024} KB)")
        return results

    def _stitch_extension(self, source: Path, clip: Path, req: RunRequest) -> Path:
        out_dir = clip.parent
        dest = out_dir / f"{_safe(source.stem)}_extended_{self._run_id}.mp4"
        self._log(f"Appending new clip to {source.name} → {dest.name}")
        concat_videos(self._ffmpeg, [source, clip], dest)
        self._log(f"Extended video saved ({dest.stat().st_size // 1024} KB)")
        return dest


class _Cancelled(Exception):
    pass


def _safe(name: str) -> str:
    keep = "".join(c if (c.isalnum() or c in "-_.") else "_" for c in name.strip())
    return keep.strip("_") or "video"


def _fmt(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m:02d}m {s:02d}s"


def _trim_log(log_path: Path, keep: int):
    if not log_path.exists():
        return
    try:
        text = log_path.read_text(encoding="utf-8")
    except OSError:
        return
    runs = [p for p in text.split(RUN_DELIM)[1:] if p.strip()]
    if len(runs) >= keep:
        trimmed = RUN_DELIM.join([""] + runs[-(keep - 1):])
        try:
            log_path.write_text(trimmed.lstrip("\n"), encoding="utf-8")
        except OSError:
            pass
