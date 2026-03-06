# -*- mode: python ; coding: utf-8 -*-
"""
PictureFlipper.spec — PyInstaller build spec.

Layout (dist/PictureFlipper/):
  PictureFlipper.exe      ← launcher (small)
  _internal/              ← Python runtime + all deps (external DLLs)
  models/                 ← yolov8n.pt  (copy manually or via post-build)
  deepface_weights/       ← facenet_weights.h5 etc.  (copy manually)
"""
import os, sys
from pathlib import Path

HERE = Path(SPECPATH)  # noqa: F821  (PyInstaller injects SPECPATH)

# ── Collect deepface package data (commons/config/models sub-packages) ────────
import deepface as _df
deepface_pkg = Path(_df.__file__).parent

# ── Hidden imports needed by ultralytics / deepface ───────────────────────────
HIDDEN = [
    # PySide6
    'PySide6.QtCore', 'PySide6.QtGui', 'PySide6.QtWidgets',
    # Image / ML
    'PIL', 'PIL.Image', 'PIL.ImageChops',
    'numpy', 'cv2',
    # YOLO
    'ultralytics', 'ultralytics.models', 'ultralytics.nn.tasks',
    'ultralytics.utils', 'ultralytics.utils.ops',
    # DeepFace
    'deepface', 'deepface.DeepFace',
    'deepface.commons', 'deepface.commons.image_utils',
    'deepface.commons.package_utils',
    'deepface.models', 'deepface.models.facial_recognition',
    'deepface.modules',
    # TF / Keras (DeepFace Facenet backend)
    'tensorflow', 'tf_keras',
    # scipy (distance metrics used by deepface)
    'scipy', 'scipy.spatial', 'scipy.spatial.distance',
]

a = Analysis(
    [str(HERE / 'main.py')],
    pathex=[str(HERE)],
    binaries=[],
    datas=[
        # deepface package data (detection / recognition model configs)
        (str(deepface_pkg), 'deepface'),
        # ultralytics cfg + assets
        (str(Path(sys.prefix) / 'Lib/site-packages/ultralytics/cfg'), 'ultralytics/cfg'),
        (str(Path(sys.prefix) / 'Lib/site-packages/ultralytics/assets'), 'ultralytics/assets'),
    ],
    hiddenimports=HIDDEN,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(HERE / 'runtime_hook.py')],
    excludes=[
        # Keep bundle lean — we don't use these
        'matplotlib', 'pandas', 'sklearn', 'IPython',
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
    exclude_binaries=True,   # ← DLLs go into COLLECT folder, not the EXE
    name='PictureFlipper',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
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
