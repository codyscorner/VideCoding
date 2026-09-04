# -*- mode: python ; coding: utf-8 -*-
import face_recognition_models

# Get the path to face_recognition_models data files
models_path = face_recognition_models.__path__[0]

# The shared VideCoding venv carries heavy ML packages FaceFinder doesn't use;
# without these excludes the EXE balloons ~10x. (numpy/PIL/dlib stay — needed.)
HEAVY_EXCLUDES = [
    'torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers',
    'cv2', 'scipy', 'pandas', 'matplotlib', 'onnx', 'onnxruntime',
    'triton', 'IPython', 'jupyter', 'sklearn', 'numba', 'jax',
    'safetensors', 'tokenizers', 'einops', 'av', 'soundfile',
    'tkinterdnd2',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        (models_path, 'face_recognition_models'),
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'face_recognition',
        'face_recognition_models',
        'dlib',
        'PIL',
        'numpy',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=HEAVY_EXCLUDES,
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

# Splash screen shown instantly during startup
splash = Splash(
    'splash.png',
    binaries=a.binaries,
    datas=a.datas,
    text_pos=(10, 230),
    text_size=10,
    text_color='white',
    text_default='Loading...',
)

exe = EXE(
    pyz,
    a.scripts,
    splash,
    splash.binaries,
    [],
    exclude_binaries=True,
    name='FaceFinder',
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
    icon='app_icon.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='FaceFinder',
)
