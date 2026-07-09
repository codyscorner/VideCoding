# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['frame_extractor.py'],
    pathex=[],
    binaries=[],
    datas=[('ui/styles.py', 'ui'), ('config.py', '.')],
    hiddenimports=['cv2', 'numpy'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers', 'scipy', 'pandas',
              'matplotlib', 'PIL', 'onnx', 'onnxruntime', 'triton', 'IPython', 'jupyter', 'sklearn',
              'numba', 'jax', 'safetensors', 'tokenizers', 'einops', 'av', 'soundfile'],
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
    name='MP4FrameExtractor',
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
    icon=['app_icon.ico'],
)
