from __future__ import annotations

import re
import subprocess
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Lock

from PyQt6.QtCore import QThread, pyqtSignal

_DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")
_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")


def _to_seconds(h, m, s) -> float:
    return int(h) * 3600 + int(m) * 60 + float(s)


class ConversionWorker(QThread):
    progress = pyqtSignal(int, int)          # completed_count, total (emitted as each job finishes)
    file_started = pyqtSignal(int)           # job_index (job has begun encoding)
    file_progress = pyqtSignal(int, int)     # job_index, percent (0-100)
    file_done = pyqtSignal(int, bool, str)   # job_index, success, message
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)          # done_count, fail_count

    def __init__(self, jobs: list[dict], ffmpeg_path: str = "ffmpeg", max_workers: int = 1):
        super().__init__()
        # jobs: list of {"input": Path, "output": Path, "args": list[str], "pre_args": list[str]}
        self.jobs = jobs
        self.ffmpeg_path = ffmpeg_path
        self.max_workers = max(1, max_workers)
        self._cancelled = False
        self._procs: list[subprocess.Popen] = []
        self._procs_lock = Lock()

    def cancel(self):
        self._cancelled = True
        with self._procs_lock:
            for proc in self._procs:
                try:
                    proc.terminate()
                except Exception:
                    pass

    def run(self):
        total = len(self.jobs)
        completed = done = failed = 0
        lock = Lock()

        def worker(item):
            nonlocal completed, done, failed
            i, job = item
            if self._cancelled:
                self.file_done.emit(i, False, "Cancelled")
                with lock:
                    completed += 1
                    self.progress.emit(completed, total)
                return
            ok = self._run_one(i, job)
            with lock:
                completed += 1
                if ok:
                    done += 1
                else:
                    failed += 1
                self.progress.emit(completed, total)

        with ThreadPoolExecutor(max_workers=self.max_workers) as pool:
            list(pool.map(worker, enumerate(self.jobs)))

        self.finished.emit(done, failed)

    def _run_one(self, i: int, job: dict) -> bool:
        if self._cancelled:
            return False

        inp: Path = job["input"]
        out: Path = job["output"]
        args: list = job["args"]
        pre_args: list = job.get("pre_args", [])

        self.file_started.emit(i)
        self.log.emit(f"→  {inp.name}   ›   {out.name}")
        out.parent.mkdir(parents=True, exist_ok=True)

        cmd = [self.ffmpeg_path] + pre_args + ["-y", "-i", str(inp)] + args + [str(out)]
        try:
            proc = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            with self._procs_lock:
                self._procs.append(proc)

            stderr_lines: list[str] = []
            total_seconds: float | None = None
            for line in proc.stderr:
                line = line.rstrip()
                if not line:
                    continue
                stderr_lines.append(line)
                if total_seconds is None:
                    m = _DURATION_RE.search(line)
                    if m:
                        total_seconds = _to_seconds(*m.groups())
                m = _TIME_RE.search(line)
                if m and total_seconds:
                    cur = _to_seconds(*m.groups())
                    pct = max(0, min(100, int(cur / total_seconds * 100)))
                    self.file_progress.emit(i, pct)

            proc.wait()

            with self._procs_lock:
                if proc in self._procs:
                    self._procs.remove(proc)

            if self._cancelled:
                self.file_done.emit(i, False, "Cancelled")
                return False

            if proc.returncode == 0:
                self.file_progress.emit(i, 100)
                self.file_done.emit(i, True, "Done")
                self.log.emit("   ✓  complete\n")
                return True
            else:
                tail = "\n".join(stderr_lines[-6:])
                self.file_done.emit(i, False, "Error")
                self.log.emit(
                    f"   ✗  failed (ffmpeg exit {proc.returncode})\n{tail}\n"
                )
                return False
        except Exception as exc:
            self.file_done.emit(i, False, str(exc))
            self.log.emit(f"   ✗  {exc}\n")
            return False
