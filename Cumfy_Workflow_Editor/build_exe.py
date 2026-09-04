"""Build script for ComfyUI Workflow Editor — produces a standalone .exe

Run with the shared VideCoding venv (build.bat does this) or any Python that has
PyQt6 + PyInstaller. Pauses at the end when launched by double-click so the
output stays readable.
"""

import subprocess
import sys
import shutil
from pathlib import Path

ROOT   = Path(__file__).parent
DIST   = ROOT / "dist"
OUTPUT = Path(r"P:\Apps\VibeCoded\ComfyUI Workflow Editor")
NAME   = "ComfyUI_Workflow_Editor"

# The shared venv carries heavy ML packages that PyInstaller would otherwise
# bundle (torch alone is hundreds of MB). Mandatory — see memory/PROJECT_SUMMARY.
EXCLUDES = [
    "torch", "torchvision", "torchaudio", "tensorflow", "transformers", "cv2",
    "scipy", "pandas", "matplotlib", "PIL", "numpy", "onnx", "onnxruntime",
    "triton", "IPython", "jupyter", "sklearn", "numba", "jax", "safetensors",
    "tokenizers", "einops", "av", "soundfile", "pkg_resources", "setuptools",
]


def pause_if_interactive():
    try:
        if sys.stdin and sys.stdin.isatty():
            input("\nPress Enter to close...")
    except Exception:
        pass


def main() -> int:
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--onefile",
        "--windowed",
        "--name", NAME,
        "--icon", str(ROOT / "app_icon.ico"),
        "--add-data", f"{ROOT / 'app_icon.ico'};.",
        "--hidden-import", "PyQt6.QtWidgets",
        "--hidden-import", "PyQt6.QtGui",
        "--hidden-import", "PyQt6.QtCore",
    ]
    for mod in EXCLUDES:
        cmd += ["--exclude-module", mod]
    cmd.append(str(ROOT / "main.py"))

    print(f"Building EXE with {sys.executable} ...")
    result = subprocess.run(cmd, cwd=str(ROOT))
    if result.returncode != 0:
        print(f"\nPyInstaller FAILED (exit {result.returncode}) — see output above.")
        return result.returncode

    exe_src = DIST / f"{NAME}.exe"
    if not exe_src.exists():
        print("\nEXE not found in dist/ — check PyInstaller output above")
        return 1

    OUTPUT.mkdir(parents=True, exist_ok=True)
    dest = OUTPUT / exe_src.name
    shutil.copy2(exe_src, dest)
    size_mb = dest.stat().st_size / (1024 * 1024)
    print(f"\nBuilt {exe_src.name} ({size_mb:.1f} MB)")
    print(f"Copied to: {dest}")
    print("Done.")
    return 0


if __name__ == "__main__":
    code = main()
    pause_if_interactive()
    sys.exit(code)
