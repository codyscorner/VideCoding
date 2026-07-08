# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['calculator.py'],
    pathex=[],
    binaries=[],
    datas=[('app_icon.ico', '.')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers', 'cv2', 'scipy', 'pandas', 'matplotlib', 'PIL', 'numpy', 'onnx', 'onnxruntime', 'triton', 'IPython', 'jupyter', 'sklearn', 'numba', 'jax', 'safetensors', 'tokenizers', 'einops', 'av', 'soundfile'],
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
    name='MidnightCalculator',
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
