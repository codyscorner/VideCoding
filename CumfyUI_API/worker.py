import json
import logging
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

logger = logging.getLogger("chain")
logger.setLevel(logging.DEBUG)


def _init_log(base_dir: Path):
    fh = logging.FileHandler(str(base_dir / "run_log.txt"), mode='w', encoding='utf-8')
    fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))
    logger.handlers.clear()
    logger.addHandler(fh)


class ChainWorker(QThread):
    log = pyqtSignal(str)
    segment_done = pyqtSignal(int)
    segment_time = pyqtSignal(int, str)
    stitch_done = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, config: dict, starting_image: str):
        super().__init__()
        self._config = config
        self._starting_image = starting_image
        self._cancelled = False
        self._total_segs = len(config.get("workflows", []))
        self._client_id = str(uuid.uuid4())
        self._run_id = str(int(time.time() * 1000))
        self._runpod_override_filename = None
        self._runpod = config.get("mode", "local") == "runpod"
        self._url = (
            config.get("runpod_url", "").rstrip("/")
            if self._runpod
            else config.get("comfyui_url", "http://127.0.0.1:8000").rstrip("/")
        )
        base_dir = Path(config.get("_base_dir", str(Path(__file__).parent)))
        self._temp_dir = base_dir / "temp"
        _init_log(base_dir)

    def cancel(self):
        self._cancelled = True

    # ------------------------------------------------------------------ #
    # Main thread entry
    # ------------------------------------------------------------------ #

    def _log(self, msg: str, level: str = "info"):
        self.log.emit(msg)
        getattr(logger, level)(msg)

    def run(self):
        try:
            logger.info("=== New run started ===")
            self._temp_dir.mkdir(exist_ok=True)
            self._clean_temp_dir()
            self._clean_merge_dir()
            output_videos = []
            workflows = self._build_effective_workflows()
            self._total_segs = len(workflows)
            chain_start = time.time()

            input_path = Path(self._config["input_dir"]) / self._starting_image
            self._log(f"Uploading starting image: {input_path.name}")
            self._upload_image(input_path)

            for wf in workflows:
                if self._cancelled:
                    self._log("Cancelled by user.")
                    return

                seg = wf["segment"]
                seg_start = time.time()
                self._log(f"[Segment {seg}/{self._total_segs}] Starting...")

                workflow_json = self._load_workflow(wf)

                # Always randomize seeds to bust ComfyUI prompt cache
                self._bust_cache(workflow_json)

                # Always normalize output prefix so _find_local_output_video can locate the file
                self._patch_output_prefix(workflow_json, seg)

                if wf["input_type"] == "image":
                    image_filename = Path(self._starting_image).name
                    workflow_json[wf["input_node_id"]]["inputs"]["image"] = image_filename
                    self._log(f"[Segment {seg}/{self._total_segs}] Using starting image: {image_filename}")
                else:
                    # All subsequent segments: extract last frame from previous video and upload as image
                    prev_video = output_videos[-1]
                    self._log(f"[Segment {seg}/{self._total_segs}] Extracting last frame from: {prev_video.name}")
                    frame_path = self._extract_last_frame(prev_video, seg)
                    self._log(f"[Segment {seg}/{self._total_segs}] Uploading frame: {frame_path.name}")
                    uploaded_name = self._upload_image(frame_path)
                    workflow_json[wf["input_node_id"]]["inputs"]["image"] = uploaded_name
                    self._log(f"[Segment {seg}/{self._total_segs}] Uploaded as: {uploaded_name}")

                prompt_id = self._queue_prompt(workflow_json)
                self._log(f"[Segment {seg}/{self._total_segs}] Queued (id: {prompt_id[:8]}...), polling...")

                self._poll_until_done(prompt_id, seg)

                if self._runpod:
                    time.sleep(5)
                output_video = self._get_output_video(seg, prompt_id)
                seg_elapsed = time.time() - seg_start
                elapsed_str = self._fmt(seg_elapsed)
                self._log(f"[Segment {seg}/{self._total_segs}] Done in {elapsed_str} → {output_video.name}")
                output_videos.append(output_video)
                self.segment_done.emit(seg)
                self.segment_time.emit(seg, elapsed_str)

            if self._cancelled:
                return

            self._log("All segments complete. Stitching final video...")
            final_path = self._stitch(output_videos)
            self._log(f"Final video: {final_path}")

            self._log("Zipping segment files...")
            zip_path = self._zip_segments(output_videos, final_path)
            self._log(f"Archive: {zip_path.name}")
            self._log(f"Total time: {self._fmt(time.time() - chain_start)}")
            self.stitch_done.emit(str(final_path))

        except Exception as e:
            logger.exception("Chain error")
            self.error.emit(str(e))

    # ------------------------------------------------------------------ #
    # Output video retrieval
    # ------------------------------------------------------------------ #

    def _get_output_video(self, seg: int, prompt_id: str) -> Path:
        return self._download_output_video(seg, prompt_id)

    def _fetch_output_video_by_prefix(self, seg: int) -> Path | None:
        """Download the expected output video using the known prefix we patched in.
        VHS_VideoCombine names files as {prefix_last_part}_00001.mp4, so we try a
        few sequence numbers via /view without relying on the history API at all."""
        subfolder = f"Merge/{self._run_id}"
        for n in range(1, 6):
            filename = f"Segment_{seg}_{n:05d}.mp4"
            params = {"filename": filename, "subfolder": subfolder, "type": "output"}
            try:
                resp = requests.get(f"{self._url}/view", params=params, timeout=60, stream=True)
                if resp.status_code == 200:
                    local_path = self._temp_dir / filename
                    with open(local_path, 'wb') as f:
                        for chunk in resp.iter_content(chunk_size=1024 * 1024):
                            f.write(chunk)
                    return local_path
            except requests.RequestException:
                pass
        return None

    def _bust_cache(self, workflow: dict):
        new_seed = int(uuid.uuid4().int % (2**32))
        for node in workflow.values():
            inp = node.get("inputs", {})
            if "noise_seed" in inp:
                inp["noise_seed"] = new_seed
            if "seed" in inp and isinstance(inp["seed"], int):
                inp["seed"] = new_seed

    def _patch_output_prefix(self, workflow: dict, seg: int):
        _VIDEO_COMBINE_TYPES = {"VHS_VideoCombine", "VHS_VideoCombineV2", "SaveVideo"}
        for node in workflow.values():
            ct = node.get("class_type", "")
            if ct in _VIDEO_COMBINE_TYPES:
                node["inputs"]["filename_prefix"] = f"Merge/{self._run_id}/Segment_{seg}"
                self._log(f"[Segment {seg}/{self._total_segs}] Patched output prefix on {ct}")
                return
        class_types = [n.get("class_type", "?") for n in workflow.values()]
        self._log(f"[Segment {seg}/{self._total_segs}] WARNING: no video combine node found. "
                  f"Nodes: {', '.join(sorted(set(class_types)))}")

    def _download_output_video(self, seg: int, prompt_id: str) -> Path:
        # Check if polling extracted filename from "already exists" error
        override = getattr(self, '_runpod_override_filename', None)
        if override:
            self._runpod_override_filename = None
            parts = override.rsplit('/', 1)
            ov_subfolder = parts[0] if len(parts) == 2 else ""
            ov_filename = parts[-1]
            self._log(f"[Segment {seg}/{self._total_segs}] Downloading (existing): {override}")
            params = {"filename": ov_filename, "subfolder": ov_subfolder, "type": "output"}
            for attempt in range(6):
                dl_resp = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
                if dl_resp.status_code == 200:
                    break
                self._log(f"[Segment {seg}/{self._total_segs}] File not ready, retrying in 5s... ({attempt+1}/6)")
                time.sleep(5)
            dl_resp.raise_for_status()
            local_path = self._temp_dir / Path(ov_filename).name
            with open(local_path, 'wb') as f:
                for chunk in dl_resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            merge_dir = Path(self._config["output_base_dir"])
            merge_dir.mkdir(parents=True, exist_ok=True)
            dest = merge_dir / Path(ov_filename).name
            dest.write_bytes(local_path.read_bytes())
            return dest

        # Get filename from history
        history_url = f"{self._url}/history/{prompt_id}"
        resp = requests.get(history_url, timeout=15)
        resp.raise_for_status()
        history = resp.json().get(prompt_id, {})

        _VIDEO_EXTS = {".mp4", ".webm", ".avi", ".mov", ".mkv", ".gif"}
        filename = None
        subfolder = ""
        for node_output in history.get("outputs", {}).values():
            # VHS_VideoCombine may report under "videos", "gifs", or "images" depending on version
            all_files = []
            for key in ("videos", "gifs", "images"):
                candidates = node_output.get(key, [])
                video_candidates = [f for f in candidates if Path(f["filename"]).suffix.lower() in _VIDEO_EXTS]
                all_files.extend(video_candidates)
            if all_files:
                match = next(
                    (f for f in all_files if f"Segment_{seg}_" in f["filename"]),
                    all_files[0]
                )
                filename = match["filename"]
                subfolder = match.get("subfolder", "")
                break

        if not filename:
            status_info = history.get("status", {})
            messages = status_info.get("messages", [])
            logger.debug(f"Segment {seg} history status: {status_info}")
            logger.debug(f"Segment {seg} history outputs: {history.get('outputs', {})}")
            errors = [m for m in messages if m[0] in ("execution_error", "execution_interrupted")]
            if errors:
                ex_msg = errors[-1][1].get("exception_message", str(errors[-1][1]))
                raise RuntimeError(f"Segment {seg} failed in ComfyUI: {ex_msg}")

            # History didn't report a video — fetch it directly using the known prefix.
            # We patched the prefix to Merge/{run_id}/Segment_{seg} so we know the filename.
            self._log(f"[Segment {seg}/{self._total_segs}] Not in history — fetching by prefix...")
            fetched = self._fetch_output_video_by_prefix(seg)
            if fetched:
                self._log(f"[Segment {seg}/{self._total_segs}] Fetched: {fetched.name}")
                merge_dir = Path(self._config["output_base_dir"])
                merge_dir.mkdir(parents=True, exist_ok=True)
                dest = merge_dir / fetched.name
                if fetched != dest:
                    dest.write_bytes(fetched.read_bytes())
                return dest

            all_found = []
            for node_output in history.get("outputs", {}).values():
                for key in ("videos", "gifs", "images"):
                    for f in node_output.get(key, []):
                        all_found.append(f"{key}:{f.get('filename', '?')}")
            outputs_keys = {k for v in history.get("outputs", {}).values() for k in v}
            detail = ", ".join(all_found) if all_found else "none"
            raise RuntimeError(
                f"Could not find output video in history for segment {seg}.\n"
                f"Output keys present: {outputs_keys or 'none'}\n"
                f"Files found: {detail}"
            )

        self._log(f"[Segment {seg}/{self._total_segs}] Downloading: {subfolder}/{filename}")
        params = {"filename": filename, "subfolder": subfolder, "type": "output"}
        for attempt in range(6):
            dl_resp = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
            if dl_resp.status_code == 200:
                break
            self._log(f"[Segment {seg}/{self._total_segs}] File not ready, retrying in 5s... ({attempt+1}/6)")
            time.sleep(5)
        dl_resp.raise_for_status()

        local_path = self._temp_dir / filename
        with open(local_path, 'wb') as f:
            for chunk in dl_resp.iter_content(chunk_size=1024 * 1024):
                f.write(chunk)

        # Also copy to Merge folder for consistency
        merge_dir = Path(self._config["output_base_dir"])
        merge_dir.mkdir(parents=True, exist_ok=True)
        dest = merge_dir / filename
        dest.write_bytes(local_path.read_bytes())
        return dest

    # ------------------------------------------------------------------ #
    # Upload helpers
    # ------------------------------------------------------------------ #

    def _extract_last_frame(self, video_path: Path, seg: int) -> Path:
        frame_path = self._temp_dir / f"frame_seg{seg}.png"
        ffmpeg = self._config.get("ffmpeg_path", "ffmpeg")
        result = subprocess.run(
            [ffmpeg, "-y", "-sseof", "-0.1", "-i", str(video_path),
             "-vframes", "1", "-q:v", "2", str(frame_path)],
            capture_output=True, text=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg frame extraction failed:\n{result.stderr}")
        return frame_path

    def _upload_image(self, image_path: Path) -> str:
        url = f"{self._url}/upload/image"
        with open(image_path, 'rb') as f:
            resp = requests.post(
                url,
                files={"image": (image_path.name, f, "image/png")},
                data={"type": "input", "overwrite": "true"},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["name"]

    def _queue_prompt(self, workflow: dict) -> str:
        url = f"{self._url}/prompt"
        payload = {
            "prompt": workflow,
            "client_id": self._client_id,
            "extra_data": {"extra_pnginfo": {}},
        }
        resp = requests.post(url, json=payload, timeout=30)
        if not resp.ok:
            try:
                detail = resp.json()
            except Exception:
                detail = resp.text
            raise RuntimeError(f"ComfyUI rejected prompt ({resp.status_code}): {detail}")
        return resp.json()["prompt_id"]

    # ------------------------------------------------------------------ #
    # Polling
    # ------------------------------------------------------------------ #

    def _poll_until_done(self, prompt_id: str, seg: int):
        queue_url = f"{self._url}/queue"
        history_url = f"{self._url}/history/{prompt_id}"
        elapsed = 0
        while not self._cancelled:
            time.sleep(3)
            elapsed += 3
            try:
                q_resp = requests.get(queue_url, timeout=10)
                q_resp.raise_for_status()
                q_data = q_resp.json()
                running_ids = [item[1] for item in q_data.get("queue_running", [])]
                pending_ids = [item[1] for item in q_data.get("queue_pending", [])]
                if prompt_id in running_ids:
                    if elapsed % 15 == 0:
                        self._log(f"[Segment {seg}/{self._total_segs}] Running... ({elapsed}s)")
                    continue
                if prompt_id in pending_ids:
                    if elapsed % 15 == 0:
                        self._log(f"[Segment {seg}/{self._total_segs}] Queued, waiting... ({elapsed}s)")
                    continue

                h_resp = requests.get(history_url, timeout=10)
                h_resp.raise_for_status()
                h_data = h_resp.json()
                if prompt_id in h_data:
                    status = h_data[prompt_id].get("status", {})
                    msgs = status.get("messages", [])
                    # Check for execution errors before treating as done
                    error_msgs = [m for m in msgs if m[0] == "execution_error"]
                    if error_msgs:
                        ex_msg = error_msgs[-1][1].get("exception_message", str(error_msgs[-1][1]))
                        if "already exists" in ex_msg:
                            self._log(f"[Segment {seg}/{self._total_segs}] File exists on pod, downloading...")
                            import re
                            match = re.search(r"output/(.+?)'\s+already exists", ex_msg)
                            if match:
                                self._runpod_override_filename = match.group(1)
                            return
                        raise RuntimeError(f"Segment {seg} failed in ComfyUI: {ex_msg}")
                    if status.get("completed", False):
                        all_msg_types = [m[0] for m in msgs]
                        self._log(f"[Segment {seg}/{self._total_segs}] ComfyUI completed. Messages: {all_msg_types}")
                        return
                    self._log(f"[Segment {seg}/{self._total_segs}] Status: {msgs[-1] if msgs else 'unknown'}")
            except requests.RequestException as e:
                self._log(f"[Segment {seg}/{self._total_segs}] Poll error: {e}")
            if elapsed % 15 == 0:
                self._log(f"[Segment {seg}/{self._total_segs}] Waiting... ({elapsed}s)")

    # ------------------------------------------------------------------ #
    # Stitch / zip / misc
    # ------------------------------------------------------------------ #

    def _clean_temp_dir(self):
        removed = 0
        for f in self._temp_dir.iterdir():
            if f.is_file():
                f.unlink()
                removed += 1
        if removed:
            self._log(f"Cleared {removed} file(s) from temp folder.")

    def _clean_merge_dir(self):
        merge_dir = Path(self._config["output_base_dir"])
        merge_dir.mkdir(parents=True, exist_ok=True)
        removed = 0
        for f in merge_dir.iterdir():
            if f.is_file() and f.suffix.lower() in {".mp4", ".png", ".jpg", ".jpeg", ".webp"}:
                f.unlink()
                removed += 1
        if removed:
            self._log(f"Cleared {removed} file(s) from Merge folder.")

    def _fmt(self, seconds: float) -> str:
        m, s = divmod(int(seconds), 60)
        return f"{m:02d}m {s:02d}s"

    # Known ComfyUI image loader class types (single frame injection)
    _IMAGE_LOADER_TYPES = {"LoadImage", "LoadImageMask", "Load Image", "LoadImagesFromDirectory", "LoadImageListFromDir //Inspire"}

    def _detect_input_node(self, workflow: dict, seg_index: int) -> tuple[str, str]:
        """Auto-detect the LoadImage node that receives the injected frame/image."""
        for nid, node in workflow.items():
            if node.get("class_type") in self._IMAGE_LOADER_TYPES:
                return nid, "image" if seg_index == 0 else "frame"
        # Structural fallback: any node with a plain string "image" input
        for nid, node in workflow.items():
            if isinstance(node.get("inputs", {}).get("image"), str):
                return nid, "image" if seg_index == 0 else "frame"
        raise RuntimeError(
            "Could not auto-detect input node — no LoadImage node found in workflow"
        )

    def _build_effective_workflows(self) -> list[dict]:
        """Discover segments by scanning the chain folder; auto-detect input node + type."""
        workflow_dir = Path(self._config["workflow_dir"])
        folder = self._config.get("active_chain_folder", "")

        chain_dir = (workflow_dir / folder) if folder else workflow_dir
        files = sorted(f for f in chain_dir.glob("workflow_segment_*.json") if "_batch" not in f.name)

        if not files:
            return self._config.get("workflows", [])

        segs = []
        for i, f in enumerate(files, 1):
            try:
                with open(f, "r", encoding="utf-8") as fh:
                    wf_json = json.load(fh)
                node_id, input_type = self._detect_input_node(wf_json, i - 1)
            except Exception as e:
                raise RuntimeError(f"Failed to read/parse {f.name}: {e}")
            logger.info(f"Segment {i}: {f.name} → node {node_id} ({input_type})")
            segs.append({
                "segment": i,
                "json_file": f.name,
                "input_node_id": node_id,
                "input_type": input_type,
            })
        return segs

    def _load_workflow(self, wf: dict) -> dict:
        workflow_dir = Path(self._config["workflow_dir"])
        folder = self._config.get("active_chain_folder", "")
        if folder:
            path = workflow_dir / folder / wf["json_file"]
        else:
            path = workflow_dir / wf["json_file"]
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _stitch(self, videos: list[Path]) -> Path:
        final_dir = Path(self._config.get("final_video_dir", self._config["output_base_dir"]))
        final_dir.mkdir(parents=True, exist_ok=True)

        stem = Path(self._starting_image).stem
        final_path = final_dir / f"{stem}.mp4"
        n = len(videos)
        self._log(f"Stitching {n} segments: {[v.name for v in videos]}")

        # Use concat filter (not demuxer) so mixed codecs (H.264 + HEVC) are decoded
        # individually before being joined — much more robust than stream copy concat.
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
        if result.stderr:
            logger.debug(f"FFmpeg stitch stderr:\n{result.stderr[-3000:]}")

        return final_path

    def _zip_segments(self, videos: list[Path], final_path: Path) -> Path:
        zip_dir = Path(self._config.get("zip_output_dir", self._config["output_base_dir"]))
        zip_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(self._starting_image).stem
        zip_path = zip_dir / f"{stem}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
            src = Path(self._starting_image)
            if src.exists():
                zf.write(src, src.name)
            for v in videos:
                zf.write(v, v.name)
            zf.write(final_path, final_path.name)

        return zip_path
