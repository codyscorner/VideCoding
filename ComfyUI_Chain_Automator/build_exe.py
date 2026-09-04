"""Build script for ComfyUI Workflow Chain Automator — produces a standalone .exe"""

import os
import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\ComfyUI Chain Automator")

# The app needs boto3 (LoRA pod check via RunPod's S3 API); the system
# Python does not have it, the repo .venv does. If we were started with a
# Python that lacks boto3, re-run this script under the .venv interpreter
# so a hand-run `python build_exe.py` / build.bat can't produce an EXE
# without it (v3.10.2 shipped that way once).
VENV_PY = ROOT.parent / ".venv" / "Scripts" / "python.exe"
try:
    import boto3  # noqa: F401
except ImportError:
    if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
        print(f"boto3 missing in {sys.executable}; re-running with {VENV_PY}")
        sys.exit(subprocess.call([str(VENV_PY), __file__, *sys.argv[1:]]))
    print("ERROR: boto3 is not importable and no repo .venv was found at "
          f"{VENV_PY}. Install boto3 (pip install boto3) or create the .venv "
          "before building — the EXE must bundle it.")
    sys.exit(1)

print(f"Building EXE with {sys.executable} ...")
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
# Never overwrite the live config next to the deployed EXE — it holds the
# user's current settings (folders, active chain, mode). Seed it only if missing.
if not (OUTPUT / "main_config.json").exists():
    shutil.copy2(ROOT / "main_config.json", OUTPUT / "main_config.json")
shutil.copy2(ROOT / "app_icon.ico", OUTPUT / "app_icon.ico")

print(f"\nCopied to: {OUTPUT}")
print("Done.")
