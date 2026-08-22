"""Build script for Prompt Enhancer — produces a standalone .exe"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\Prompt Enhancer")

print("Building EXE...")
result = subprocess.run(
    [sys.executable, "-m", "PyInstaller", "--noconfirm", "PromptEnhancer.spec"],
    cwd=str(ROOT)
)
if result.returncode != 0:
    sys.exit(result.returncode)

exe_src = DIST / "PromptEnhancer.exe"
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
# user's API keys and preferences. Seed it only if missing.
if not (OUTPUT / "main_config.json").exists() and (ROOT / "main_config.json").exists():
    shutil.copy2(ROOT / "main_config.json", OUTPUT / "main_config.json")
icon_src = ROOT / "app_icon.ico"
if icon_src.exists():
    shutil.copy2(icon_src, OUTPUT / "app_icon.ico")

print(f"\nCopied to: {OUTPUT}")
print("Done.")
