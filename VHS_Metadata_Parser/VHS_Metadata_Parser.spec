# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['vhs_metadata_parser.py'],
    pathex=[],
    binaries=[],
    datas=[('app_icon.ico', '.')],
    hiddenimports=['PyQt6'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'tensorflow', 'tensorboard',
        'keras', 'jax', 'jaxlib', 'transformers', 'diffusers', 'accelerate',
        'safetensors', 'onnx', 'onnxruntime', 'sklearn', 'scipy', 'pandas',
        'matplotlib', 'sympy', 'numba', 'llvmlite', 'h5py', 'triton',
        'xformers', 'bitsandbytes', 'sentencepiece', 'tokenizers',
        'face_recognition', 'dlib', 'ultralytics', 'playwright',
        'cv2', 'numpy', 'PIL', 'py7zr', 'rarfile', 'send2trash',
        'IPython', 'jupyter', 'notebook', 'pytest',
    ],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='VHS_Metadata_Parser',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
