import json
import logging
import subprocess
import time
import uuid
import zipfile
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal

LOG_FILE = Path(__file__).parent / "run_log.txt"

logger = logging.getLogger("chain")
logger.setLevel(logging.DEBUG)
_fh = logging.FileHandler(str(LOG_FILE), mode='w', encoding='utf-8')
_fh.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s', datefmt='%H:%M:%S'))
logger.addHandler(_fh)


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
        self._client_id = str(uuid.uuid4())
        self._run_id = str(int(time.time()))
        self._runpod_override_filename = None
        self._runpod = config.get("mode", "local") == "runpod"
        self._url = (
            config.get("runpod_url", "").rstrip("/")
            if self._runpod
            else config.get("comfyui_url", "http://127.0.0.1:8000").rstrip("/")
        )
        self._temp_dir = Path(__file__).parent / "temp"

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
            self._clean_merge_dir()
            output_videos = []
            workflows = self._config["workflows"]
            chain_start = time.time()

            if self._runpod:
                input_path = Path(self._config["input_dir"]) / self._starting_image
                self._log(f"[RunPod] Uploading starting image: {self._starting_image}")
                self._upload_image(input_path)

            for wf in workflows:
                if self._cancelled:
                    self._log("Cancelled by user.")
                    return

                seg = wf["segment"]
                seg_start = time.time()
                self._log(f"[Segment {seg}/7] Starting...")

                workflow_json = self._load_workflow(wf)

                # RunPod: strip Windows path from filename_prefix — use simple Segment_N
                if self._runpod:
                    self._patch_output_prefix(workflow_json, seg)

                if wf["input_type"] == "image":
                    workflow_json[wf["input_node_id"]]["inputs"]["image"] = self._starting_image
                    self._log(f"[Segment {seg}/7] Using starting image: {self._starting_image}")
                else:
                    prev_video = output_videos[-1]
                    # Rename with _GLF suffix when uploading to RunPod to avoid filename collision
                    if self._runpod:
                        glf_name = prev_video.stem + "_GLF" + prev_video.suffix
                        glf_path = self._temp_dir / glf_name
                        glf_path.write_bytes(prev_video.read_bytes())
                        upload_path = glf_path
                    else:
                        upload_path = prev_video
                    self._log(f"[Segment {seg}/7] Uploading video: {upload_path.name}")
                    uploaded_name = self._upload_video(upload_path)
                    workflow_json[wf["input_node_id"]]["inputs"]["video"] = uploaded_name
                    self._log(f"[Segment {seg}/7] Uploaded as: {uploaded_name}")

                prompt_id = self._queue_prompt(workflow_json)
                self._log(f"[Segment {seg}/7] Queued (id: {prompt_id[:8]}...), polling...")

                self._poll_until_done(prompt_id, seg)

                if self._runpod:
                    time.sleep(5)
                output_video = self._get_output_video(seg, prompt_id)
                seg_elapsed = time.time() - seg_start
                elapsed_str = self._fmt(seg_elapsed)
                self._log(f"[Segment {seg}/7] Done in {elapsed_str} → {output_video.name}")
                output_videos.append(output_video)
                self.segment_done.emit(seg)
                self.segment_time.emit(seg, elapsed_str)

            if self._cancelled:
                return

            self._log("All segments complete. Stitching final video...")
            final_path = self._stitch(output_videos)
            total_elapsed = time.time() - chain_start
            self._log(f"Total time: {self._fmt(total_elapsed)}")
            self._log(f"Final video: {final_path}")

            self._log("Zipping segment files...")
            zip_path = self._zip_segments(output_videos, final_path)
            self._log(f"Archive: {zip_path.name}")
            self.stitch_done.emit(str(final_path))

        except Exception as e:
            logger.exception("Chain error")
            self.error.emit(str(e))

    # ------------------------------------------------------------------ #
    # Output video retrieval
    # ------------------------------------------------------------------ #

    def _get_output_video(self, seg: int, prompt_id: str) -> Path:
        if self._runpod:
            return self._download_output_video(seg, prompt_id)
        return self._find_local_output_video(seg)

    def _patch_output_prefix(self, workflow: dict, seg: int):
        seg_id = str(uuid.uuid4())[:8]
        new_seed = int(uuid.uuid4().int % (2**32))
        for node in workflow.values():
            ct = node.get("class_type", "")
            inp = node.get("inputs", {})
            if ct == "VHS_VideoCombine":
                inp["filename_prefix"] = f"Merge/Segment_{seg}_{seg_id}"
            # Randomize seed on any sampler or noise node to bust cache
            if "noise_seed" in inp:
                inp["noise_seed"] = new_seed
            if "seed" in inp and isinstance(inp["seed"], int):
                inp["seed"] = new_seed

    def _find_local_output_video(self, seg: int) -> Path:
        base_dir = Path(self._config["output_base_dir"])
        mp4s = sorted(
            base_dir.glob(f"Segment_{seg}_*.mp4"),
            key=lambda p: p.stat().st_mtime,
            reverse=True
        )
        if not mp4s:
            raise FileNotFoundError(f"No .mp4 found in {base_dir} matching Segment_{seg}_*.mp4")
        return mp4s[0]

    def _download_output_video(self, seg: int, prompt_id: str) -> Path:
        # Check if polling extracted filename from "already exists" error
        override = getattr(self, '_runpod_override_filename', None)
        if override:
            self._runpod_override_filename = None
            parts = override.rsplit('/', 1)
            ov_subfolder = parts[0] if len(parts) == 2 else ""
            ov_filename = parts[-1]
            self._log(f"[Segment {seg}/7] Downloading (existing): {override}")
            params = {"filename": ov_filename, "subfolder": ov_subfolder, "type": "output"}
            for attempt in range(6):
                dl_resp = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
                if dl_resp.status_code == 200:
                    break
                self._log(f"[Segment {seg}/7] File not ready, retrying in 5s... ({attempt+1}/6)")
                time.sleep(5)
            dl_resp.raise_for_status()
            local_path = self._temp_dir / Path(dl_filename).name
            with open(local_path, 'wb') as f:
                for chunk in dl_resp.iter_content(chunk_size=1024 * 1024):
                    f.write(chunk)
            merge_dir = Path(self._config["output_base_dir"])
            merge_dir.mkdir(parents=True, exist_ok=True)
            dest = merge_dir / Path(dl_filename).name
            dest.write_bytes(local_path.read_bytes())
            return dest

        # Get filename from history
        history_url = f"{self._url}/history/{prompt_id}"
        resp = requests.get(history_url, timeout=15)
        resp.raise_for_status()
        history = resp.json().get(prompt_id, {})

        filename = None
        subfolder = ""
        for node_output in history.get("outputs", {}).values():
            files = node_output.get("videos") or node_output.get("gifs") or []
            if files:
                match = next(
                    (f for f in files if f"Segment_{seg}_" in f["filename"]),
                    files[0]
                )
                filename = match["filename"]
                subfolder = match.get("subfolder", "")
                break

        if not filename:
            raise RuntimeError(f"Could not find output video in history for segment {seg}")

        dl_filename = filename
        self._log(f"[Segment {seg}/7] Downloading: {subfolder}/{filename}")
        params = {"filename": filename, "subfolder": subfolder, "type": "output"}
        for attempt in range(6):
            dl_resp = requests.get(f"{self._url}/view", params=params, timeout=300, stream=True)
            if dl_resp.status_code == 200:
                break
            self._log(f"[Segment {seg}/7] File not ready, retrying in 5s... ({attempt+1}/6)")
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

    def _upload_video(self, video_path: Path) -> str:
        url = f"{self._url}/upload/image"
        with open(video_path, 'rb') as f:
            resp = requests.post(
                url,
                files={"image": (video_path.name, f, "video/mp4")},
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
        resp.raise_for_status()
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
                        self._log(f"[Segment {seg}/7] Running... ({elapsed}s)")
                    continue
                if prompt_id in pending_ids:
                    if elapsed % 15 == 0:
                        self._log(f"[Segment {seg}/7] Queued, waiting... ({elapsed}s)")
                    continue

                h_resp = requests.get(history_url, timeout=10)
                h_resp.raise_for_status()
                h_data = h_resp.json()
                if prompt_id in h_data:
                    status = h_data[prompt_id].get("status", {})
                    msgs = status.get("messages", [])
                    if status.get("completed", False):
                        return
                    # Treat execution_error from "already exists" as complete — file is there
                    last_msg = msgs[-1][0] if msgs else ""
                    if last_msg == "execution_error":
                        ex_msg = msgs[-1][1].get("exception_message", "")
                        if "already exists" in ex_msg:
                            self._log(f"[Segment {seg}/7] File exists on pod, downloading...")
                            # Extract actual filename from error path
                            import re
                            match = re.search(r"output/(.+?)'\s+already exists", ex_msg)
                            if match:
                                self._runpod_override_filename = match.group(1)
                            return
                    self._log(f"[Segment {seg}/7] Status: {msgs[-1] if msgs else 'unknown'}")
            except requests.RequestException as e:
                self._log(f"[Segment {seg}/7] Poll error: {e}")
            if elapsed % 15 == 0:
                self._log(f"[Segment {seg}/7] Waiting... ({elapsed}s)")

    # ------------------------------------------------------------------ #
    # Stitch / zip / misc
    # ------------------------------------------------------------------ #

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

    def _load_workflow(self, wf: dict) -> dict:
        workflow_dir = Path(self._config["workflow_dir"])
        path = workflow_dir / wf["json_file"]
        with open(path, 'r') as f:
            return json.load(f)

    def _stitch(self, videos: list[Path]) -> Path:
        final_dir = Path(self._config.get("final_video_dir", self._config["output_base_dir"]))
        final_dir.mkdir(parents=True, exist_ok=True)

        concat_file = self._temp_dir / "concat_list.txt"
        lines = [f"file '{v.as_posix()}'" for v in videos]
        concat_file.write_text("\n".join(lines), encoding="utf-8")

        stem = Path(self._starting_image).stem
        final_path = final_dir / f"{stem}.mp4"

        ffmpeg = self._config.get("ffmpeg_path", "ffmpeg")
        result = subprocess.run(
            [ffmpeg, "-y", "-f", "concat", "-safe", "0",
             "-i", str(concat_file), "-c", "copy", str(final_path)],
            capture_output=True, text=True
        )
        concat_file.unlink(missing_ok=True)

        if result.returncode != 0:
            raise RuntimeError(f"FFmpeg stitch failed:\n{result.stderr}")

        return final_path

    def _zip_segments(self, videos: list[Path], final_path: Path) -> Path:
        zip_dir = Path(self._config.get("zip_output_dir", self._config["output_base_dir"]))
        zip_dir.mkdir(parents=True, exist_ok=True)
        stem = Path(self._starting_image).stem
        zip_path = zip_dir / f"{stem}.zip"

        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_STORED) as zf:
            for v in videos:
                zf.write(v, v.name)
            zf.write(final_path, final_path.name)

        return zip_path
