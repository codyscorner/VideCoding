"""Build script for ComfyUI Workflow Editor — produces a standalone .exe"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\ComfyUI Workflow Editor")

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "ComfyUI_Workflow_Editor",
    "--add-data", f"{ROOT / 'ui'};ui",
    "--hidden-import", "PyQt6.QtWidgets",
    "--hidden-import", "PyQt6.QtGui",
    "--hidden-import", "PyQt6.QtCore",
    str(ROOT / "main.py"),
]

print("Building EXE...")
result = subprocess.run(cmd, cwd=str(ROOT))
if result.returncode != 0:
    sys.exit(result.returncode)

# Copy EXE to VibeCoded apps folder
exe_src = DIST / "ComfyUI_Workflow_Editor.exe"
if exe_src.exists():
    OUTPUT.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT / "ComfyUI_Workflow_Editor.exe"
    shutil.copy2(exe_src, dest)
    print(f"\nCopied to: {dest}")
else:
    print("EXE not found in dist/ — check PyInstaller output above")
    sys.exit(1)

print("Done.")
