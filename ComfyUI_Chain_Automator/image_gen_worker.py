import json
import random
import time
import uuid
from pathlib import Path

import requests
from PyQt6.QtCore import QThread, pyqtSignal


def _find_node_by_class(workflow: dict, class_type: str):
    for k, v in workflow.items():
        if v.get("class_type") == class_type:
            return k, v
    return None


class ImageGenWorker(QThread):
    log = pyqtSignal(str)
    image_ready = pyqtSignal(str)   # absolute path to saved image
    error = pyqtSignal(str)

    def __init__(self, config: dict, workflow_path: Path,
                 positive: str, negative: str, seed: int,
                 reference_images: list[Path] | None = None):
        super().__init__()
        self._config = config
        self._workflow_path = workflow_path
        self._positive = positive
        self._negative = negative
        self._seed = seed
        self._reference_images = reference_images or []
        self._cancelled = False
        self._client_id = str(uuid.uuid4())
        self._runpod = config.get("mode", "local") == "runpod"
        self._url = (
            config.get("runpod_url", "").rstrip("/")
            if self._runpod
            else config.get("comfyui_url", "http://127.0.0.1:8000").rstrip("/")
        )
        base_dir = Path(config.get("_base_dir", str(Path(__file__).parent)))
        self._temp_dir = base_dir / "temp"

    def cancel(self):
        self._cancelled = True

    def _log(self, msg: str):
        self.log.emit(msg)

    # ------------------------------------------------------------------ #
    # Main thread entry
    # ------------------------------------------------------------------ #

    def run(self):
        try:
            self._temp_dir.mkdir(exist_ok=True)

            with open(self._workflow_path, 'r', encoding='utf-8') as f:
                workflow = json.load(f)

            seed = self._seed if self._seed >= 0 else random.randint(0, 2**31)
            self._patch_workflow(workflow, seed)

            if self._reference_images:
                self._upload_references(workflow)

            self._log("Queuing image generation workflow...")
            prompt_id = self._queue_prompt(workflow)
            self._log(f"Queued (id: {prompt_id[:8]}...), polling...")

            self._poll_until_done(prompt_id)

            if self._cancelled:
                return

            self._log("Generation complete — retrieving image...")
            image_path = self._get_output_image(prompt_id)
            self._log(f"Saved: {image_path.name}")
            self.image_ready.emit(str(image_path))

        except Exception as e:
            self.error.emit(str(e))

    # ------------------------------------------------------------------ #
    # Workflow patching
    # ------------------------------------------------------------------ #

    def _patch_workflow(self, workflow: dict, seed: int):
        # Positive prompt — prefer PrimitiveStringMultiline, fall back to CLIPTextEncode
        pos_patched = False
        result = _find_node_by_class(workflow, "PrimitiveStringMultiline")
        if result:
            _, node = result
            node["inputs"]["value"] = self._positive
            pos_patched = True

        if not pos_patched:
            for _, node in workflow.items():
                if node.get("class_type") == "CLIPTextEncode":
                    meta = node.get("_meta", {}).get("title", "").lower()
                    if "neg" not in meta:
                        node["inputs"]["text"] = self._positive
                        pos_patched = True
                        break

        # Negative prompt — find CLIPTextEncode with "neg" in title
        for _, node in workflow.items():
            if node.get("class_type") == "CLIPTextEncode":
                meta = node.get("_meta", {}).get("title", "").lower()
                if "neg" in meta:
                    node["inputs"]["text"] = self._negative
                    break

        # Seed — KSampler first, then any noise_seed / seed int fields
        result = _find_node_by_class(workflow, "KSampler")
        if result:
            _, node = result
            node["inputs"]["seed"] = seed

        for node in workflow.values():
            inp = node.get("inputs", {})
            if "noise_seed" in inp:
                inp["noise_seed"] = seed
            if "seed" in inp and isinstance(inp["seed"], int):
                inp["seed"] = seed

    # ------------------------------------------------------------------ #
    # Reference image upload
    # ------------------------------------------------------------------ #

    def _upload_references(self, workflow: dict):
        load_nodes = sorted(
            [(k, v) for k, v in workflow.items() if v.get("class_type") == "LoadImage"],
            key=lambda x: x[0],
        )
        for i, img_path in enumerate(self._reference_images[:len(load_nodes)]):
            node_id, _ = load_nodes[i]
            self._log(f"Uploading reference image {i + 1}: {img_path.name}")
            uploaded_name = self._upload_image(img_path)
            workflow[node_id]["inputs"]["image"] = uploaded_name
            self._log(f"Reference {i + 1} uploaded as: {uploaded_name}")

    def _upload_image(self, image_path: Path) -> str:
        with open(image_path, "rb") as f:
            resp = requests.post(
                f"{self._url}/upload/image",
                files={"image": (image_path.name, f, "image/png")},
                data={"type": "input", "overwrite": "true"},
                timeout=120,
            )
        resp.raise_for_status()
        return resp.json()["name"]

    # ------------------------------------------------------------------ #
    # API helpers
    # ------------------------------------------------------------------ #

    def _queue_prompt(self, workflow: dict) -> str:
        resp = requests.post(
            f"{self._url}/prompt",
            json={"prompt": workflow, "client_id": self._client_id},
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["prompt_id"]

    def _poll_until_done(self, prompt_id: str):
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
                    if elapsed % 60 == 0:
                        self._log(f"Generating... ({elapsed // 60}m)")
                    continue
                if prompt_id in pending_ids:
                    if elapsed % 60 == 0:
                        self._log(f"Queued, waiting... ({elapsed // 60}m)")
                    continue

                h_resp = requests.get(history_url, timeout=10)
                h_resp.raise_for_status()
                h_data = h_resp.json()
                if prompt_id in h_data:
                    if h_data[prompt_id].get("status", {}).get("completed", False):
                        return
            except requests.RequestException as e:
                self._log(f"Poll error: {e}")

            if elapsed % 60 == 0:
                self._log(f"Waiting... ({elapsed // 60}m)")

    def _get_output_image(self, prompt_id: str) -> Path:
        h_resp = requests.get(f"{self._url}/history/{prompt_id}", timeout=15)
        h_resp.raise_for_status()
        history = h_resp.json().get(prompt_id, {})

        img_info = None
        for node_out in history.get("outputs", {}).values():
            imgs = node_out.get("images", [])
            if imgs:
                img_info = imgs[0]
                break

        if not img_info:
            raise RuntimeError("Could not find output image in ComfyUI history")

        params = {
            "filename": img_info["filename"],
            "subfolder": img_info.get("subfolder", ""),
            "type": img_info.get("type", "output"),
        }
        self._log(f"Downloading: {img_info['filename']}")
        dl_resp = requests.get(f"{self._url}/view", params=params, timeout=120)
        dl_resp.raise_for_status()

        out_dir = Path(self._config.get("input_dir", str(self._temp_dir)))
        out_dir.mkdir(parents=True, exist_ok=True)
        dest = out_dir / img_info["filename"]
        dest.write_bytes(dl_resp.content)
        return dest
