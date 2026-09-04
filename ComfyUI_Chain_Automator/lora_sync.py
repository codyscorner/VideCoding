"""LoRA inventory + sync for chain workflows.

Every batch workflow names its LoRAs by bare filename (ComfyUI resolves them
against its models/loras folder). Before a chain runs, this module answers:

  * which LoRA files does the chain reference (per segment file)?
  * are they all present in the local LoRA folder (Settings > Folders)?
  * in RunPod mode: are they all present on the pod's volume (checked via
    RunPod's S3-compatible API, Settings > RunPod Volume (S3))?
  * upload the ones the pod is missing, from the local folder.

The S3 access mirrors the S3 Browser app (same profile / endpoint / RunPod
quirks — long read timeout for the server-side multipart merge, retries on
transient 403s, "already landed" check before re-uploading).

boto3 is imported lazily so the app still starts without it (local-only
users) and so a broken S3 config never breaks chain selection.
"""
from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal

LORA_EXTS = {".safetensors"}
BATCH_FILE_GLOB = "workflow_segment_*_batch.json"
_LORA_KEY_RE = re.compile(r"^lora(_name|_\d+)$")

# Config keys (all live in main_config.json next to the EXE)
CFG_S3_PROFILE = "s3_profile_name"
CFG_S3_REGION = "s3_region"
CFG_S3_ENDPOINT = "s3_endpoint_url"
CFG_S3_BUCKET = "s3_bucket_name"
CFG_S3_LORAS_PREFIX = "s3_loras_prefix"
CFG_LORA_CHECK = "lora_check_enabled"

S3_DEFAULTS = {
    CFG_S3_PROFILE: "runpod-s3",
    CFG_S3_REGION: "",
    CFG_S3_ENDPOINT: "",
    CFG_S3_BUCKET: "",
    CFG_S3_LORAS_PREFIX: "runpod-slim/ComfyUI/models/loras/",
    CFG_LORA_CHECK: True,
}

UPLOAD_RETRY_ATTEMPTS = 6
UPLOAD_RETRY_BASE_DELAY = 1.0


# ---------------------------------------------------------------------- #
# Workflow scanning
# ---------------------------------------------------------------------- #

def loras_in_workflow(workflow: dict) -> set[str]:
    """Bare LoRA filenames referenced by any LoRA-loader style input:
    `lora_name` (LoraLoader*, MiniMaxH3TurboLoRA, ...) and `lora_NN`
    (rgthree Lora Loader Stack). 'None' / empty slots are ignored."""
    names: set[str] = set()
    for node in workflow.values():
        if not isinstance(node, dict):
            continue
        for key, value in node.get("inputs", {}).items():
            if not _LORA_KEY_RE.match(key) or not isinstance(value, str):
                continue
            value = value.strip()
            if not value or value.lower() == "none":
                continue
            if Path(value).suffix.lower() in LORA_EXTS:
                names.add(value)
    return names


def collect_chain_loras(chain_dir: Path) -> dict[str, list[str]]:
    """LoRA name -> sorted list of batch workflow files (in the chain folder)
    that reference it. Unreadable files are skipped here — the wiring
    validator already reports those."""
    refs: dict[str, set[str]] = {}
    for f in sorted(Path(chain_dir).glob(BATCH_FILE_GLOB)):
        try:
            with open(f, "r", encoding="utf-8") as fh:
                workflow = json.load(fh)
        except Exception:  # noqa: BLE001
            continue
        for name in loras_in_workflow(workflow):
            refs.setdefault(name, set()).add(f.name)
    return {k: sorted(v) for k, v in refs.items()}


# ---------------------------------------------------------------------- #
# Local folder
# ---------------------------------------------------------------------- #

@dataclass
class LocalLoraStatus:
    present: dict[str, Path]      # name -> local file
    missing: list[str]            # names not found under loras_dir
    case_mismatch: dict[str, str]  # name -> actual on-disk name (Windows finds it, Linux pod won't)


def check_local_loras(loras_dir: str | Path, names: list[str] | set[str]) -> LocalLoraStatus:
    base = Path(loras_dir) if loras_dir else None
    present: dict[str, Path] = {}
    missing: list[str] = []
    case_mismatch: dict[str, str] = {}
    if not base or not base.is_dir():
        return LocalLoraStatus({}, sorted(names), {})
    # Index the folder once (recursive: workflows may reference "sub/x.safetensors")
    index: dict[str, Path] = {}
    for p in base.rglob("*"):
        if p.is_file() and p.suffix.lower() in LORA_EXTS:
            index[p.relative_to(base).as_posix()] = p
    lower_index = {k.lower(): k for k in index}
    for name in sorted(names):
        key = name.replace("\\", "/")
        if key in index:
            present[name] = index[key]
        elif key.lower() in lower_index:
            actual = lower_index[key.lower()]
            present[name] = index[actual]
            case_mismatch[name] = actual
        else:
            missing.append(name)
    return LocalLoraStatus(present, missing, case_mismatch)


