from pathlib import Path
import subprocess

from PyQt6.QtCore import QThread, pyqtSignal


class ConversionWorker(QThread):
    progress = pyqtSignal(int, int)        # job_index, total (emitted before each job starts)
    file_done = pyqtSignal(int, bool, str) # job_index, success, message
    log = pyqtSignal(str)
    finished = pyqtSignal(int, int)        # done_count, fail_count

    def __init__(self, jobs: list[dict], ffmpeg_path: str = "ffmpeg"):
        super().__init__()
        # jobs: list of {"input": Path, "output": Path, "args": list[str]}
        self.jobs = jobs
        self.ffmpeg_path = ffmpeg_path
        self._cancelled = False
        self._proc = None

    def cancel(self):
        self._cancelled = True
        if self._proc:
            try:
                self._proc.terminate()
            except Exception:
                pass

    def run(self):
        done = failed = 0
        total = len(self.jobs)

        for i, job in enumerate(self.jobs):
            if self._cancelled:
                self.log.emit("— Cancelled —")
                break

            self.progress.emit(i, total)
            inp: Path = job["input"]
            out: Path = job["output"]
            args: list = job["args"]

            self.log.emit(f"→  {inp.name}   ›   {out.name}")
            out.parent.mkdir(parents=True, exist_ok=True)

            cmd = [self.ffmpeg_path, "-y", "-i", str(inp)] + args + [str(out)]
            try:
                self._proc = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                stderr_lines: list[str] = []
                for line in self._proc.stderr:
                    line = line.rstrip()
                    if line:
                        stderr_lines.append(line)
                self._proc.wait()

                if self._proc.returncode == 0:
                    done += 1
                    self.file_done.emit(i, True, "Done")
                    self.log.emit("   ✓  complete\n")
                else:
                    failed += 1
                    tail = "\n".join(stderr_lines[-6:])
                    self.file_done.emit(i, False, "Error")
                    self.log.emit(
                        f"   ✗  failed (ffmpeg exit {self._proc.returncode})\n{tail}\n"
                    )
            except Exception as exc:
                failed += 1
                self.file_done.emit(i, False, str(exc))
                self.log.emit(f"   ✗  {exc}\n")

        self.progress.emit(total, total)
        self.finished.emit(done, failed)
