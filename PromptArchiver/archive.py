"""Prompt Archiver data layer.

Direct port of the Electron main.js IPC handlers. Operates on the same
on-disk archive format, so archives created by v1.x load unchanged:

    Prompt_Archive/
      text|image|video/
        prompt_<timestamp>/
          prompt.txt
          negative_prompt.txt   (optional)
          metadata.json
          <output files...>
"""

from __future__ import annotations

import json
import shutil
import zipfile
from datetime import datetime, timezone
from pathlib import Path

PROMPT_TYPES = ("text", "image", "video")
RESERVED_FILES = {"prompt.txt", "metadata.json", "negative_prompt.txt"}


def _iso_now() -> str:
    """UTC ISO timestamp matching JS `new Date().toISOString()` (ms + Z)."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.") + (
        f"{datetime.now(timezone.utc).microsecond // 1000:03d}Z"
    )


def _folder_name(iso_timestamp: str) -> str:
    """prompt_<timestamp> with : and . replaced by - (parity with main.js)."""
    return "prompt_" + iso_timestamp.replace(":", "-").replace(".", "-")


class ArchiveError(Exception):
    """Raised when an archive operation cannot be completed."""


class PromptArchive:
    """All file operations for one archive root."""

    def __init__(self, root: str | Path):
        self.root = Path(root)

    # ---- structure -------------------------------------------------------

    def ensure_structure(self) -> None:
        for t in PROMPT_TYPES:
            (self.root / t).mkdir(parents=True, exist_ok=True)

    # ---- loading ---------------------------------------------------------

    def load_prompts(self) -> list[dict]:
        """Read every prompt folder; skip unreadable ones. Newest first."""
        prompts: list[dict] = []
        for ptype in PROMPT_TYPES:
            type_dir = self.root / ptype
            if not type_dir.is_dir():
                continue
            for folder in type_dir.iterdir():
                if not folder.is_dir():
                    continue
                try:
                    prompts.append(self._read_prompt_folder(folder))
                except (OSError, json.JSONDecodeError, KeyError) as exc:
                    print(f"Skipping unreadable prompt folder {folder}: {exc}")
        prompts.sort(key=lambda p: p.get("timestamp") or "", reverse=True)
        return prompts

    def _read_prompt_folder(self, folder: Path) -> dict:
        metadata = json.loads((folder / "metadata.json").read_text(encoding="utf-8"))

        # prompt.txt is normally present, but some v1.x folders lack it —
        # the old app hid those entirely; we show them with an empty prompt.
        prompt_path = folder / "prompt.txt"
        prompt_text = (
            prompt_path.read_text(encoding="utf-8") if prompt_path.exists() else ""
        )

        negative = ""
        neg_path = folder / "negative_prompt.txt"
        if neg_path.exists():
            negative = neg_path.read_text(encoding="utf-8")

        output_files = sorted(
            f.name for f in folder.iterdir()
            if f.is_file() and f.name not in RESERVED_FILES
        )

        record = dict(metadata)
        record.update(
            prompt=prompt_text,
            negativePrompt=negative,
            outputFiles=output_files,
            path=str(folder),
            # backfill keys missing from old archives
            title=metadata.get("title", ""),
            aiSource=metadata.get("aiSource", ""),
            modelName=metadata.get("modelName", ""),
            modelType=metadata.get("modelType", ""),
            baseModel=metadata.get("baseModel", ""),
            hasNegativePrompt=metadata.get("hasNegativePrompt", bool(negative)),
            rating=metadata.get("rating", 0) or 0,
            tags=metadata.get("tags", []) or [],
        )
        return record

    # ---- creating / updating --------------------------------------------

    def save_prompt(self, data: dict) -> Path:
        """Create a new prompt folder from dialog data; returns its path."""
        timestamp = _iso_now()
        folder = self.root / data["type"] / _folder_name(timestamp)
        folder.mkdir(parents=True, exist_ok=True)

        (folder / "prompt.txt").write_text(data["prompt"], encoding="utf-8")
        negative = (data.get("negativePrompt") or "").strip()
        if negative:
            (folder / "negative_prompt.txt").write_text(
                data["negativePrompt"], encoding="utf-8"
            )

        metadata = {
            "timestamp": timestamp,
            "type": data["type"],
            "title": data.get("title", ""),
            "tags": data.get("tags", []),
            "folderName": folder.name,
            "aiSource": data.get("aiSource", ""),
            "modelName": data.get("modelName", ""),
            "modelType": data.get("modelType", ""),
            "baseModel": data.get("baseModel", ""),
            "hasNegativePrompt": bool(negative),
            "rating": 0,
        }
        self._write_metadata(folder, metadata)

        self._copy_files_into(folder, data.get("outputFiles", []), dedupe=False)
        return folder

    def update_prompt(self, prompt_path: str | Path, data: dict) -> None:
        folder = Path(prompt_path)
        (folder / "prompt.txt").write_text(data["prompt"], encoding="utf-8")

        negative = (data.get("negativePrompt") or "").strip()
        neg_path = folder / "negative_prompt.txt"
        if negative:
            neg_path.write_text(data["negativePrompt"], encoding="utf-8")
        else:
            neg_path.unlink(missing_ok=True)

        metadata = self._read_metadata(folder)
        metadata.update(
            title=data.get("title", ""),
            tags=data.get("tags", []),
            aiSource=data.get("aiSource", ""),
            modelName=data.get("modelName", ""),
            modelType=data.get("modelType", ""),
            baseModel=data.get("baseModel", ""),
            hasNegativePrompt=bool(negative),
            lastModified=_iso_now(),
        )
        self._write_metadata(folder, metadata)

    def update_rating(self, prompt_path: str | Path, rating: int) -> None:
        folder = Path(prompt_path)
        metadata = self._read_metadata(folder)
        metadata.update(rating=rating, lastModified=_iso_now())
        self._write_metadata(folder, metadata)

    def change_type(self, prompt_path: str | Path, new_type: str) -> Path:
        folder = Path(prompt_path)
        current_type = folder.parent.name
        if current_type == new_type:
            return folder

        dest_dir = self.root / new_type
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest = dest_dir / folder.name
        if dest.exists():
            raise ArchiveError(
                "A prompt with this name already exists in the destination folder"
            )
        folder.rename(dest)

        metadata = self._read_metadata(dest)
        metadata["type"] = new_type
        self._write_metadata(dest, metadata)
        return dest

    def delete_prompt(self, prompt_path: str | Path) -> None:
        shutil.rmtree(prompt_path, ignore_errors=True)

    def clone_prompt(self, prompt_path: str | Path) -> Path:
        source = Path(prompt_path)
        metadata = self._read_metadata(source)

        timestamp = _iso_now()
        clone = self.root / metadata["type"] / _folder_name(timestamp)
        clone.mkdir(parents=True, exist_ok=True)

        for f in source.iterdir():
            if f.is_file():
                shutil.copy2(f, clone / f.name)

        metadata.update(
            timestamp=timestamp,
            folderName=clone.name,
            clonedFrom=self._read_metadata(source).get("folderName", source.name),
            rating=0,
        )
        self._write_metadata(clone, metadata)
        return clone

    # ---- output files ----------------------------------------------------

    def replace_files(self, prompt_path: str | Path, new_files: list[str]) -> None:
        folder = Path(prompt_path)
        for f in folder.iterdir():
            if f.is_file() and f.name not in RESERVED_FILES:
                f.unlink(missing_ok=True)
        self._copy_files_into(folder, new_files, dedupe=False)

    def append_files(self, prompt_path: str | Path, new_files: list[str]) -> None:
        self._copy_files_into(Path(prompt_path), new_files, dedupe=True)

    @staticmethod
    def _copy_files_into(folder: Path, files: list[str], dedupe: bool) -> None:
        for src in files:
            src_path = Path(src)
            try:
                dest = folder / src_path.name
                if dedupe:
                    counter = 1
                    while dest.exists():
                        dest = folder / f"{src_path.stem}_{counter}{src_path.suffix}"
                        counter += 1
                shutil.copy2(src_path, dest)
            except OSError as exc:
                print(f"Error copying file {src}: {exc}")

    # ---- export ----------------------------------------------------------

    @staticmethod
    def export_zip(prompt_paths: list[str], zip_path: str | Path) -> int:
        """Zip each prompt folder under its basename; returns archive size."""
        zip_path = Path(zip_path)
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
            for prompt_path in prompt_paths:
                folder = Path(prompt_path)
                for f in folder.rglob("*"):
                    if f.is_file():
                        zf.write(f, Path(folder.name) / f.relative_to(folder))
        return zip_path.stat().st_size

    # ---- metadata helpers --------------------------------------------------

    @staticmethod
    def _read_metadata(folder: Path) -> dict:
        return json.loads((folder / "metadata.json").read_text(encoding="utf-8"))

    @staticmethod
    def _write_metadata(folder: Path, metadata: dict) -> None:
        (folder / "metadata.json").write_text(
            json.dumps(metadata, indent=2), encoding="utf-8"
        )