# ---------------------------------------------------------------------- #
# RunPod volume via S3
# ---------------------------------------------------------------------- #

def s3_configured(config: dict) -> bool:
    return bool(
        (config.get(CFG_S3_ENDPOINT) or "").strip()
        and (config.get(CFG_S3_BUCKET) or "").strip()
        and (config.get(CFG_S3_PROFILE) or "").strip()
    )


def import_s3_browser_config(path: str | Path) -> dict:
    """Read the S3 Browser app's config.json (profile_name / region /
    endpoint_url / bucket_name) into this app's config keys."""
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    out = {}
    for src, dst in (
        ("profile_name", CFG_S3_PROFILE), ("region", CFG_S3_REGION),
        ("endpoint_url", CFG_S3_ENDPOINT), ("bucket_name", CFG_S3_BUCKET),
    ):
        if data.get(src):
            out[dst] = str(data[src]).strip()
    return out


class S3LoraStore:
    """Thin S3 client scoped to the pod's LoRA folder."""

    def __init__(self, config: dict):
        import boto3  # lazy: optional dependency, slow import
        from botocore.config import Config as BotoConfig

        self.bucket = (config.get(CFG_S3_BUCKET) or "").strip()
        self.prefix = (config.get(CFG_S3_LORAS_PREFIX) or S3_DEFAULTS[CFG_S3_LORAS_PREFIX]).strip()
        if self.prefix and not self.prefix.endswith("/"):
            self.prefix += "/"
        session = boto3.session.Session(profile_name=(config.get(CFG_S3_PROFILE) or "").strip() or None)
        self._client = session.client(
            "s3",
            region_name=(config.get(CFG_S3_REGION) or "").strip() or None,
            endpoint_url=(config.get(CFG_S3_ENDPOINT) or "").strip(),
            # RunPod merges multipart chunks server-side after
            # CompleteMultipartUpload and can take minutes to answer for
            # large files — the default 60s read timeout would abort the wait
            # and trigger a full re-upload.
            config=BotoConfig(
                s3={"addressing_style": "path"},
                signature_version="s3v4",
                read_timeout=1800,
                retries={"max_attempts": 3},
            ),
        )

    def key_for(self, name: str) -> str:
        return self.prefix + name.replace("\\", "/")

    def test_connection(self) -> None:
        self._client.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix, MaxKeys=1)

    def list_remote(self) -> dict[str, int]:
        """LoRA name (relative to the prefix) -> size, recursive."""
        out: dict[str, int] = {}
        paginator = self._client.get_paginator("list_objects_v2")
        for page in paginator.paginate(Bucket=self.bucket, Prefix=self.prefix):
            for obj in page.get("Contents", []):
                rel = obj["Key"][len(self.prefix):]
                if rel and not rel.endswith("/"):
                    out[rel] = obj["Size"]
        return out

    def object_size(self, key: str) -> int:
        return self._client.head_object(Bucket=self.bucket, Key=key)["ContentLength"]

    def merge_tmp_present(self) -> bool:
        """RunPod shows a .s3compat-merge-*.tmp in the folder while it merges
        multipart chunks server-side."""
        resp = self._client.list_objects_v2(Bucket=self.bucket, Prefix=self.prefix + ".s3compat-merge-")
        return bool(resp.get("Contents"))

    def upload(self, local_path: Path, key: str, progress_cb=None) -> None:
        self._client.upload_file(str(local_path), self.bucket, key, Callback=progress_cb)


@dataclass
class RemoteLoraStatus:
    present: dict[str, int]   # name -> size on pod
    missing: list[str]
    size_mismatch: dict[str, tuple[int, int]]  # name -> (local size, pod size)
    error: str = ""           # non-empty = could not check (config / network)


