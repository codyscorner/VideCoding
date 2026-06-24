"""Build script for Video Converter — produces a standalone .exe"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\Video Converter")

icon = ROOT / "app_icon.ico"
icon_args = ["--icon", str(icon)] if icon.exists() else []

print("Building EXE...")
cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "VideoConverter",
    *icon_args,
    str(ROOT / "main.py"),
]
result = subprocess.run(cmd, cwd=str(ROOT))
if result.returncode != 0:
    sys.exit(result.returncode)

exe_src = DIST / "VideoConverter.exe"
if not exe_src.exists():
    print("EXE not found in dist/ — check PyInstaller output above")
    sys.exit(1)

OUTPUT.mkdir(parents=True, exist_ok=True)

r = subprocess.run(
    ["robocopy", str(exe_src.parent), str(OUTPUT), exe_src.name, "/R:10", "/W:5"],
    capture_output=True, text=True,
)
if r.returncode >= 8:
    print(r.stdout)
    print(r.stderr)
    sys.exit(1)

print(f"\nCopied to: {OUTPUT}")
print("Done.")
