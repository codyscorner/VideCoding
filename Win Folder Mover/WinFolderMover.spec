# WinFolderMover.spec
# PyInstaller spec — onefile, windowed, no console
# Run via: build_exe.bat  (or: pyinstaller WinFolderMover.spec --clean --noconfirm)

# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtGui',
        'PyQt6.QtWidgets',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PyQt6.QtMultimedia',
        'PyQt6.QtWebEngine',
        'PyQt6.QtNetwork',
        'PyQt6.Qt3D',
        'PyQt6.QtBluetooth',
        'PyQt6.QtDBus',
        'PyQt6.QtDesigner',
        'PyQt6.QtHelp',
        'PyQt6.QtLocation',
        'PyQt6.QtNfc',
        'PyQt6.QtPositioning',
        'PyQt6.QtPrintSupport',
        'PyQt6.QtQml',
        'PyQt6.QtQuick',
        'PyQt6.QtRemoteObjects',
        'PyQt6.QtSensors',
        'PyQt6.QtSerialPort',
        'PyQt6.QtSql',
        'PyQt6.QtSvg',
        'PyQt6.QtTest',
        'PyQt6.QtWebChannel',
        'PyQt6.QtWebSockets',
        'PyQt6.QtXml',
        'torch', 'torchvision', 'torchaudio', 'tensorflow', 'transformers',
        'cv2', 'scipy', 'pandas', 'matplotlib', 'PIL', 'numpy', 'onnx',
        'onnxruntime', 'triton', 'IPython', 'jupyter', 'sklearn', 'numba',
        'jax', 'safetensors', 'tokenizers', 'einops', 'av', 'soundfile',
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='WinFolderMover',
    icon='app_icon.ico',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,      # windowed — no console popup
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    onefile=True,
)
