"""Build ComfyUI_Video_Creator.exe with PyInstaller and deploy it to
P:\\Apps\\VibeCoded\\ComfyUI Video Creator.

Run with the repo .venv (build.bat does this automatically) — it has PyQt6,
requests, websocket-client and Pillow. The shared venv also carries heavy
ML packages, so every one of them is excluded or the EXE balloons ~10x.
"""

import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
DIST = ROOT / "dist"
APP_NAME = "ComfyUI_Video_Creator"
OUTPUT = Path(r"P:\Apps\VibeCoded\ComfyUI Video Creator")
FFMPEG_SOURCES = [
    Path(r"P:\Apps\VibeCoded\ComfyUI Chain Automator\ffmpeg.exe"),
]

EXCLUDES = [
    "torch", "torchvision", "torchaudio", "tensorflow", "transformers", "cv2",
    "scipy", "pandas", "matplotlib", "onnx", "onnxruntime", "triton", "IPython",
    "jupyter", "sklearn", "numba", "jax", "safetensors", "tokenizers", "einops",
    "av", "soundfile", "boto3", "botocore", "playwright", "numpy",
]

VENV_PY = ROOT.parent / ".venv" / "Scripts" / "python.exe"
try:
    import PyQt6  # noqa: F401
    import PyInstaller  # noqa: F401
except ImportError:
    if VENV_PY.exists() and Path(sys.executable).resolve() != VENV_PY.resolve():
        print(f"PyQt6/PyInstaller missing in {sys.executable}; re-running with {VENV_PY}")
        sys.exit(subprocess.call([str(VENV_PY), __file__, *sys.argv[1:]]))
    print("ERROR: PyQt6 and PyInstaller are required. Build with the repo .venv.")
    sys.exit(1)


def version_from_main() -> str:
    m = re.search(r'^VERSION\s*=\s*"([^"]+)"', (ROOT / "main.py").read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else "?"


def main():
    print(f"Building {APP_NAME} v{version_from_main()} with {sys.executable} ...")
    cmd = [
        sys.executable, "-m", "PyInstaller", "--noconfirm", "--clean",
        "--onefile", "--windowed",
        "--name", APP_NAME,
        "--icon", str(ROOT / "app_icon.ico"),
        "--add-data", f"{ROOT / 'app_icon.ico'};.",
        "--collect-all", "PyQt6",
        "--hidden-import", "requests",
        "--hidden-import", "websocket",
        "--hidden-import", "PIL",
    ]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    cmd.append(str(ROOT / "main.py"))
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        sys.exit(result.returncode)

    exe_src = DIST / f"{APP_NAME}.exe"
    if not exe_src.exists():
        print("EXE not found in dist/ — check the PyInstaller output above")
        sys.exit(1)
    print(f"Built {exe_src} ({exe_src.stat().st_size // (1024 * 1024)} MB)")

    OUTPUT.mkdir(parents=True, exist_ok=True)
    # robocopy retries while the old EXE is still open; exit code < 8 = success
    r = subprocess.run(
        ["robocopy", str(exe_src.parent), str(OUTPUT), exe_src.name, "/R:10", "/W:5"],
        capture_output=True, text=True,
    )
    if r.returncode >= 8:
        print(r.stdout)
        print(r.stderr)
        sys.exit(1)

    shutil.copy2(ROOT / "app_icon.ico", OUTPUT / "app_icon.ico")
    # Never overwrite the live config next to the deployed EXE.
    if not (OUTPUT / "video_creator_config.json").exists() and (ROOT / "video_creator_config.json").exists():
        shutil.copy2(ROOT / "video_creator_config.json", OUTPUT / "video_creator_config.json")
    # Ship ffmpeg next to the EXE (thumbnails, last-frame, stitching).
    if not (OUTPUT / "ffmpeg.exe").exists():
        for src in FFMPEG_SOURCES:
            if src.exists():
                shutil.copy2(src, OUTPUT / "ffmpeg.exe")
                print(f"Copied ffmpeg.exe from {src}")
                break
        else:
            print("WARNING: no ffmpeg.exe found to ship — set FFmpeg path in Settings or drop ffmpeg.exe next to the EXE")

    sync = Path(r"P:\Apps\VibeCoded\Sync-StartMenuShortcuts.ps1")
    if sync.exists():
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(sync)],
                       capture_output=True, text=True)
        print("Start Menu shortcuts synced")

    print(f"\nDeployed to: {OUTPUT}")
    print("Done.")


if __name__ == "__main__":
    main()
