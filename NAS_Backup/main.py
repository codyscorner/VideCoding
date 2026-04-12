# main.py — application entry point
#
# GUI mode (default):
#   python main.py
#
# Headless mode (for Task Scheduler):
#   NAS_Backup.exe --run
#   python main.py --run

import os
import shutil
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

from config import ConfigManager


def run_headless(config: ConfigManager) -> int:
    """Run the full backup without a GUI. Writes output to Logs/.
    Returns 0 on success, 1 on failure."""

    cfg             = config.get_all()
    sources         = cfg.get("snapshot_sources", [])
    destination     = cfg.get("destination", "")
    retention_days  = cfg.get("retention_days", 365)
    threads         = cfg.get("robocopy_threads", 16)
    versioned_files = cfg.get("versioned_files", True)

    if not sources:
        print("ERROR: No snapshot sources configured. Open the app and add sources first.")
        return 1
    if not destination:
        print("ERROR: No destination configured.")
        return 1

    # Set up log file
    log_dir = Path(__file__).parent / "Logs"
    log_dir.mkdir(exist_ok=True)
    stamp    = datetime.now().strftime("%Y-%m-%d_%H-%M")
    log_path = log_dir / f"backup_{stamp}.log"

    def log(msg: str) -> None:
        print(msg)
        with open(log_path, "a", encoding="utf-8") as fh:
            fh.write(msg + "\n")

    date_stamp   = datetime.now().strftime("%Y-%m-%d")
    today_folder = os.path.join(destination, date_stamp)
    total_steps  = len(sources) + 2
    step         = 0

    log("=" * 44)
    log("NAS BACKUP — HEADLESS MODE")
    log(f"Started:     {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Sources:     {', '.join(sources)}")
    log(f"Destination: {destination}")
    log(f"Today folder: {today_folder}")
    log("=" * 44)

    for source in sources:
        source_name = Path(source).name
        dest_sub    = os.path.join(today_folder, source_name)

        # Same-day versioning pre-pass
        if versioned_files and os.path.exists(dest_sub):
            log(f"\n  Today's folder exists — checking for changed files in [{source_name}]…")
            versioned = _version_existing_files(source, dest_sub, log)
            log(f"  ✓ {versioned} file(s) versioned" if versioned else "  ✓ No changed files")

        # Backup into dated folder
        step += 1
        os.makedirs(dest_sub, exist_ok=True)
        log(f"\n[{step}/{total_steps}] Backing up: {source}\n             → {dest_sub}")
        ok, _ = _robocopy(source, dest_sub, threads, log)
        if not ok:
            log(f"ERROR: Backup failed for {source}")
            return 1

    # Retention
    step += 1
    log(f"\n[{step}/{total_steps}] Applying retention policy ({retention_days} days)…")
    _apply_retention(destination, retention_days, log)

    # Verify
    step += 1
    log(f"\n[{step}/{total_steps}] Verifying today's backup…")
    _verify(today_folder, log)

    log("\n" + "=" * 44)
    log("BACKUP COMPLETED SUCCESSFULLY")
    log(f"Finished: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    log(f"Log: {log_path}")
    log("=" * 44)
    return 0


def _version_existing_files(source: str, dest: str, log) -> int:
    """Rename changed destination files before overwriting (same-day only)."""
    versioned = 0
    for root, _dirs, files in os.walk(source):
        rel_dir = os.path.relpath(root, source)
        for fname in files:
            dst_file = (
                os.path.join(dest, fname)
                if rel_dir == "."
                else os.path.join(dest, rel_dir, fname)
            )
            if not os.path.exists(dst_file):
                continue
            src_file = os.path.join(root, fname)
            try:
                same_size  = os.path.getsize(src_file) == os.path.getsize(dst_file)
                same_mtime = abs(os.path.getmtime(src_file) - os.path.getmtime(dst_file)) <= 2.0
            except OSError:
                continue
            if same_size and same_mtime:
                continue
            name, ext  = os.path.splitext(fname)
            dt_str     = datetime.fromtimestamp(os.path.getmtime(dst_file)).strftime("%Y-%m-%d_%H%M%S")
            versioned_name = f"{name}_v{dt_str}{ext}"
            versioned_path = os.path.join(os.path.dirname(dst_file), versioned_name)
            try:
                os.rename(dst_file, versioned_path)
                log(f"    [v] {fname}  ->  {versioned_name}")
                versioned += 1
            except OSError as exc:
                log(f"    ⚠ Could not version {fname}: {exc}")
    return versioned


def _robocopy(source: str, dest: str, threads: int, log) -> tuple[bool, str]:
    args = [
        "robocopy", source, dest,
        "/E", "/FFT", f"/MT:{threads}",
        "/W:5", "/R:3", "/NDL", "/TEE", "/BYTES",
    ]
    start  = time.time()
    result = subprocess.run(args, capture_output=False)
    elapsed = time.time() - start
    h, rem = divmod(int(elapsed), 3600)
    m, s   = divmod(rem, 60)
    duration = f"{h:02d}:{m:02d}:{s:02d}"
    ok = result.returncode <= 7
    if ok:
        log(f"  ✓ Completed in {duration}")
    else:
        log(f"  ✗ FAILED (exit code {result.returncode})")
    return ok, duration


def _apply_retention(destination: str, days: int, log) -> None:
    """Delete dated folders (YYYY-MM-DD) older than *days*."""
    if not os.path.exists(destination):
        return
    cutoff  = datetime.now() - timedelta(days=days)
    deleted = 0
    for item in os.listdir(destination):
        item_path = os.path.join(destination, item)
        if not os.path.isdir(item_path):
            continue
        try:
            folder_date = datetime.strptime(item, "%Y-%m-%d")
        except ValueError:
            continue
        if folder_date < cutoff:
            log(f"  Deleting old backup: {item}")
            shutil.rmtree(item_path)
            deleted += 1
    log(f"  ✓ {deleted} old backup(s) deleted" if deleted else "  ✓ No old backups to delete")


def _verify(path: str, log) -> None:
    file_count  = 0
    total_bytes = 0
    for root, _dirs, files in os.walk(path):
        file_count += len(files)
        for f in files:
            try:
                total_bytes += os.path.getsize(os.path.join(root, f))
            except (OSError, FileNotFoundError):
                pass
    log(f"  ✓ Files in today's backup: {file_count:,}")
    log(f"  ✓ Total size: {round(total_bytes / (1024 ** 3), 2)} GB")


def main() -> None:
    config = ConfigManager()

    if "--run" in sys.argv:
        sys.exit(run_headless(config))

    from PyQt6.QtWidgets import QApplication
    from main_window import MainWindow

    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MainWindow(config)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