def check_remote_loras(config: dict, names: list[str] | set[str],
                       local: LocalLoraStatus | None = None) -> RemoteLoraStatus:
    try:
        store = S3LoraStore(config)
        remote = store.list_remote()
    except ImportError:
        return RemoteLoraStatus({}, [], {}, error=(
            "boto3 is not installed in the Python running this app. The built EXE "
            "bundles it; when running from source use the repo .venv (run.bat does)"))
    except Exception as e:  # noqa: BLE001
        return RemoteLoraStatus({}, [], {}, error=f"{type(e).__name__}: {e}")
    present: dict[str, int] = {}
    missing: list[str] = []
    mismatch: dict[str, tuple[int, int]] = {}
    for name in sorted(names):
        key = name.replace("\\", "/")
        if key in remote:
            present[name] = remote[key]
            if local and name in local.present:
                lsize = local.present[name].stat().st_size
                if lsize != remote[key]:
                    mismatch[name] = (lsize, remote[key])
        else:
            missing.append(name)
    return RemoteLoraStatus(present, missing, mismatch)


class RemoteLoraCheckWorker(QThread):
    """Runs check_remote_loras off the UI thread (network)."""
    done = pyqtSignal(object)  # RemoteLoraStatus

    def __init__(self, config: dict, names: list[str], local: LocalLoraStatus | None):
        super().__init__()
        self._config = config
        self._names = list(names)
        self._local = local

    def run(self):
        self.done.emit(check_remote_loras(self._config, self._names, self._local))


@dataclass
class LoraUploadJob:
    name: str
    local_path: Path
    size: int


class LoraUploadWorker(QThread):
    """Uploads LoRA files from the local folder to the pod's LoRA folder."""
    log = pyqtSignal(str)
    progress = pyqtSignal(int, int, str, int, int)  # bytes_done, bytes_total, name, files_done, files_total
    finished_ok = pyqtSignal(list)  # list of (name, error) — empty = all good

    def __init__(self, config: dict, jobs: list[LoraUploadJob]):
        super().__init__()
        self._config = config
        self._jobs = jobs
        self._cancelled = False
        self._total = sum(j.size for j in jobs)

    def cancel(self):
        self._cancelled = True

    def run(self):
        errors: list[tuple[str, str]] = []
        try:
            store = S3LoraStore(self._config)
        except ImportError:
            self.finished_ok.emit([("(connection)", "boto3 is not installed in the Python running this app — use the built EXE or the repo .venv")])
            return
        except Exception as e:  # noqa: BLE001
            self.finished_ok.emit([("(connection)", f"{type(e).__name__}: {e}")])
            return

        done_bytes = 0
        n = len(self._jobs)
        for i, job in enumerate(self._jobs):
            if self._cancelled:
                errors.append((job.name, "cancelled"))
                continue
            key = store.key_for(job.name)
            self.log.emit(f"Uploading LoRA {i + 1}/{n}: {job.name} ({job.size / 1e6:.0f} MB)")
            last_error: Exception | None = None
            for attempt in range(1, UPLOAD_RETRY_ATTEMPTS + 1):
                if self._cancelled:
                    break
                sent = 0
                merge_logged = False

                def cb(chunk: int, _job=job):
                    nonlocal sent, merge_logged
                    sent += chunk
                    self.progress.emit(done_bytes + sent, self._total, _job.name, i, n)
                    if not merge_logged and sent >= _job.size:
                        merge_logged = True
                        self.log.emit(f"  {_job.name}: all bytes sent, waiting for the pod to merge the upload...")

                try:
                    store.upload(job.local_path, key, cb)
                    last_error = None
                    break
                except Exception as exc:  # noqa: BLE001
                    # The final CompleteMultipartUpload can time out during
                    # RunPod's server-side merge even though the object landed.
                    try:
                        if store.object_size(key) == job.size:
                            last_error = None
                            break
                    except Exception:  # noqa: BLE001
                        pass
                    last_error = exc
                    if attempt < UPLOAD_RETRY_ATTEMPTS:
                        delay = UPLOAD_RETRY_BASE_DELAY * (2 ** (attempt - 1))
                        self.log.emit(f"  {job.name}: attempt {attempt} failed ({type(exc).__name__}), retrying in {delay:.0f}s")
                        time.sleep(delay)
            if last_error is not None:
                errors.append((job.name, str(last_error)))
                self.log.emit(f"  FAILED: {job.name}: {last_error}")
            else:
                # Verify size so a truncated object is never trusted.
                try:
                    remote_size = store.object_size(key)
                    if remote_size != job.size:
                        errors.append((job.name, f"size on pod {remote_size} != local {job.size}"))
                        self.log.emit(f"  WARNING: {job.name} landed with the wrong size ({remote_size} vs {job.size})")
                    else:
                        self.log.emit(f"  OK: {job.name} is on the pod")
                except Exception as e:  # noqa: BLE001
                    self.log.emit(f"  {job.name}: uploaded, could not verify size ({e})")
            done_bytes += job.size
            self.progress.emit(done_bytes, self._total, job.name, i + 1, n)
        self.finished_ok.emit(errors)
