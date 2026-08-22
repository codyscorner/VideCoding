# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path
from PyInstaller.utils.hooks import collect_all

ROOT = Path(r'P:\AI\VideCoding\PromptEnhancer')
ICON = ROOT / 'app_icon.ico'

qt_datas, qt_binaries, qt_hiddenimports = collect_all('PyQt6')

datas = [(str(ROOT / 'ui'), 'ui'), (str(ROOT / 'resources'), 'resources')] + qt_datas
if ICON.exists():
    datas.append((str(ICON), '.'))

a = Analysis(
    [str(ROOT / 'main.py')],
    pathex=[],
    binaries=qt_binaries,
    datas=datas,
    hiddenimports=qt_hiddenimports + ['requests', 'ui.settings_dialog', 'ui.history'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers', 'cv2', 'scipy', 'pandas', 'matplotlib', 'onnx', 'onnxruntime', 'triton', 'IPython', 'jupyter', 'sklearn', 'numba', 'jax', 'safetensors', 'tokenizers', 'einops', 'av', 'soundfile'],
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
    name='PromptEnhancer',
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
    icon=str(ICON) if ICON.exists() else None,
)
