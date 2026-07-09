# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('app_icon.ico', '.'),
    ],
    hiddenimports=[
        'PIL',
        'PIL.Image',
        'PIL.ExifTags',
        'PIL.ImageOps',
        'cv2',
        'numpy',
        'send2trash',
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
        'face_recognition', 'dlib', 'ultralytics', 'playwright',
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
