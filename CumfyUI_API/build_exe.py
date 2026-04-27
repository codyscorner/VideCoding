"""Build script for ComfyUI Chain Automator — produces a standalone .exe"""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent

cmd = [
    sys.executable, "-m", "PyInstaller",
    "--noconfirm",
    "--onefile",
    "--windowed",
    "--name", "ComfyUI_Chain_Automator",
    "--add-data", f"{ROOT / 'ui'};ui",
    "--hidden-import", "PyQt6.QtMultimedia",
    "--hidden-import", "PyQt6.QtMultimediaWidgets",
    "--hidden-import", "requests",
    str(ROOT / "main.py"),
]

print("Building EXE...")
result = subprocess.run(cmd, cwd=str(ROOT))
sys.exit(result.returncode)
