import fnmatch
import hashlib
import shutil
from pathlib import Path

from PyQt6.QtCore import QThread, pyqtSignal


def _hash_file(path: Path) -> str:
    h = hashlib.blake2b(digest_size=16)
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


class SyncWorker(QThread):
    compare_done = pyqtSignal(list)   # list of file-info dicts
    progress     = pyqtSignal(int, int)
    log          = pyqtSignal(str)
    copy_done    = pyqtSignal(list)   # list of copied file-info dicts (report)
    delete_done  = pyqtSignal(list)   # list of deleted file-info dicts (report)
    error        = pyqtSignal(str)

    def __init__(
        self,
        mode: str,
        source: str,
        dest: str,
        recursive: bool,
        file_mask: str = "",
        missing_files: list | None = None,
        hash_verify: bool = False,
    ):
        super().__init__()
        self._mode = mode          # "compare" | "reverse" | "copy" | "delete"
        self._source = Path(source)
        self._dest = Path(dest)
        self._recursive = recursive
        self._patterns = self._parse_mask(file_mask)
        self._missing_files = missing_files or []
        self._hash_verify = hash_verify
        self._cancelled = False

    @staticmethod
    def _parse_mask(mask: str) -> list[str]:
        if not mask.strip():
            return []
        patterns = []
        for part in mask.split(","):
            p = part.strip()
            if not p:
                continue
            if "*" not in p and "?" not in p:
                p = p.lstrip(".")
                p = f"*.{p}"
            patterns.append(p.lower())
        return patterns

    def _matches(self, filename: str) -> bool:
        if not self._patterns:
            return True
        name = filename.lower()
        return any(fnmatch.fnmatch(name, pat) for pat in self._patterns)

    def cancel(self) -> None:
        self._cancelled = True

    def run(self) -> None:
        try:
            if self._mode == "compare":
                self._run_compare()
            elif self._mode == "reverse":
                self._run_reverse()
            elif self._mode == "delete":
                self._run_delete()
            else:
                self._run_copy()
        except Exception as exc:
            self.error.emit(str(exc))

    # ------------------------------------------------------------------
    def _scan_index(self, root: Path, label: str) -> dict:
        """Return {(rel_path, size): Path} for every matching file under root."""
        index: dict = {}
        if not root.exists():
            self.log.emit(f"{label} folder does not exist yet.")
            return index
        pattern = "**/*" if self._recursive else "*"
        try:
            entries = list(root.glob(pattern))
        except OSError as exc:
            self.log.emit(f"WARNING: Could not fully scan {label.lower()} — {exc}")
            entries = []
        for f in entries:
            if self._cancelled:
                return index
            try:
                if not f.is_file():
                    continue
                if not self._matches(f.name):
                    continue
                rel = f.relative_to(root)
                index[(str(rel), f.stat().st_size)] = f
            except OSError as exc:
                self.log.emit(f"WARNING: Skipped (unreadable): {f.name} — {exc}")
        return index

    # ------------------------------------------------------------------
    def _run_compare(self) -> None:
        self.log.emit(f"Source:      {self._source}")
        self.log.emit(f"Destination: {self._dest}")
        self.log.emit(f"Subfolders:  {'Yes' if self._recursive else 'No'}")
        mask_display = ", ".join(self._patterns) if self._patterns else "all files"
        self.log.emit(f"File mask:   {mask_display}")
        if self._hash_verify:
            self.log.emit("Hash verify: ON (matched-size files will be content-checked)")
        self.log.emit("─" * 48)

        self.log.emit("Scanning destination...")
        dest_index = self._scan_index(self._dest, "Destination")
        self.log.emit(f"Destination has {len(dest_index)} file(s).")

        self.log.emit("Scanning source...")
        pattern = "**/*" if self._recursive else "*"
        missing = []
        scanned = 0
        differs = 0

        try:
            entries = list(self._source.glob(pattern))
        except OSError as exc:
            self.log.emit(f"WARNING: Could not scan source — {exc}")
            entries = []

        for src_file in entries:
            if self._cancelled:
                self.log.emit("Cancelled.")
                return
            try:
                if not src_file.is_file():
                    continue
                if not self._matches(src_file.name):
                    continue
                size = src_file.stat().st_size
            except OSError as exc:
                self.log.emit(f"WARNING: Skipped (unreadable): {src_file.name} — {exc}")
                continue

            scanned += 1
            rel = src_file.relative_to(self._source)
            key = (str(rel), size)

            if key not in dest_index:
                missing.append({
                    "name":     src_file.name,
                    "size":     size,
                    "src_path": str(src_file),
                    "rel_path": str(rel),
                    "reason":   "Missing",
                })
            elif self._hash_verify:
                dst_file = dest_index[key]
                try:
                    if _hash_file(src_file) != _hash_file(dst_file):
                        differs += 1
                        missing.append({
                            "name":     src_file.name,
                            "size":     size,
                            "src_path": str(src_file),
                            "rel_path": str(rel),
                            "reason":   "Content differs",
                        })
                except OSError as exc:
                    self.log.emit(f"WARNING: Could not hash {src_file.name} — {exc}")

        self.log.emit(f"Source has {scanned} file(s).")
        if self._hash_verify:
            self.log.emit(f"Content mismatches found: {differs}")
        self.log.emit("─" * 48)
        if missing:
            self.log.emit(f"Files to sync: {len(missing)}. Ready to sync.")
        else:
            self.log.emit("Destination is up to date — nothing to copy.")
        self.compare_done.emit(missing)

    # ------------------------------------------------------------------
    def _run_reverse(self) -> None:
        self.log.emit(f"Source:      {self._source}")
        self.log.emit(f"Destination: {self._dest}")
        self.log.emit(f"Subfolders:  {'Yes' if self._recursive else 'No'}")
        self.log.emit("Reverse diff: finding files in Destination not present in Source")
        self.log.emit("─" * 48)

        self.log.emit("Scanning source...")
        src_index = self._scan_index(self._source, "Source")
        self.log.emit(f"Source has {len(src_index)} file(s).")

        self.log.emit("Scanning destination...")
        pattern = "**/*" if self._recursive else "*"
        extra = []
        scanned = 0

        try:
            entries = list(self._dest.glob(pattern))
        except OSError as exc:
            self.log.emit(f"WARNING: Could not scan destination — {exc}")
            entries = []

        for dst_file in entries:
            if self._cancelled:
                self.log.emit("Cancelled.")
                return
            try:
                if not dst_file.is_file():
                    continue
                if not self._matches(dst_file.name):
                    continue
                size = dst_file.stat().st_size
            except OSError as exc:
                self.log.emit(f"WARNING: Skipped (unreadable): {dst_file.name} — {exc}")
                continue

            scanned += 1
            rel = dst_file.relative_to(self._dest)
            key = (str(rel), size)

            if key not in src_index:
                extra.append({
                    "name":     dst_file.name,
                    "size":     size,
                    "dst_path": str(dst_file),
                    "rel_path": str(rel),
                    "reason":   "Extra in Destination",
                })

        self.log.emit(f"Destination has {scanned} file(s).")
        self.log.emit("─" * 48)
        if extra:
            self.log.emit(f"Files not in Source: {len(extra)}.")
        else:
            self.log.emit("No extra files found in Destination.")
        self.compare_done.emit(extra)

    # ------------------------------------------------------------------
    def _run_copy(self) -> None:
        total = len(self._missing_files)
        copied = []
        for i, info in enumerate(self._missing_files):
            if self._cancelled:
                self.log.emit("Cancelled.")
                self.copy_done.emit(copied)
                return

            dst = self._dest / info["rel_path"]
            dst.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(info["src_path"], dst)
            copied.append(info)

            self.log.emit(f"Copied: {info['rel_path']}")
            self.progress.emit(i + 1, total)

        self.copy_done.emit(copied)

    # ------------------------------------------------------------------
    def _run_delete(self) -> None:
        total = len(self._missing_files)
        deleted = []
        for i, info in enumerate(self._missing_files):
            if self._cancelled:
                self.log.emit("Cancelled.")
                self.delete_done.emit(deleted)
                return

            try:
                Path(info["dst_path"]).unlink()
                deleted.append(info)
                self.log.emit(f"Deleted: {info['rel_path']}")
            except OSError as exc:
                self.log.emit(f"WARNING: Could not delete {info['rel_path']} — {exc}")

            self.progress.emit(i + 1, total)

        self.delete_done.emit(deleted)
