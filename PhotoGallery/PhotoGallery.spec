# -*- mode: python ; coding: utf-8 -*-
import face_recognition_models

block_cipher = None

# Path to the face landmark/encoding model files face_recognition needs at runtime.
models_path = face_recognition_models.__path__[0]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),
        (models_path, 'face_recognition_models'),
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'PIL.ImageOps',
        'cv2',
        'numpy',
        'send2trash',
        'face_recognition',
        'face_recognition_models',
        'dlib',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch', 'torchvision', 'torchaudio', 'tensorflow', 'tensorboard',
        'keras', 'jax', 'jaxlib', 'transformers', 'diffusers', 'accelerate',
        'safetensors', 'onnx', 'onnxruntime', 'sklearn', 'scipy', 'pandas',
        'matplotlib', 'sympy', 'numba', 'llvmlite', 'h5py', 'triton',
        'xformers', 'bitsandbytes', 'sentencepiece', 'tokenizers',
        'ultralytics', 'playwright',
        'IPython', 'jupyter', 'notebook', 'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='PhotoGallery',
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
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='PhotoGallery',
)
