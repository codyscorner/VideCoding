# -*- mode: python ; coding: utf-8 -*-
"""
PictureFlipper.spec — PyInstaller build spec.

Layout (dist/PictureFlipper/):
  PictureFlipper.exe      ← launcher (small)
  _internal/              ← Python runtime + all deps
  models/                 ← yolov8n.pt  (copied post-build)
  .deepface/weights/      ← facenet_weights.h5 etc. (copied post-build)
"""
import sys
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

HERE = Path(SPECPATH)  # noqa: F821  (PyInstaller injects SPECPATH)

# ── Locate package dirs via sys.path (avoids importing torch/ultralytics) ──────
def _find_pkg(name: str) -> Path:
    for p in sys.path:
        candidate = Path(p) / name
        if candidate.is_dir():
            return candidate
    raise FileNotFoundError(f"Cannot find package '{name}' in sys.path")

deepface_pkg   = _find_pkg('deepface')
ultralytics_pkg = _find_pkg('ultralytics')

# ── collect_all for packages with dynamic/runtime imports ─────────────────────
# tensorflow: hundreds of ops modules loaded dynamically at runtime
tf_datas,     tf_binaries,     tf_hidden     = collect_all('tensorflow')
# tf_keras: keras backend loaded dynamically
tfk_datas,    tfk_binaries,    tfk_hidden    = collect_all('tf_keras')
# tqdm: TF pulls it in partially — full collection prevents "unknown location"
tqdm_datas,   tqdm_binaries,   tqdm_hidden   = collect_all('tqdm')
# pandas: deepface uses internal submodules (e.g. _config.display)
pd_datas,     pd_binaries,     pd_hidden     = collect_all('pandas')

# ── Merge all collected results ───────────────────────────────────────────────
ALL_DATAS = (
    tf_datas + tfk_datas + tqdm_datas + pd_datas + [
        (str(HERE / 'app_icon.ico'), '.'),
        # deepface: copy the whole package as data so dynamic backends are importable
        (str(deepface_pkg), 'deepface'),
        # ultralytics: config files + default assets
        (str(ultralytics_pkg / 'cfg'),    'ultralytics/cfg'),
        (str(ultralytics_pkg / 'assets'), 'ultralytics/assets'),
        # OpenCV Haar cascade XMLs required by deepface's opencv detector
        (str(_find_pkg('cv2') / 'data'), 'cv2/data'),
    ]
)

ALL_BINARIES = tf_binaries + tfk_binaries + tqdm_binaries + pd_binaries

ALL_HIDDEN = (
    tf_hidden + tfk_hidden + tqdm_hidden + pd_hidden + [
        # PySide6 GUI
        'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
        # Image processing
        'PIL', 'PIL.Image', 'PIL.ImageChops',
        'numpy', 'cv2',
        # YOLO person detection
        'ultralytics', 'ultralytics.models', 'ultralytics.nn.tasks',
        'ultralytics.utils', 'ultralytics.utils.ops',
        # DeepFace face matching (all submodules deepface imports dynamically)
        'deepface', 'deepface.DeepFace',
        'deepface.commons', 'deepface.commons.image_utils',
        'deepface.commons.package_utils',
        'deepface.models', 'deepface.models.facial_recognition',
        'deepface.modules', 'deepface.modules.representation',
        'deepface.modules.detection', 'deepface.modules.recognition',
        'deepface.detectors', 'deepface.detectors.OpenCvWrapper',
        # scipy distance metrics used by deepface
        'scipy', 'scipy.spatial', 'scipy.spatial.distance',
    ]
)

a = Analysis(
    [str(HERE / 'main.py')],
    pathex=[str(HERE)],
    binaries=ALL_BINARIES,
    datas=ALL_DATAS,
    hiddenimports=ALL_HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(HERE / 'runtime_hook.py')],
    excludes=[
        'matplotlib', 'sklearn', 'IPython',
        'notebook', 'jupyter', 'sphinx', 'pytest',
        'tkinter', '_tkinter',
    ],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PictureFlipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(HERE / 'app_icon.ico'),
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PictureFlipper',
)
