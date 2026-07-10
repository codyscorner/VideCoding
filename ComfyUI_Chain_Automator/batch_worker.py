import json
import logging
import shutil
import subprocess
import threading
import time
import uuid
import zipfile
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("batch_chain")
logger.setLevel(logging.DEBUG)


class BatchChainWorker(QThread):
    log = pyqtSignal(str)
    segment_done = pyqtSignal(int)
    segment_time = pyqtSignal(int, str)
    segment_secs = pyqtSignal(int, float)     # segment, elapsed seconds (for ETA)
    step_progress = pyqtSignal(int, int, int)  # segment, step value, step max
    all_done = pyqtSignal(list)   # list[str] of final video paths
    error = pyqtSignal(str)

    def __init__(self, config: dict, images: list[str]):
        super().__init__()
        self._config = config
        self._images = images
        self._cancelled = False
        self._active_prompt_id = ""
        self._total_segs = len(config.get("workflows", []))
        self._client_id = str(uuid.uuid4())
        self._run_id = str(int(time.time() * 1000))
        # Suffix for stitched filenames so re-running the same source image
        # (e.g. after cleaning out a folder) never collides with or gets
        # skipped by an earlier batch's video of the same name.
        self._run_stamp = time.strftime("%Y%m%d_%H%M%S")
        self._runpod = config.get("mode", "local") == "runpod"
        self._url = (
            config.get("runpod_url", "").rstrip("/")
            if self._runpod
            else config.get("comfyui_url", "http://127.0.0.1:8000").rstrip("/")
        )
        self._batch_dir_local = Path(config.get("batch_dir_local", ""))
        self._batch_dir_runpod = config.get("batch_dir_runpod", "/workspace/runpod-slim/Batch_Processing")
        self._runpod_input_dir = config.get("runpod_input_dir", "/workspace/runpod-slim/ComfyUI/input")
        base_dir = Path(config.get("_base_dir", str(Path(__file__).parent)))
        self._temp_dir = base_dir / "temp"

        log_path = base_dir / "batch_run_log.txt"
        self._trim_log(log_path, keep=50)
        fh = logging.FileHandler(str(log_path), mode='a', encoding='utf-8')
        fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))
        logger.handlers.clear()
        logger.addHandler(fh)

    def cancel(self):
        self._cancelled = True
        # Stop the job on the ComfyUI server too — otherwise the prompt keeps
        # running (and on RunPod keeps billing) after the UI says cancelled.
        threading.Thread(target=self._interrupt_server, daemon=True).start()

    def _interrupt_server(self):
        try:
            requests.post(f"{self._url}/queue", json={"delete": [self._active_prompt_id]}, timeout=10)
        except Exception:
            pass
        try:
            requests.post(f"{self._url}/interrupt", timeout=10)
        except Exception:
            pass

    def _log(self, msg: str):
        self.log.emit(msg)
        logger.info(msg)

    # ------------------------------------------------------------------ #
    # Main thread entry
    # ------------------------------------------------------------------ #

    def run(self):
        try:
            logger.info("=== New batch run started ===")
            batch_start = time.time()
            self._temp_dir.mkdir(exist_ok=True)
            self._clean_temp_dir()
            self._batch_dir_local.mkdir(parents=True, exist_ok=True)
            n = len(self._images)
            self._log(f"Batch: {n} image{'s' if n != 1 else ''}")

            workflows = self._build_effective_workflows()
            self._total_segs = len(workflows)

            # Local mode: prepare fixed per-segment subdirs
            seg_subdirs = {}
            if not self._runpod:
                for wf in workflows:
                    s = wf["segment"]
                    d = self._batch_dir_local / f"seg_{s}"
                    d.mkdir(parents=True, exist_ok=True)
                    seg_subdirs[s] = d

            # segment_outputs[seg_idx] = list of N video Paths (one per image)
            segment_outputs: list[list[Path]] = []
            # transition_frames[i] = frames extracted between segments for image i
            transition_frames: list[list[Path]] = [[] for _ in range(n)]

            for wf in workflows:
                if self._cancelled:
                    self._log("Cancelled.")
                    return

                seg = wf["segment"]
                seg_start = time.time()
                self._log(f"[Segment {seg}/{self._total_segs}] Starting — {n} images in batch...")

                workflow_json = self._load_workflow(wf)
                self._bust_cache(workflow_json)

                # Use run-ID subfolder so each run gets an isolated, clean directory
                upload_subfolder = f"Batch_Processing/{self._run_id}/seg_{seg}"

                if seg == 1:
                    input_dir = Path(self._config["input_dir"])
                    if self._runpod:
                        for i, img_name in enumerate(self._images):
                            src = input_dir / img_name
                            fname = f"{i+1:03d}_{src.name}"
                            self._upload_batch_image(src, upload_subfolder, fname)
                        self._log(f"[Segment {seg}/{self._total_segs}] Uploaded {n} starting images")
                    else:
                        local_subdir = seg_subdirs[seg]
                        for f in local_subdir.iterdir():
                            if f.is_file(): f.unlink()
                        for i, img_name in enumerate(self._images):
                            src = input_dir / img_name
                            shutil.copy2(src, local_subdir / f"{i+1:03d}_{src.name}")
                        self._log(f"[Segment {seg}/{self._total_segs}] Staged {n} starting images")
                else:
                    prev_videos = segment_outputs[-1]
                    if self._runpod:
                        for i, prev_video in enumerate(prev_videos):
                            frame = self._temp_dir / f"{i+1:03d}_frame_seg{seg}.png"
                            self._extract_last_frame_to(prev_video, frame)
                            self._upload_batch_image(frame, upload_subfolder, frame.name)
                            transition_frames[i].append(frame)
                        self._log(f"[Segment {seg}/{self._total_segs}] Uploaded {n} frames")
                    else:
                        local_subdir = seg_subdirs[seg]
                        for f in local_subdir.iterdir():
                            if f.is_file(): f.unlink()
                        for i, prev_video in enumerate(prev_videos):
                            dst = local_subdir / f"{i+1:03d}_frame_seg{seg}.png"
                            self._extract_last_frame_to(prev_video, dst)
                            transition_frames[i].append(dst)
                        self._log(f"[Segment {seg}/{self._total_segs}] Extracted {n} last frames")

                # Set directory for LoadImageListFromDir
                if self._runpod:
                    dir_path = f"{self._runpod_input_dir}/Batch_Processing/{self._run_id}/seg_{seg}"
                else:
                    dir_path = str(seg_subdirs[seg])
                self._patch_batch_input(workflow_json, dir_path)
                self._patch_batch_output_prefix(workflow_json, seg)

                prompt_id = self._queue_prompt(workflow_json)
                self._active_prompt_id = prompt_id
                self._log(f"[Segment {seg}/{self._total_segs}] Queued ({prompt_id[:8]}...), polling...")

                self._wait_until_done(prompt_id, seg)
                if self._cancelled:
                    self._log("Cancelled.")
                    return

                if self._runpod:
                    time.sleep(5)
                videos = self._download_batch_outputs(seg, prompt_id, n)
                elapsed_secs = time.time() - seg_start
                elapsed = self._fmt(elapsed_secs)
                self._log(f"[Segment {seg}/{self._total_segs}] Done in {elapsed} — {n} videos")
                segment_outputs.append(videos)
                self.segment_done.emit(seg)
                self.segment_time.emit(seg, elapsed)
                self.segment_secs.emit(seg, elapsed_secs)

            if self._cancelled:
                return

            self._log("All segments complete. Stitching final videos...")
            final_paths = []
            for i, img_name in enumerate(self._images):
                chain_videos = [segment_outputs[s][i] for s in range(len(workflows))]
                final = self._stitch(chain_videos, img_name)
                final_paths.append(str(final))
                size_kb = final.stat().st_size // 1024
                self._log(f"  [{i+1}/{n}] {final.name}  ({size_kb} KB)")
                src_image = Path(self._config["input_dir"]) / img_name
                zip_path = self._zip_segments(chain_videos, final, src_image, transition_frames[i])
                self._log(f"  [{i+1}/{n}] Archive: {zip_path.name}")

            self._log(f"Total time: {self._fmt(time.time() - batch_start)}")
            self.all_done.emit(final_paths)

        except Exception as e:
            logger.exception("Batch chain error")
            self.error.emit(str(e))

    # ------------------------------------------------------------------ #
    # Workflow patching
    # ------------------------------------------------------------------ #

    def _upload_batch_image(self, image_path: Path, subfolder: str, filename: str):
        with open(image_path, 'rb') as f:
            resp = requests.post(
                f"{self._url}/upload/image",
                files={"image": (filename, f, "image/png")},
                data={"type": "input", "subfolder": subfolder, "overwrite": "true"},
                timeout=120,
            )
        resp.raise_for_status()

    def _patch_batch_input(self, workflow: dict, directory: str):
        for node in workflow.values():
            if node.get("class_type") == "LoadImageListFromDir //Inspire":
                node["inputs"]["directory"] = directory
                return

    def _patch_batch_output_prefix(self, workflow: dict, seg: int):
        for node in workflow.values():
            if node.get("class_type") == "VHS_VideoCombine":
                node["inputs"]["filename_prefix"] = f"Merge/{self._run_id}/Batch_{seg}"
                break

    def _bust_cache(self, workflow: dict):
        new_seed = int(uuid.uuid4().int % (2**32))
        for node in workflow.values():
            inp = node.get("inputs", {})
            if "noise_seed" in inp:
                inp["noise_seed"] = new_seed
            if "seed" in inp and isinstance(inp["seed"], int):
                inp["seed"] = new_seed

    # ------------------------------------------------------------------ #
    # Output collection
    # ------------------------------------------------------------------ #

    def _download_batch_outputs(self, seg: int, prompt_id: str, n: int) -> list[Path]:
        history_url = f"{self._url}/history/{prompt_id}"
        resp = requests.get(history_url, timeout=15)
        resp.raise_for_status()
        history = resp.json().get(prompt_id, {})

        all_files = []
        for node_output in history.get("outputs", {}).values():
            files = node_output.get("videos") or node_output.get("gifs") or []
            if files:
                all_files = sorted(files, key=lambda f: f["filename"])
                break

        if not all_files:
            if getattr(self, '_already_exists_seg', None) == seg:
                self._already_exists_seg = None
                self._log(f"  No history outputs — waiting 2s for writes to finish...")
                time.sleep(2)
                subfolder = f"Merge/{self._run_id}"
                downloaded = []
                for i in range(1, n + 1):
                    filename = f"Batch_{seg}_{i:05d}.mp4"
                    self._log(f"  Downloading {i}/{n}: {filename}")
                    params = {"filename": filename, "subfolder": subfolder, "type": "output"}
                    for attempt in range(6):
                        dl = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
                        if dl.status_code == 200:
                            break
                        self._log(f"  Not ready, retrying ({attempt+1}/6)...")
                        time.sleep(5)
                    dl.raise_for_status()
                    local = self._temp_dir / f"batch_seg{seg}_{i:03d}.mp4"
                    with open(local, 'wb') as f:
                        for chunk in dl.iter_content(1024 * 1024):
                            f.write(chunk)
                    downloaded.append(local)
                return downloaded
            raise RuntimeError(f"No output videos in history for batch segment {seg}")

        if len(all_files) != n:
            # A silent truncation here would stitch every image after the gap
            # to the wrong chain of videos — fail loudly instead.
            names = ", ".join(f["filename"] for f in all_files)
            raise RuntimeError(
                f"Segment {seg}: expected {n} output videos, ComfyUI returned "
                f"{len(all_files)} ({names or 'none'}). One or more images "
                f"failed on the server — check the ComfyUI console."
            )

        downloaded = []
        for idx, file_info in enumerate(all_files):
            filename = file_info["filename"]
            subfolder = file_info.get("subfolder", "")
            self._log(f"  Downloading {idx+1}/{len(all_files)}: {filename}")
            params = {"filename": filename, "subfolder": subfolder, "type": "output"}
            for attempt in range(6):
                dl = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
                if dl.status_code == 200:
                    break
                self._log(f"  Not ready, retrying ({attempt+1}/6)...")
                time.sleep(5)
            dl.raise_for_status()
            local = self._temp_dir / f"batch_seg{seg}_{idx+1:03d}.mp4"
            with open(local, 'wb') as f:
                for chunk in dl.iter_content(1024 * 1024):
                    f.write(chunk)
            downloaded.append(local)

        return downloaded

    # ------------------------------------------------------------------ #
    # Frame extraction
    # ------------------------------------------------------------------ #

    def _extract_last_frame_to(self, video_path: Path, dst: Path) -> Path:
        ffmpeg = self._config.get("ffmpeg_path", "ffmpeg")
        result = subprocess.run(
            [ffmpeg, "-y", "-sseof", "-0.1", "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", str(dst)],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg frame extraction failed:\n{result.stderr}")
        return dst

    # ------------------------------------------------------------------ #
    # Stitch
    # ------------------------------------------------------------------ #

    def _zip_segments(self, videos: list[Path], final_path: Path, src_image: Path, frames: list[Path] | None = None) -> Path:
        zip_dir = Path(self._config.get("zip_output_dir", self._config.get("final_video_dir", str(final_path.parent))))
        zip_dir.mkdir(parents=True, exist_ok=True)
        zip_path = zip_dir / f"{final_path.stem}.zip"
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
            if src_image.exists():
                zf.write(src_image, src_image.name)
            for seg_idx, frame in enumerate(frames or [], start=2):
                if frame.exists():
                    zf.write(frame, f"frame_start_seg{seg_idx}.png")
            for v in videos:
                zf.write(v, v.name)
            zf.write(final_path, final_path.name)
        return zip_path

    def _stitch(self, videos: list[Path], img_name: str) -> Path:
        final_dir = Path(self._config.get("final_video_dir", self._config["output_base_dir"]))
        final_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(img_name).stem
        final_path = final_dir / f"{stem}_{self._run_stamp}.mp4"
        n = len(videos)
        ffmpeg = self._config.get("ffmpeg_path", "ffmpeg")
        inputs = []
        for v in videos:
            inputs += ["-i", str(v)]
        filter_inputs = "".join(f"[{i}:v]" for i in range(n))
        filter_complex = f"{filter_inputs}concat=n={n}:v=1[out]"
        result = subprocess.run(
            [ffmpeg, "-y"] + inputs + [
                "-filter_complex", filter_complex,
                "-map", "[out]",
                "-c:v", "libx264", "-preset", "fast", "-crf", "18",
                "-an",
                str(final_path),
            ],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg stitch failed:\n{result.stderr[-3000:]}")
        return final_path

    # ------------------------------------------------------------------ #
    # API helpers
    # ------------------------------------------------------------------ #

    def _clean_temp_dir(self):
        removed = 0
        for f in self._temp_dir.iterdir():
            if f.is_file():
                f.unlink()
                removed += 1
        if removed:
            self._log(f"Cleared {removed} file(s) from temp folder.")

    def _queue_prompt(self, workflow: dict) -> str:
        resp = requests.post(
            f"{self._url}/prompt",
            json={"prompt": workflow, "client_id": self._client_id, "extra_data": {"extra_pnginfo": {}}},
            timeout=30
        )
        resp.raise_for_status()
        return resp.json()["prompt_id"]

    def _handle_execution_error(self, ex_msg: str, seg: int):
        """Shared error handling: 'already exists' means the outputs are on the
        server from a prior run — recover by downloading instead of failing."""
        if "already exists" in ex_msg or "Error opening output file" in ex_msg:
            self._log(f"[Segment {seg}/{self._total_segs}] Output exists on server, downloading...")
            self._already_exists_seg = seg
            return
        raise RuntimeError(f"ComfyUI execution error: {ex_msg}")

    def _history_done(self, prompt_id: str, seg: int) -> bool:
        """Check /history once. True if the prompt finished (or recovered via
        the already-exists path); raises on a real execution error."""
        h = requests.get(f"{self._url}/history/{prompt_id}", timeout=10).json()
        if prompt_id not in h:
            return False
        status = h[prompt_id].get("status", {})
        if status.get("completed", False):
            return True
        msgs = status.get("messages", [])
        if msgs and msgs[-1][0] == "execution_error":
            self._handle_execution_error(msgs[-1][1].get("exception_message", ""), seg)
            return True  # already-exists recovery
        return False

    def _wait_until_done(self, prompt_id: str, seg: int):
        """Wait for the prompt via websocket for live step progress; fall back
        to HTTP polling if the websocket can't connect or drops."""
        try:
            import websocket
        except ImportError:
            self._poll_until_done(prompt_id, seg)
            return

        ws_url = self._url.replace("https://", "wss://").replace("http://", "ws://")
        try:
            ws = websocket.create_connection(f"{ws_url}/ws?clientId={self._client_id}", timeout=20)
        except Exception as e:
            self._log(f"[Segment {seg}/{self._total_segs}] Websocket unavailable ({type(e).__name__}) — using polling")
            self._poll_until_done(prompt_id, seg)
            return

        start = time.time()
        last_minute_logged = 0
        try:
            while not self._cancelled:
                try:
                    msg = ws.recv()
                except websocket.WebSocketTimeoutException:
                    # Quiet stretch (model load, VAE decode) — confirm liveness
                    # via history so a missed finish can't hang us forever.
                    try:
                        if self._history_done(prompt_id, seg):
                            return
                    except requests.RequestException:
                        pass
                    minute = int(time.time() - start) // 60
                    if minute > last_minute_logged:
                        last_minute_logged = minute
                        self._log(f"[Segment {seg}/{self._total_segs}] Running... ({minute}m)")
                    continue
                except Exception:
                    self._log(f"[Segment {seg}/{self._total_segs}] Websocket dropped — using polling")
                    self._poll_until_done(prompt_id, seg)
                    return

                if isinstance(msg, bytes):
                    continue  # binary preview frames
                try:
                    payload = json.loads(msg)
                except ValueError:
                    continue
                mtype = payload.get("type")
                data = payload.get("data", {})
                if mtype == "progress":
                    self.step_progress.emit(seg, int(data.get("value", 0)), int(data.get("max", 1)))
                    minute = int(time.time() - start) // 60
                    if minute > last_minute_logged:
                        last_minute_logged = minute
                        self._log(f"[Segment {seg}/{self._total_segs}] Running... ({minute}m)")
                elif mtype == "executing" and data.get("prompt_id") == prompt_id and data.get("node") is None:
                    return  # prompt finished
                elif mtype == "execution_error" and data.get("prompt_id") == prompt_id:
                    self._handle_execution_error(data.get("exception_message", ""), seg)
                    return  # already-exists recovery
        finally:
            try:
                ws.close()
            except Exception:
                pass

    def _poll_until_done(self, prompt_id: str, seg: int):
        queue_url = f"{self._url}/queue"
        elapsed = 0
        while not self._cancelled:
            time.sleep(3)
            elapsed += 3
            try:
                q = requests.get(queue_url, timeout=10).json()
                running = [item[1] for item in q.get("queue_running", [])]
                pending = [item[1] for item in q.get("queue_pending", [])]
                if prompt_id in running:
                    if elapsed % 60 == 0:
                        self._log(f"[Segment {seg}/{self._total_segs}] Running... ({elapsed // 60}m)")
                    continue
                if prompt_id in pending:
                    if elapsed % 60 == 0:
                        self._log(f"[Segment {seg}/{self._total_segs}] Queued... ({elapsed // 60}m)")
                    continue
                if self._history_done(prompt_id, seg):
                    return
                if elapsed % 60 == 0:
                    self._log(f"[Segment {seg}/{self._total_segs}] Waiting for history... ({elapsed // 60}m)")
            except requests.RequestException as e:
                self._log(f"[Segment {seg}/{self._total_segs}] Poll error: {e}")

    # ------------------------------------------------------------------ #
    # Workflow loading (mirrors ChainWorker)
    # ------------------------------------------------------------------ #

    def _batch_chain_dir(self) -> Path:
        workflow_dir = Path(self._config["workflow_dir"])
        folder = self._config.get("active_chain_folder", "")
        return workflow_dir / folder if folder else workflow_dir

    def _load_workflow(self, wf: dict) -> dict:
        path = self._batch_chain_dir() / wf["json_file"]
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _build_effective_workflows(self) -> list[dict]:
        template = self._config.get("workflows", [])
        chain_dir = self._batch_chain_dir()
        files = sorted(chain_dir.glob("workflow_segment_*_batch.json"))
        if not files:
            return template
        video_entries = [t for t in template if t.get("input_type") in ("video", "frame")]
        fallback = video_entries[-1] if video_entries else (template[-1] if template else {})
        segs = []
        for i, f in enumerate(files, 1):
            tmpl = template[i - 1] if i - 1 < len(template) else fallback
            segs.append({
                "segment": i,
                "json_file": f.name,
                "input_node_id": tmpl.get("input_node_id", ""),
                "input_type": tmpl.get("input_type", "frame"),
            })
        return segs

    def _trim_log(self, log_path: Path, keep: int):
        delimiter = "=== New batch run started ==="
        if not log_path.exists():
            return
        text = log_path.read_text(encoding='utf-8')
        parts = text.split(delimiter)
        # parts[0] is anything before the first delimiter (empty or header noise)
        batches = [p for p in parts[1:] if p.strip()]
        if len(batches) >= keep:
            trimmed = delimiter.join([""] + batches[-(keep - 1):])
            log_path.write_text(trimmed.lstrip('\n'), encoding='utf-8')

    def _fmt(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}m {s:02d}s"
