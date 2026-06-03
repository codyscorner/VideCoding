"""Build script for ComfyUI Workflow Chain Automator — produces a standalone .exe"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\ComfyUI Workflow Chain Automator")

print("Building EXE...")
result = subprocess.run(
    [sys.executable, "-m", "PyInstaller", "--noconfirm", "ComfyUI_Chain_Automator.spec"],
    cwd=str(ROOT)
)
if result.returncode != 0:
    sys.exit(result.returncode)

exe_src = DIST / "ComfyUI_Chain_Automator.exe"
if not exe_src.exists():
    print("EXE not found in dist/ — check PyInstaller output above")
    sys.exit(1)

OUTPUT.mkdir(parents=True, exist_ok=True)

# robocopy: /R:10 = 10 retries, /W:5 = 5s wait between, exit code <8 = success
r = subprocess.run(
    ["robocopy", str(exe_src.parent), str(OUTPUT), exe_src.name, "/R:10", "/W:5"],
    capture_output=True, text=True
)
if r.returncode >= 8:
    print(r.stdout); print(r.stderr)
    sys.exit(1)
shutil.copy2(ROOT / "main_config.json", OUTPUT / "main_config.json")
shutil.copy2(ROOT / "app_icon.ico", OUTPUT / "app_icon.ico")

print(f"\nCopied to: {OUTPUT}")
print("Done.")
