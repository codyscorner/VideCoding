import os
import re
import subprocess
from datetime import date

CREATE_NO_WINDOW = 0x08000000

DEFAULT_PREFIX = "All_PC_Images_backup"

# Maps compression key → 7z flags
COMPRESSION_FLAGS = {
    "store":   ["-m0=Copy"],
    "fast":    ["-mx=3"],
    "normal":  ["-mx=5"],
    "maximum": ["-mx=7"],
    "ultra":   ["-mx=9"],
}


def build_archive_name(prefix=None):
    p = (prefix or DEFAULT_PREFIX).strip() or DEFAULT_PREFIX
    return f"{p}_{date.today().strftime('%Y_%m_%d')}.7z"


def run_archive(seven_zip_path, source_folder, dest_path, progress_cb, log_cb,
                cancel_check=None, prefix=None, compression="store"):
    """
    Returns (success: bool, archive_path: str, error: str).
    progress_cb(int 0-100) called with 7z percentage.
    cancel_check() returns True if the user cancelled.
    """
    archive_name = build_archive_name(prefix)
    archive_path = os.path.join(dest_path, archive_name)

    if os.path.exists(archive_path):
        log_cb(f"Overwriting existing archive: {archive_name}")
        try:
            os.remove(archive_path)
        except Exception as e:
            return False, archive_path, f"Cannot remove existing archive: {e}"

    comp_flags = COMPRESSION_FLAGS.get(compression, COMPRESSION_FLAGS["store"])
    cmd = [seven_zip_path, "a", "-t7z", *comp_flags, "-bsp1", archive_path, source_folder]

    log_cb(f"Archive:     {archive_name}")
    log_cb(f"Source:      {source_folder}")
    log_cb(f"Destination: {dest_path}")
    log_cb(f"Compression: {compression.capitalize()}")
    log_cb("Archiving...")

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            creationflags=CREATE_NO_WINDOW,
        )

        buf = b""
        while True:
            chunk = process.stdout.read(256)
            if not chunk:
                break
            if cancel_check and cancel_check():
                process.kill()
                return False, archive_path, "cancelled"
            buf += chunk
            parts = re.split(b"[\r\n]", buf)
            buf = parts[-1]
            for part in parts[:-1]:
                text = part.decode("utf-8", errors="replace").strip()
                if not text:
                    continue
                m = re.search(r"(\d+)%", text)
                if m:
                    progress_cb(int(m.group(1)))
                else:
                    log_cb(text)

        # Flush remaining buffer
        if buf:
            text = buf.decode("utf-8", errors="replace").strip()
            if text and not re.search(r"\d+%", text):
                log_cb(text)

        process.wait()

        if process.returncode == 0:
            return True, archive_path, ""
        return False, archive_path, f"7z exited with code {process.returncode}"

    except Exception as e:
        return False, "", str(e)
